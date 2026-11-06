from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Usuario
from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico, HistoricoManutencao
from .models import Sensor, Telemetria
from .limit_service import sync_limit_reading


class AlertLifecycleTests(APITestCase):
    def setUp(self):
        empresa = Empresa.objects.create(nome='Ciclos', cnpj='CICLOS', email='ciclos@example.com')
        self.equipamento = Equipamento.objects.create(
            empresa=empresa, nome='Motor', numero_serie='CICLOS', criticidade='C',
        )
        self.sensor = Sensor.objects.create(
            equipamento=self.equipamento, nome='Temperatura 1', tipo='temperatura',
            unidade_medida='C', limite_alerta=100,
        )
        self.gestor = Usuario.objects.create_user(
            username='gestor_ciclos', password='123', tipo_usuario='gestor', empresa=empresa,
        )
        self.client.force_authenticate(self.gestor)
        # Os testes preditivos exercitam a análise real separadamente.
        tendencia = patch('telemetria.signals.sync_sensor_trend')
        tendencia.start()
        self.addCleanup(tendencia.stop)

    def ler(self, *valores, sensor=None):
        return [Telemetria.objects.create(sensor=sensor or self.sensor, valor=v) for v in valores]

    def alertas(self):
        return Alerta.objects.filter(origem='limite', sensor=self.sensor).order_by('pk')

    def test_valores_normais_nao_criam_alerta_nem_ordem(self):
        self.ler(10, 60, 69.9)
        self.assertFalse(Alerta.objects.exists())
        self.assertFalse(OrdemServico.objects.exists())

    def test_limites_inclusivos_e_vinculo_explicito(self):
        for valor, nivel in [(70, 'baixo'), (85, 'medio'), (100, 'critico')]:
            self.ler(valor)
            alerta = self.alertas().get()
            self.assertEqual(alerta.nivel, nivel)
            self.assertEqual(alerta.sensor_id, self.sensor.pk)
            ordem = alerta.ordem_servico
            self.assertEqual(ordem.alerta_origem_id, alerta.pk)
            self.assertEqual(ordem.sensor_origem_id, self.sensor.pk)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_repeticao_e_reprocessamento_nao_duplicam(self):
        self.ler(90, 90, 90)
        leitura = Telemetria.objects.latest('pk')
        sync_limit_reading(leitura)
        self.assertEqual(self.alertas().count(), 1)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_queda_de_gravidade_preserva_pico_e_atualiza_condicao(self):
        self.ler(110, 75)
        alerta = self.alertas().get()
        self.assertEqual(alerta.nivel, 'critico')
        self.assertEqual(alerta.dados_analise['nivel_atual'], 'baixo')
        self.assertEqual(alerta.dados_analise['ultimo_valor'], 75)
        self.assertEqual(alerta.ordem_servico.prioridade, 'C')

    def test_oscilacao_reinicia_confirmacao_e_recuperacao_nao_fecha_ordem(self):
        self.ler(90, 60, 90, 60)
        alerta = self.alertas().get()
        self.assertEqual(alerta.status, 'ativo')
        self.assertEqual(alerta.dados_analise['leituras_normais_consecutivas'], 1)
        self.ler(60)
        alerta.refresh_from_db()
        self.assertEqual(alerta.status, 'resolvido')
        self.assertIn('recuperado_em', alerta.dados_analise)
        self.assertEqual(alerta.ordem_servico.status, 'pendente')
        self.assertFalse(HistoricoManutencao.objects.exists())

    def test_ausencia_edicao_e_reprocessamento_nao_confirmam_recuperacao(self):
        self.ler(90)
        normal = self.ler(60)[0]
        sync_limit_reading(normal)
        normal.valor = 50
        normal.save()
        alerta = self.alertas().get()
        self.assertEqual(alerta.status, 'ativo')
        self.assertEqual(alerta.dados_analise['leituras_normais_consecutivas'], 1)

    def test_sensores_do_mesmo_tipo_nao_se_misturam(self):
        outro = Sensor.objects.create(
            equipamento=self.equipamento, nome='Temperatura 2', tipo='temperatura',
            unidade_medida='C', limite_alerta=100,
        )
        self.ler(90)
        self.ler(110, sensor=outro)
        self.assertEqual(Alerta.objects.filter(origem='limite').count(), 2)
        self.assertEqual(OrdemServico.objects.count(), 2)
        self.ler(60, 60)
        self.assertEqual(Alerta.objects.get(sensor=outro).status, 'ativo')

    def test_recorrencia_reutiliza_ordem_aberta_e_preserva_ocorrencias(self):
        self.ler(90, 60, 60)
        anterior = self.alertas().get()
        self.ler(110)
        atual = self.alertas().last()
        anterior.refresh_from_db()
        self.assertNotEqual(atual.pk, anterior.pk)
        self.assertEqual(anterior.status, 'resolvido')
        self.assertEqual(atual.status, 'ativo')
        self.assertEqual(atual.ordem_servico_id, anterior.ordem_servico_id)
        self.assertEqual(atual.ordem_servico.alerta_origem_id, anterior.pk)
        self.assertEqual(OrdemServico.objects.count(), 1)
        for alerta in (anterior, atual):
            resposta = self.client.get(reverse('alertas-detail', args=[alerta.pk]))
            self.assertEqual(resposta.data['ordem_servico_id'], anterior.ordem_servico_id)

    def test_recorrencia_tambem_reutiliza_ordem_em_andamento_apos_renomear(self):
        self.ler(90)
        ordem = self.alertas().get().ordem_servico
        ordem.titulo = 'Investigar motor'
        ordem.status = 'andamento'
        ordem.save()
        self.ler(60, 60, 90)
        self.assertEqual(OrdemServico.objects.count(), 1)
        self.assertEqual(self.alertas().last().ordem_servico_id, ordem.pk)

    def test_conclusao_ou_cancelamento_nao_resolvem_alerta_nem_recriam_os(self):
        for terminal in ('concluida', 'cancelada'):
            with self.subTest(status=terminal):
                self.ler(90)
                alerta = self.alertas().last()
                ordem = alerta.ordem_servico
                ordem.status = terminal
                ordem.save()
                quantidade = OrdemServico.objects.count()
                self.ler(110, 110)
                alerta.refresh_from_db()
                ordem.refresh_from_db()
                self.assertEqual(alerta.status, 'ativo')
                self.assertEqual(ordem.status, terminal)
                self.assertEqual(OrdemServico.objects.count(), quantidade)
                self.ler(60, 60)

    def test_nova_ocorrencia_apos_ordem_terminal_cria_nova_ordem(self):
        for terminal in ('concluida', 'cancelada'):
            with self.subTest(status=terminal):
                self.ler(90)
                anterior = self.alertas().last()
                ordem = anterior.ordem_servico
                ordem.status = terminal
                ordem.save()
                self.ler(60, 60, 90)
                atual = self.alertas().last()
                self.assertNotEqual(atual.pk, anterior.pk)
                self.assertNotEqual(atual.ordem_servico_id, ordem.pk)
                self.assertEqual(atual.ordem_servico.status, 'pendente')
                self.ler(60, 60)

    def test_prioridade_manual_e_contexto_de_abertura_sao_preservados(self):
        self.ler(75)
        ordem = self.alertas().get().ordem_servico
        ordem.prioridade_manual = True
        ordem.prioridade = 'B'
        ordem.save()
        self.equipamento.criticidade = 'A'
        self.equipamento.save()
        self.ler(110)
        ordem.refresh_from_db()
        self.assertEqual(ordem.prioridade, 'B')
        self.assertTrue(ordem.prioridade_manual)
        self.assertEqual(ordem.gravidade_condicao, 'critica')
        self.assertEqual(ordem.prioridade_automatica, 'C')
        self.assertEqual(ordem.criticidade_na_abertura, 'C')
        resposta = self.client.patch(reverse('ordens-servico-detail', args=[ordem.pk]),
                                    {'status': 'andamento'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data['criticidade_na_abertura'], 'C')

    def test_recalculo_api_nao_reescreve_criticidade_de_abertura(self):
        self.ler(75)
        ordem = self.alertas().get().ordem_servico
        self.equipamento.criticidade = 'A'
        self.equipamento.save()
        resposta = self.client.patch(reverse('ordens-servico-detail', args=[ordem.pk]),
                                    {'status': 'andamento'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(resposta.data['criticidade_na_abertura'], 'C')

    def test_ignorado_nao_renasce_sem_recuperacao_confirmada(self):
        self.ler(90)
        alerta = self.alertas().get()
        resposta = self.client.patch(reverse('alertas-detail', args=[alerta.pk]),
                                    {'status': 'ignorado'}, format='json')
        self.assertEqual(resposta.status_code, 405, resposta.data)
        # Prepara um ignorado legado, que continua sendo acompanhado.
        Alerta.objects.filter(pk=alerta.pk).update(status='ignorado')
        self.ler(110, 60, 110)
        self.assertEqual(self.alertas().count(), 1)
        self.ler(60, 60, 110)
        alerta.refresh_from_db()
        self.assertEqual(alerta.status, 'ignorado')
        self.assertIn('recuperado_em', alerta.dados_analise)
        self.assertEqual(self.alertas().count(), 2)

    def test_alerta_manual_legado_nao_e_resolvido_pela_telemetria(self):
        manual = Alerta.objects.create(
            equipamento=self.equipamento, sensor=self.sensor, origem='manual',
            tipo_alerta='Alerta de Temperatura', nivel='medio', descricao='Verificação humana',
        )
        self.ler(90, 60, 60)
        manual.refresh_from_db()
        self.assertEqual(manual.status, 'ativo')
        self.assertEqual(self.alertas().get().status, 'resolvido')
        self.assertEqual(OrdemServico.objects.count(), 2)
        resposta = self.client.patch(reverse('alertas-detail', args=[manual.pk]),
                                    {'status': 'resolvido'}, format='json')
        self.assertEqual(resposta.status_code, 405, resposta.data)

    def test_api_nao_forja_origem_nem_altera_identidade_automatica(self):
        resposta = self.client.post(reverse('alertas-list'), {
            'equipamento': self.equipamento.pk, 'tipo_alerta': 'Falso',
            'origem': 'limite', 'nivel': 'critico', 'descricao': 'Teste',
        }, format='json')
        self.assertEqual(resposta.status_code, 405)
        self.ler(90)
        alerta = self.alertas().get()
        for dados in ({'origem': 'manual'}, {'sensor': None}, {'status': 'resolvido'}):
            resposta = self.client.patch(reverse('alertas-detail', args=[alerta.pk]), dados, format='json')
            self.assertEqual(resposta.status_code, 405, resposta.data)

    def test_conclusao_modelo_gera_data_e_historico_uma_unica_vez(self):
        self.ler(90)
        ordem = self.alertas().get().ordem_servico
        ordem.status = 'concluida'
        ordem.save(update_fields=['status'])
        ordem.refresh_from_db()
        self.assertIsNotNone(ordem.data_conclusao)
        data = ordem.data_conclusao
        ordem.save()
        self.assertEqual(HistoricoManutencao.objects.filter(ordem_servico=ordem).count(), 1)
        self.assertEqual(ordem.data_conclusao, data)

    def test_estados_terminais_nao_reabrem_pelo_modelo_ou_api(self):
        for terminal in ('concluida', 'cancelada'):
            ordem = OrdemServico.objects.create(
                equipamento=self.equipamento, titulo=terminal, descricao='Teste', status=terminal,
            )
            resposta = self.client.patch(reverse('ordens-servico-detail', args=[ordem.pk]),
                                        {'status': 'pendente'}, format='json')
            self.assertEqual(resposta.status_code, 400, resposta.data)
            ordem.status = 'pendente'
            with self.assertRaises(ValidationError):
                ordem.save()

    def test_sensor_inativo_ou_sem_limite_valido_nao_resolve_alerta(self):
        self.ler(90)
        self.sensor.ativo = False
        self.sensor.save()
        self.ler(50, 50)
        self.assertEqual(self.alertas().get().status, 'ativo')
        self.sensor.ativo = True
        self.sensor.limite_alerta = 0
        self.sensor.save()
        self.ler(50, 50)
        self.assertEqual(self.alertas().get().status, 'ativo')

    def test_valor_invalido_nao_comprova_recuperacao(self):
        self.ler(90)
        invalida = self.ler(float('inf'))[0]
        sync_limit_reading(invalida)
        self.assertEqual(self.alertas().get().dados_analise['leituras_normais_consecutivas'], 0)
        resposta = self.client.post(reverse('leituras-list'),
                                    {'sensor': self.sensor.pk, 'valor': 'NaN'}, format='json')
        self.assertEqual(resposta.status_code, 400)

    def test_alteracao_de_limites_reinicia_confirmacao(self):
        self.ler(90, 50)
        self.sensor.limite_alerta_baixo_pct = 60
        self.sensor.save()
        self.ler(50)
        self.assertEqual(self.alertas().get().status, 'ativo')
        self.ler(50)
        self.assertEqual(self.alertas().get().status, 'resolvido')

    def test_falha_no_fluxo_reverte_a_leitura_e_o_alerta(self):
        with patch('alertas.signals.PrioridadeOSService.criar_por_alerta', side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):
                self.ler(90)
        self.assertFalse(Telemetria.objects.exists())
        self.assertFalse(Alerta.objects.exists())
        self.assertFalse(OrdemServico.objects.exists())

    def test_agravamento_atualiza_gravidade_mesmo_sem_mudar_prioridade(self):
        self.equipamento.criticidade = None
        self.equipamento.save()
        self.ler(75, 90)
        ordem = self.alertas().get().ordem_servico
        self.assertIsNone(ordem.prioridade)
        self.assertEqual(ordem.gravidade_condicao, 'moderada')

    def test_alerta_manual_vinculado_nao_pode_mudar_de_equipamento(self):
        alerta = Alerta.objects.create(
            equipamento=self.equipamento, tipo_alerta='Inspeção', descricao='Teste', origem='manual',
        )
        outro = Equipamento.objects.create(
            empresa=self.equipamento.empresa, nome='Outro', numero_serie='CICLOS-OUTRO',
        )
        resposta = self.client.patch(reverse('alertas-detail', args=[alerta.pk]),
                                    {'equipamento': outro.pk}, format='json')
        self.assertEqual(resposta.status_code, 405)
