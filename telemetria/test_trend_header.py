"""Contexto e medição atual independem da amostra operacional de tendência."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from .models import Sensor, Telemetria, TrendConfig
from .trend_analysis import analyze_sensor_trend
from .views import TrendDashboardView


class TrendHeaderTests(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nome='Metalúrgica', cnpj='HEADER', email='contato@example.com')
        self.equipment = Equipamento.objects.create(empresa=self.company, nome='Motor principal', numero_serie='SN-HEADER')
        self.sensor = Sensor.objects.create(equipamento=self.equipment, nome='Temperatura',
            tipo='temperatura', unidade_medida='°C', limite_alerta=100)

    def test_setor_e_ultima_leitura_zero_com_analise_desativada(self):
        EquipamentoLocalizacao.objects.create(equipamento=self.equipment, setor='Linha de produção')
        TrendConfig.objects.create(sensor=self.sensor, ativo=False)
        reading = Telemetria.objects.create(sensor=self.sensor, valor=0)
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual(result['sensor_info']['setor'], 'Linha de produção')
        self.assertEqual(result['latest_reading'], dict(id=reading.pk, valor=0, timestamp=reading.timestamp.isoformat()))
        self.assertIsNone(result['current_value'])
        self.assertFalse(result['analysis_enabled'])
        self.assertEqual(result['config_used']['source'], 'sensor')

    def test_leitura_antiga_fora_da_janela_e_futura_nao_substitui_a_atual(self):
        old = Telemetria.objects.create(sensor=self.sensor, valor=25)
        stamp = timezone.now() - timedelta(days=3)
        Telemetria.objects.filter(pk=old.pk).update(timestamp=stamp)
        future = Telemetria.objects.create(sensor=self.sensor, valor=80)
        Telemetria.objects.filter(pk=future.pk).update(timestamp=timezone.now() + timedelta(hours=1))
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual(result['latest_reading']['id'], old.pk)
        self.assertEqual(result['latest_reading']['timestamp'], stamp.isoformat())
        self.assertEqual(result['readings_summary'], [])
        self.assertIsNone(result['current_value'])
        self.assertTrue(result['insufficient_data'])

    def test_sem_localizacao_e_sem_telemetria_retorna_null(self):
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertIsNone(result['sensor_info']['setor'])
        self.assertIsNone(result['latest_reading'])
        self.assertEqual(result['config_used']['source'], 'padrao')

    def test_empate_de_horario_utiliza_maior_id(self):
        first = Telemetria.objects.create(sensor=self.sensor, valor=10)
        last = Telemetria.objects.create(sensor=self.sensor, valor=20)
        Telemetria.objects.filter(pk=last.pk).update(timestamp=first.timestamp)
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual(result['latest_reading']['id'], last.pk)
        self.assertEqual(result['latest_reading']['valor'], 20)

    def test_endpoint_preserva_escopo_e_configuracao_global(self):
        TrendConfig.objects.create(ativo=False, duracao_minima_minutos=45)
        Telemetria.objects.create(sensor=self.sensor, valor=12)
        factory = APIRequestFactory()
        for company, expected in [(self.company, 200),
            (Empresa.objects.create(nome='Outra', cnpj='OUTRA-HEADER', email='outra@example.com'), 404)]:
            user = Usuario.objects.create_user(username=f'gestor{company.pk}', empresa=company, tipo_usuario='gestor')
            request = factory.get('/api/telemetria/tendencias/', {'sensor_id': self.sensor.pk})
            force_authenticate(request, user=user)
            response = TrendDashboardView.as_view()(request)
            self.assertEqual(response.status_code, expected)
            if expected == 200:
                self.assertEqual(response.data['config_used']['source'], 'global')
                self.assertEqual(response.data['config_used']['duracao_minima_minutos'], 45)
                self.assertEqual(response.data['latest_reading']['valor'], 12)
