import csv
import io
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, CriteriosCriticidade, PlanoManutencao
from ativos.services import aplicar_criticidade, CRITERIOS_SUGERIDOS
from alertas.models import Alerta
from .models import OrdemServico
from .services import PrioridadeOSService


class PrioridadeABCTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Prioridade ABC', cnpj='PABC', email='p@example.com')
        self.outra = Empresa.objects.create(nome='Outra ABC', cnpj='PABC-OUTRA', email='o@example.com')
        self.gestor = Usuario.objects.create_user(username='pabc', tipo_usuario='gestor', empresa=self.empresa)
        self.tecnico = Usuario.objects.create_user(username='pabc-tec', tipo_usuario='tecnico', empresa=self.empresa)
        self.outro = Usuario.objects.create_user(username='pabc-outro', tipo_usuario='gestor', empresa=self.outra)
        self.guia = CriteriosCriticidade.objects.create(empresa=self.empresa, revisao=1, **CRITERIOS_SUGERIDOS,
            representante_manutencao='Representante de teste', data_validacao=timezone.localdate())
        self.equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Bomba ABC', numero_serie='PABC')
        aplicar_criticidade(self.equipamento, 'B', 'Impacto intermediário com contingência.', self.gestor)
        self.client.force_authenticate(self.gestor)
        self.url = reverse('ordens-servico-list')

    def criar(self, **kwargs):
        return OrdemServico.objects.create(equipamento=self.equipamento, titulo='Inspeção ABC', descricao='Inspecionar', **kwargs)

    def test_todas_as_classes_e_tipos_copiam_snapshot_sem_matriz(self):
        for classe in ('A', 'B', 'C', None):
            self.equipamento.criticidade = classe
            self.equipamento.save()
            for tipo in ('corretiva', 'preventiva', 'preditiva'):
                with self.subTest(classe=classe, tipo=tipo):
                    ordem = self.criar(tipo_os=tipo, risco_seguranca=True, gravidade_condicao='critica')
                    self.assertEqual(ordem.prioridade, classe)
                    self.assertEqual(ordem.prioridade_automatica, classe)
                    self.assertEqual(ordem.criticidade_na_abertura, classe)
                    self.assertEqual(ordem.criterios_criticidade_na_abertura_id, self.guia.pk)
                    self.assertFalse(ordem.prioridade_manual)
                    self.assertEqual(ordem.historico_prioridade.count(), 1)

    def test_reclassificacao_edicao_e_encerramento_nao_recalculam_os(self):
        ordem = self.criar()
        aplicar_criticidade(self.equipamento, 'A', 'Processo alterado, sem contingência.', self.gestor)
        url = reverse('ordens-servico-detail', args=[ordem.pk])
        for data in ({'gravidade_condicao': 'critica'}, {'risco_seguranca': True}, {'status': 'concluida'}):
            response = self.client.patch(url, data, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['prioridade'], 'B')
            self.assertEqual(response.data['criticidade_atual'], 'A')
            self.assertEqual(response.data['criticidade_na_abertura'], 'B')
        self.assertEqual(ordem.historico_prioridade.count(), 1)

    def test_criacao_sem_classe_nao_bloqueia_e_os_continua_a_definir(self):
        aplicar_criticidade(self.equipamento, None, 'Avaliação pendente de revisão.', self.gestor)
        response = self.client.post(self.url, {'equipamento': self.equipamento.pk, 'titulo': 'Triagem', 'descricao': 'Avaliar'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['prioridade'])
        aplicar_criticidade(self.equipamento, 'A', 'Classificação concluída.', self.gestor)
        ordem = OrdemServico.objects.get(pk=response.data['id'])
        self.assertIsNone(ordem.prioridade)

    def test_ajuste_e_restauracao_preservam_base_e_auditam(self):
        ordem = self.criar()
        ajuste = reverse('ordens-servico-ajustar-prioridade', args=[ordem.pk])
        response = self.client.post(ajuste, {'prioridade': 'A', 'justificativa': 'Atendimento adiantado por parada.'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['prioridade_manual'])
        self.assertEqual(response.data['prioridade_origem'], 'ajustada')
        self.assertEqual(response.data['prioridade_automatica'], 'B')
        aplicar_criticidade(self.equipamento, 'C', 'Reserva instalada.', self.gestor)
        restored = self.client.post(reverse('ordens-servico-restaurar-prioridade', args=[ordem.pk]), {'justificativa': 'Retomar o planejamento original.'})
        self.assertEqual(restored.status_code, 200, restored.data)
        self.assertEqual(restored.data['prioridade'], 'B')
        self.assertFalse(restored.data['prioridade_manual'])
        events = list(ordem.historico_prioridade.all())
        self.assertEqual([e.origem for e in events], ['restauracao', 'ajuste', 'herdada'])
        self.assertEqual(events[1].alterado_por, self.gestor)
        self.assertEqual(events[1].prioridade_anterior, 'B')

    def test_ajuste_exige_motivo_e_nao_aceita_categoria_antiga(self):
        ordem = self.criar()
        url = reverse('ordens-servico-ajustar-prioridade', args=[ordem.pk])
        for payload in ({'prioridade': 'A'}, {'prioridade': 'A', 'justificativa': '  '}, {'prioridade': 'alta', 'justificativa': 'Teste'}):
            self.assertEqual(self.client.post(url, payload).status_code, 400)
        self.assertEqual(ordem.historico_prioridade.count(), 1)

    def test_tecnico_e_outra_empresa_nao_ajustam_prioridade(self):
        ordem = self.criar()
        for user, expected in ((self.tecnico, 403), (self.outro, 404)):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.post(reverse('ordens-servico-ajustar-prioridade', args=[ordem.pk]),
                {'prioridade': 'A', 'justificativa': 'Teste'}).status_code, expected)
        self.client.force_authenticate(self.tecnico)
        self.assertEqual(self.client.get(reverse('ordens-servico-historico-prioridade', args=[ordem.pk])).status_code, 200)

    def test_api_geral_nao_contorna_ajuste_e_equipamento_e_fixo(self):
        ordem = self.criar()
        url = reverse('ordens-servico-detail', args=[ordem.pk])
        self.assertEqual(self.client.patch(url, {'prioridade': 'A'}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {'equipamento': self.equipamento.pk, 'titulo': 'Teste', 'descricao': 'Teste', 'prioridade': 'A'}).status_code, 400)
        outro = Equipamento.objects.create(empresa=self.empresa, nome='Outro', numero_serie='PABC-2')
        self.assertEqual(self.client.patch(url, {'equipamento': outro.pk}).status_code, 400)
        ordem.criticidade_na_abertura = 'A'
        with self.assertRaises(ValidationError):
            ordem.save()

    def test_encerradas_nao_aceitam_ajuste_ou_restauracao(self):
        for status in ('concluida', 'cancelada'):
            ordem = self.criar(status=status)
            for action in ('ajustar-prioridade', 'restaurar-prioridade'):
                response = self.client.post(reverse('ordens-servico-' + action, args=[ordem.pk]), {'prioridade': 'A', 'justificativa': 'Teste'})
                self.assertEqual(response.status_code, 400)

    def test_os_legada_sem_base_nao_permite_restauracao(self):
        ordem = self.criar()
        OrdemServico.objects.filter(pk=ordem.pk).update(prioridade_herdada_conhecida=False, prioridade_origem='convertida')
        response = self.client.post(reverse('ordens-servico-restaurar-prioridade', args=[ordem.pk]), {'justificativa': 'Rever legado'})
        self.assertEqual(response.status_code, 400)

    def test_heranca_e_preservada_por_alerta_tendencia_e_horimetro(self):
        plano = PlanoManutencao.objects.create(equipamento=self.equipamento, nome_servico='Lubrificar', descricao='Rotina', intervalo_horas=100, prioridade='critica')
        self.equipamento.horimetro = 110
        self.equipamento.save()
        programada = OrdemServico.objects.get(titulo__contains=plano.nome_servico)
        self.assertEqual(programada.prioridade, 'B')
        alerta = Alerta.objects.create(equipamento=self.equipamento, tipo_alerta='Temperatura', descricao='Quente', nivel='baixo')
        ordem = PrioridadeOSService.criar_por_alerta(alerta)
        self.assertEqual(ordem.prioridade, 'B')
        alerta.nivel = 'critico'
        alerta.save()
        ordem.refresh_from_db()
        self.assertEqual(ordem.prioridade, 'B')
        tendencia = Alerta.objects.create(equipamento=self.equipamento, tipo_alerta='Tendência', descricao='Subindo', origem='tendencia',
            dados_analise={'intervention_recommended': True, 'risk_level': 'medio'})
        preditiva = PrioridadeOSService.criar_por_tendencia(tendencia)
        aplicar_criticidade(self.equipamento, 'A', 'Mudança operacional.', self.gestor)
        tendencia.dados_analise['risk_level'] = 'critico'
        tendencia.save()
        PrioridadeOSService.criar_por_tendencia(tendencia)
        preditiva.refresh_from_db()
        self.assertEqual(preditiva.prioridade, 'B')
        self.assertEqual(preditiva.gravidade_condicao, 'critica')

    def test_ordenacao_antes_da_paginacao_e_filtros_compartilhados_com_exportacao(self):
        self.equipamento.criticidade = 'C'
        self.equipamento.save()
        for i in range(25):
            self.criar()
        self.equipamento.criticidade = 'A'
        self.equipamento.save()
        mais_antiga = self.criar(data_abertura=timezone.now() - timedelta(days=10))
        self.criar(status='cancelada')
        response = self.client.get(self.url, {'abertas': 'true', 'limit': 3})
        self.assertEqual(response.data['results'][0]['id'], mais_antiga.pk)
        self.assertEqual(response.data['count'], 26)
        self.assertIn('abertas=true', response.data['next'])
        filtered = self.client.get(self.url, {'abertas': 'true', 'prioridade': 'A'})
        self.assertEqual(filtered.data['count'], 1)
        exported = self.client.get('/api/exportar/ordens-servico/csv/', {'abertas': 'true', 'prioridade': 'A'})
        self.assertEqual(exported.status_code, 200)
        rows = list(csv.reader(io.StringIO(exported.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(mais_antiga.pk))
        self.assertEqual(rows[1][5], 'A — Alta')
        dashboard = self.client.get('/api/dashboards/resumo/')
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(dashboard.data['ordens_prioritarias'][0]['id'], mais_antiga.pk)

    def test_a_definir_tem_filtro_e_nao_e_tratada_como_classe_c(self):
        self.equipamento.criticidade = None
        self.equipamento.save()
        ordem = self.criar()
        response = self.client.get(self.url, {'prioridade': 'a_definir'})
        self.assertEqual(response.data['a_definir'], 1)
        self.assertIsNone(response.data['results'][0]['prioridade'])
        self.assertEqual(response.data['results'][0]['id'], ordem.pk)
        self.assertEqual(self.client.get(self.url, {'prioridade': 'C'}).data['count'], 0)

    def test_exportacao_respeita_visibilidade_do_tecnico(self):
        livre = self.criar()
        self.criar(responsavel=self.gestor)
        self.client.force_authenticate(self.tecnico)
        response = self.client.get('/api/exportar/ordens-servico/csv/')
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(livre.pk))
