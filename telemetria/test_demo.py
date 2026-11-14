from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from .models import Sensor, Telemetria, TrendConfig, TrendDemo
from .demo_serializers import TrendDemoSnapshotSerializer
from scripts.simulador_realtime import obter_sensores_ativos


class TrendDemoTests(APITestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nome='Empresa demo', cnpj='DEMO-TEST', email='demo@test.local')
        self.admin = Usuario.objects.create_user(username='demo_admin', password='test', tipo_usuario='admin')
        self.client.force_authenticate(self.admin)
        self.start = timezone.now()
        self.url = reverse('trend-demo')

    def create(self, scenario='aumento'):
        with patch('django.utils.timezone.now', return_value=self.start):
            response = self.client.post(self.url, {'empresa': self.company.pk, 'cenario': scenario}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.demo_url = reverse('trend-demo-detail', args=[response.data['id']])
        return response.data

    def act(self, seconds, **data):
        with patch('django.utils.timezone.now', return_value=self.start + timedelta(seconds=seconds)):
            return self.client.post(self.demo_url, data or {'acao': 'avancar'}, format='json')

    def complete(self, start=0):
        result = None
        for seconds in range(start + 10, start + 61, 10):
            result = self.act(seconds)
            self.assertEqual(result.status_code, 200, result.data)
        return result.data

    def test_cadastros_tem_nomes_operacionais_e_vinculo_de_teste(self):
        data = self.create()
        demo = TrendDemo.objects.get(pk=data['id'])
        self.assertEqual(demo.sensor.nome, 'Temperatura do motor')
        self.assertEqual(demo.sensor.equipamento.nome, 'Motor de monitoramento')
        self.assertTrue(demo.sensor.equipamento.numero_serie.startswith('SN-'))
        self.assertNotIn(demo.sensor, obter_sensores_ativos())

    def test_demo_uses_real_clock_and_creates_predictive_order_before_warning_limit(self):
        data = self.create()
        self.assertTrue(data['analysis']['insufficient_data'])
        for _ in range(4):
            self.act(0)
        self.assertEqual(Telemetria.objects.count(), 1)
        data = self.complete()
        self.assertEqual(data['status'], 'concluido')
        self.assertEqual([row['valor'] for row in data['analysis']['readings_summary']], [40,42,44,46,48,50,52])
        self.assertEqual(data['analysis']['sample_duration_minutes'], 1)
        self.assertTrue(all(check['passed'] for check in data['analysis']['checks']))
        self.assertEqual(data['analysis']['threshold_per_hour'], 2)
        self.assertLess(data['analysis']['current_value'], 70)
        self.assertEqual(Alerta.objects.filter(origem='tendencia').count(), 1)
        self.assertEqual(Alerta.objects.filter(origem='limite').count(), 0)
        self.assertEqual(OrdemServico.objects.get().tipo_os, 'preditiva')
        self.act(100)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_stable_and_spike_scenarios_do_not_force_anomaly(self):
        for scenario in ('estavel', 'pico'):
            self.create(scenario)
            data = self.complete()
            self.assertFalse(data['analysis']['is_anomalous'])
            self.assertEqual(data['alertas'], [])
            self.assertEqual(data['ordens'], [])

    def test_crossing_and_recovery_distinguish_limit_and_trend_without_closing_work(self):
        self.create(); self.complete()
        self.assertEqual(self.act(70, acao='fase', cenario='limite').status_code, 200)
        data = self.complete(70)
        self.assertGreater(data['analysis']['current_value'], 100)
        self.assertEqual({alert['origem'] for alert in data['alertas']}, {'limite','tendencia'})
        self.assertEqual(len(data['ordens']), 2)
        self.act(140, acao='fase', cenario='recuperacao')
        data = self.complete(140)
        self.assertFalse(data['analysis']['is_anomalous'])
        self.assertFalse(Alerta.objects.filter(status='ativo').exists())
        self.assertEqual(set(OrdemServico.objects.values_list('status',flat=True)), {'pendente'})

    def test_only_admin_can_create_or_access_demo(self):
        self.create()
        for role in ('gestor','tecnico'):
            self.admin.tipo_usuario = role; self.admin.save()
            self.assertEqual(self.client.get(self.demo_url).status_code, 403)
            self.assertEqual(self.client.post(self.url, {'empresa':self.company.pk}).status_code, 403)

    def test_admin_cannot_advance_another_admin_demo(self):
        self.create()
        other = Usuario.objects.create_user(username='other', password='test', tipo_usuario='admin')
        self.client.force_authenticate(other)
        self.assertEqual(self.act(10).status_code, 404)
        self.assertEqual(Telemetria.objects.count(), 1)

    def test_invalid_inputs_do_not_create_data(self):
        for body in ({}, {'empresa':999999}, {'empresa':self.company.pk,'cenario':'invalid'}):
            self.assertEqual(self.client.post(self.url, body, format='json').status_code, 400)
        self.assertEqual(Equipamento.objects.count(), 0)

    def test_server_owns_values_timestamps_and_interval(self):
        data = self.create()
        response = self.act(1, valor=9999, timestamp='2099-01-01', acao='avancar')
        self.assertEqual(response.data['passo'], 1)
        self.assertEqual(Telemetria.objects.get().valor, 40)
        self.assertEqual(Telemetria.objects.get().timestamp, self.start)
        self.assertEqual(data['analysis']['config_used']['duracao_minima_minutos'], 1)

    def test_stop_and_phase_validation(self):
        self.create()
        self.assertEqual(self.act(1, acao='fase', cenario='limite').status_code, 400)
        self.assertEqual(self.act(1, acao='parar').data['status'], 'parado')
        self.act(60)
        self.assertEqual(Telemetria.objects.count(), 1)
        self.assertEqual(self.act(70, acao='fase', cenario='estavel').status_code, 200)

    def test_get_is_read_only_and_expiry_stops(self):
        self.create()
        for _ in range(2): self.client.get(self.demo_url)
        self.assertEqual(Telemetria.objects.count(), 1)
        self.assertEqual(self.act(1900).data['status'], 'parado')
        self.assertEqual(self.act(1910, acao='fase', cenario='aumento').status_code, 400)

    def test_snapshots_match_documented_response_before_and_after_alerts(self):
        created = self.create('limite')
        completed = self.complete()
        self.assertTrue(completed['alertas'])
        self.assertTrue(completed['ordens'])
        for payload in (created, completed):
            contract = TrendDemoSnapshotSerializer(data=payload)
            self.assertTrue(contract.is_valid(), contract.errors)
        self.assertEqual(self.client.get(self.demo_url).data['id'], created['id'])

    def test_latest_demo_without_history_preserves_empty_response(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

    def test_demo_does_not_change_real_sensor_or_global_and_script_ignores_demo(self):
        global_config = TrendConfig.objects.create(duracao_minima_minutos=30)
        equipment = Equipamento.objects.create(empresa=self.company,nome='Real',numero_serie='REAL')
        sensor = Sensor.objects.create(equipamento=equipment,nome='Real',tipo='temperatura',unidade_medida='C',limite_alerta=80)
        self.create()
        global_config.refresh_from_db(); sensor.refresh_from_db()
        self.assertEqual(global_config.duracao_minima_minutos,30)
        self.assertEqual(sensor.limite_alerta,80)
        self.assertEqual(list(obter_sensores_ativos()),[sensor])
        self.assertEqual(TrendDemo.objects.count(),1)
