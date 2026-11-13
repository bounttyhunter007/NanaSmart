from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Usuario
from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from manutencao.services import PrioridadeOSService
from telemetria.limit_service import sync_limit_reading
from telemetria.models import Sensor, Telemetria
from telemetria.predictive_service import sync_sensor_trend


class OrderAlertHistoryTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Histórico OS', cnpj='HOS', email='hos@example.com')
        self.equipamento = Equipamento.objects.create(
            empresa=self.empresa, nome='Bomba', numero_serie='HOS', criticidade='B')
        self.sensor = Sensor.objects.create(equipamento=self.equipamento, nome='Pressão',
            tipo='pressao', unidade_medida='bar', limite_alerta=100)
        self.gestor = Usuario.objects.create_user(username='hos', tipo_usuario='gestor', empresa=self.empresa)
        self.client.force_authenticate(self.gestor)
        self.inicio = timezone.now().replace(microsecond=0) - timedelta(hours=2)
        automatico = patch('telemetria.signals.sync_sensor_trend')
        automatico.start()
        self.addCleanup(automatico.stop)

    def leitura(self, valor, minuto):
        with patch('django.utils.timezone.now', return_value=self.inicio + timedelta(minutes=minuto)):
            return Telemetria.objects.create(sensor=self.sensor, valor=valor)

    def detalhe(self, ordem):
        response = self.client.get(reverse('ordens-servico-detail', args=[ordem.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_abertura_e_duas_elevacoes_preservam_datas_e_niveis_na_os_e_lista(self):
        self.leitura(70, 0)
        alerta = Alerta.objects.get()
        evidencia = alerta.dados_deteccao.copy()
        self.leitura(85, 3)
        self.leitura(100, 7)
        alerta.refresh_from_db()
        eventos = alerta.historico_niveis
        self.assertEqual([(e['nivel_anterior'], e['nivel']) for e in eventos],
                         [('baixo', 'medio'), ('medio', 'critico')])
        self.assertEqual([e['ocorrido_em'] for e in eventos],
                         [(self.inicio + timedelta(minutes=m)).isoformat() for m in (3, 7)])
        self.assertEqual(alerta.dados_deteccao, evidencia)
        ordem = alerta.ordem_servico
        self.assertEqual(ordem.prioridade, 'B')
        self.assertEqual(ordem.criticidade_na_abertura, 'B')
        self.assertEqual(ordem.descricao.count('[ELEVAÇÃO DO ALERTA'), 2)
        self.assertIn('Baixo → Médio', ordem.descricao)
        self.assertIn(timezone.localtime(self.inicio + timedelta(minutes=7)).strftime('%d/%m/%Y %H:%M:%S'), ordem.descricao)
        detalhe = self.detalhe(ordem)
        ocorrencia = detalhe['historico_alertas'][0]
        self.assertEqual(ocorrencia['nivel_inicial'], 'baixo')
        self.assertEqual(ocorrencia['nivel_maximo'], 'critico')
        self.assertFalse(ocorrencia['historico_incompleto'])
        self.assertEqual(len(ocorrencia['historico_niveis']), 2)
        lista = self.client.get(reverse('ordens-servico-list')).data['results']
        self.assertEqual(lista[0]['historico_alertas'], detalhe['historico_alertas'])

    def test_repeticao_queda_e_reprocessamento_nao_duplicam_os_registros(self):
        self.leitura(70, 0)
        self.leitura(100, 1)
        self.leitura(75, 2)
        ultima = self.leitura(100, 3)
        alerta = Alerta.objects.get()
        descricao = alerta.ordem_servico.descricao
        sync_limit_reading(ultima)
        PrioridadeOSService.criar_por_alerta(alerta)
        alerta.historico_niveis = []
        alerta.save(update_fields=['descricao', 'historico_niveis'])
        alerta.refresh_from_db()
        self.assertEqual(len(alerta.historico_niveis), 1)
        self.assertEqual(alerta.ordem_servico.descricao, descricao)

    def test_recorrencia_inferior_ao_pico_da_os_tambem_registra_elevacao(self):
        for minuto, valor in enumerate((100, 10, 10, 70, 85)):
            self.leitura(valor, minuto)
        ordem = OrdemServico.objects.get()
        ocorrencias = self.detalhe(ordem)['historico_alertas']
        self.assertEqual(len(ocorrencias), 2)
        self.assertIsNotNone(ocorrencias[0]['data_normalizacao'])
        self.assertEqual(ocorrencias[1]['historico_niveis'][0]['nivel'], 'medio')
        self.assertIn('Baixo → Médio', ordem.descricao)
        self.assertEqual(ordem.descricao.count('[ABERTURA DO ALERTA'), 2)

    def test_ordem_encerrada_preserva_descricao_e_expoe_evolucao_do_alerta(self):
        self.leitura(70, 0)
        ordem = OrdemServico.objects.get()
        ordem.status = 'concluida'
        ordem.save()
        descricao = ordem.descricao
        self.leitura(100, 2)
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, 'concluida')
        self.assertEqual(ordem.descricao, descricao)
        self.assertEqual(OrdemServico.objects.count(), 1)
        self.assertEqual(self.detalhe(ordem)['historico_alertas'][0]['historico_niveis'][0]['nivel'], 'critico')

    def test_preditiva_preserva_texto_original_e_historico_sem_duplicacao(self):
        trend = dict(analysis_enabled=True, insufficient_data=False, is_anomalous=True,
            direction='increasing', risk_level='baixo', intervention_recommended=True,
            readings_count=3, sample_duration_minutes=30, r_squared=.98,
            persistence_ratio=1, slope_per_hour=1, current_value=60, projected_breach_hours=40)
        with patch('telemetria.predictive_service.analyze_sensor_trend', side_effect=lambda _: trend.copy()):
            with patch('django.utils.timezone.now', return_value=self.inicio):
                sync_sensor_trend(self.sensor.pk)
            ordem = OrdemServico.objects.get()
            original = ordem.descricao
            trend.update(risk_level='critico', current_value=95)
            with patch('django.utils.timezone.now', return_value=self.inicio + timedelta(minutes=5)):
                sync_sensor_trend(self.sensor.pk)
                sync_sensor_trend(self.sensor.pk)
        ordem.refresh_from_db()
        self.assertTrue(ordem.descricao.startswith(original))
        self.assertEqual(ordem.descricao.count('[ELEVAÇÃO DO ALERTA'), 1)
        self.assertEqual(self.detalhe(ordem)['historico_alertas'][0]['historico_niveis'][0]['nivel'], 'critico')

    def test_lacuna_antiga_permanece_explicita_mesmo_apos_nova_elevacao(self):
        self.leitura(70, 0)
        Alerta.objects.update(nivel='medio')  # Simula pico anterior à migração.
        self.leitura(100, 3)
        ocorrencia = self.detalhe(OrdemServico.objects.get())['historico_alertas'][0]
        self.assertTrue(ocorrencia['historico_incompleto'])
        self.assertEqual(len(ocorrencia['historico_niveis']), 1)
        self.assertEqual(ocorrencia['historico_niveis'][0]['nivel_anterior'], 'medio')

    def test_alteracao_sem_nova_analise_nao_reutiliza_horario_antigo(self):
        self.leitura(70, 0)
        alerta = Alerta.objects.get()
        instante = self.inicio + timedelta(minutes=20)
        with patch('django.utils.timezone.now', return_value=instante):
            alerta.nivel = 'critico'
            alerta.save(update_fields=['nivel'])
        alerta.refresh_from_db()
        self.assertEqual(alerta.historico_niveis[0]['ocorrido_em'], instante.isoformat())

    def test_historico_nao_e_exposto_a_outra_empresa(self):
        self.leitura(70, 0)
        outra = Empresa.objects.create(nome='Outra', cnpj='OUTRA-HOS', email='outra@example.com')
        usuario = Usuario.objects.create_user(username='outro-hos', tipo_usuario='gestor', empresa=outra)
        self.client.force_authenticate(usuario)
        self.assertEqual(self.client.get(reverse('ordens-servico-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('ordens-servico-detail', args=[OrdemServico.objects.get().pk])).status_code, 404)

    def test_falha_na_atualizacao_da_os_reverte_elevacao_e_leitura(self):
        self.leitura(70, 0)
        with patch.object(PrioridadeOSService, 'criar_por_alerta', side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):
                self.leitura(100, 1)
        alerta = Alerta.objects.get()
        self.assertEqual(alerta.nivel, 'baixo')
        self.assertEqual(alerta.historico_niveis, [])
        self.assertEqual(Telemetria.objects.count(), 1)
        self.assertNotIn('[ELEVAÇÃO DO ALERTA', OrdemServico.objects.get().descricao)
