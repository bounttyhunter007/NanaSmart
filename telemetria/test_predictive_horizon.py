"""Critérios de abertura e preservação da previsão que originou a O.S."""
from copy import deepcopy
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Usuario
from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from .models import Sensor, Telemetria, TrendConfig
from .predictive_service import sync_sensor_trend
from .serializers import TrendConfigSerializer
from .trend_analysis import get_effective_config


class PredictiveHorizonTests(APITestCase):
    def setUp(self):
        self.clock = timezone.now()
        company = Empresa.objects.create(nome='Previsão', cnpj='HORIZON', email='qa@example.test')
        equipment = Equipamento.objects.create(empresa=company, nome='Compressor', numero_serie='HORIZON', criticidade='B')
        self.sensor = Sensor.objects.create(equipamento=equipment, nome='Temperatura', tipo='temperatura',
                                            unidade_medida='°C', limite_alerta=100)
        self.user = Usuario.objects.create_user(username='horizon', tipo_usuario='gestor', empresa=company)
        self.client.force_authenticate(self.user)

    def readings(self, values, minutes=60, end=None):
        end = end or self.clock
        rows = Telemetria.objects.bulk_create([Telemetria(sensor=self.sensor, valor=v) for v in values])
        for index, row in enumerate(rows):
            Telemetria.objects.filter(pk=row.pk).update(
                timestamp=end - timedelta(minutes=(len(values) - 1 - index) * minutes))

    def sync(self):
        with patch('django.utils.timezone.now', return_value=self.clock):
            return sync_sensor_trend(self.sensor.pk)

    def test_defaults_and_exact_two_hour_forecast_create_one_order(self):
        config = get_effective_config(self.sensor)
        self.assertEqual(config['duracao_minima_minutos'], 120)
        self.assertEqual(config['antecedencia_os_minutos'], 120)
        self.readings([60, 70, 80])
        for _ in range(2):
            result = self.sync()
            self.assertTrue(result['intervention_recommended'])
            self.assertEqual(result['projected_breach_minutes'], 120)
            self.assertEqual(result['projected_breach_at'], (self.clock + timedelta(hours=2)).isoformat())
        self.assertEqual(OrdemServico.objects.count(), 1)
        self.assertEqual(OrdemServico.objects.get().prioridade, 'B')

    def test_many_readings_cannot_replace_two_hours(self):
        self.readings([60 + index * .02 for index in range(1000)], minutes=.01)
        self.assertTrue(self.sync()['insufficient_data'])
        self.assertFalse(OrdemServico.objects.exists())

    def test_thousands_of_readings_keep_coverage_and_verify_originals(self):
        self.readings([50 + index * .025 for index in range(1201)], minutes=.1)
        result = self.sync()
        self.assertEqual(result['source_readings_count'], 1201)
        self.assertEqual(result['readings_count'], 50)
        self.assertEqual(result['sample_duration_minutes'], 120)
        self.assertTrue(result['intervention_recommended'])
        self.assertEqual(result['source_persistence_ratio'], 1)

    def test_rounding_does_not_make_forecast_inside_horizon(self):
        self.readings([60, 70, 79.9999])
        result = self.sync()
        self.assertEqual(result['projected_breach_minutes'], 120)  # apresentação arredondada
        self.assertFalse(result['intervention_recommended'])
        self.assertEqual(result['intervention_reason'], 'outside_horizon')
        self.assertEqual(Alerta.objects.count(), 1)
        self.assertFalse(OrdemServico.objects.exists())

    def test_expired_projection_does_not_create_order(self):
        self.readings([60, 70, 80], end=self.clock - timedelta(hours=3))
        result = self.sync()
        self.assertEqual(result['intervention_reason'], 'expired_projection')
        self.assertFalse(OrdemServico.objects.exists())

    def test_reached_limit_is_not_a_new_predictive_order(self):
        self.readings([80, 90, 100])
        result = self.sync()
        self.assertEqual(result['intervention_reason'], 'limit_reached')
        self.assertFalse(OrdemServico.objects.exists())

    def test_saved_duration_is_preserved_and_horizon_can_be_changed(self):
        config = TrendConfig.objects.create(sensor=self.sensor, duracao_minima_minutos=30)
        self.readings([40, 50, 60])
        self.assertFalse(self.sync()['intervention_recommended'])
        config.antecedencia_os_minutos = 240
        config.save()
        self.assertTrue(self.sync()['intervention_recommended'])
        config.refresh_from_db()
        self.assertEqual(config.duracao_minima_minutos, 30)

    def test_order_freezes_eligible_analysis_not_previous_alert_detection(self):
        self.readings([30, 40, 50])
        self.sync()
        alert = Alerta.objects.get()
        self.assertFalse(OrdemServico.objects.exists())
        Telemetria.objects.all().delete()
        self.clock += timedelta(minutes=30)
        self.readings([60, 70, 80])
        self.sync()
        order = OrdemServico.objects.get()
        frozen = deepcopy(order.evidencia_preditiva)
        self.assertEqual(alert.dados_deteccao['analise']['current_value'], 50)
        self.assertEqual(frozen['analise']['current_value'], 80)
        self.assertEqual(frozen['analise']['config_used']['antecedencia_os_minutos'], 120)
        self.assertIn('100 °C', frozen['resumo'])
        self.assertEqual(frozen['leituras'][-1]['timestamp'], self.clock.isoformat())
        # A projeção se afasta; o episódio e a ordem continuam os mesmos.
        Telemetria.objects.all().delete()
        self.clock += timedelta(minutes=10)
        self.readings([65, 70, 75])
        self.assertFalse(self.sync()['intervention_recommended'])
        order.refresh_from_db()
        self.assertEqual(order.evidencia_preditiva, frozen)
        self.assertEqual(Alerta.objects.get().pk, alert.pk)
        self.assertEqual(OrdemServico.objects.count(), 1)
        order.evidencia_preditiva = {}
        with self.assertRaises(ValidationError):
            order.save()

    def test_api_exposes_evidence_but_cannot_overwrite_it(self):
        self.readings([60, 70, 80])
        self.sync()
        order = OrdemServico.objects.get()
        response = self.client.patch(f'/api/ordens-servico/{order.pk}/',
                                     {'evidencia_preditiva': {'forged': True}}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['evidencia_preditiva'], order.evidencia_preditiva)
        order.refresh_from_db()
        self.assertNotIn('forged', order.evidencia_preditiva)

    def test_analysis_get_is_read_only_and_periodic_command_creates_order(self):
        self.readings([60, 70, 80])
        response = self.client.get(f'/api/telemetria/tendencias/?sensor_id={self.sensor.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['intervention_recommended'])
        self.assertFalse(Alerta.objects.exists())
        with patch('django.utils.timezone.now', return_value=self.clock):
            call_command('analisar_tendencias', stdout=StringIO())
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_invalid_horizons_are_rejected_and_partial_updates_preserve_values(self):
        for value in (0, -1, 'não numérico', 1.5):
            with self.subTest(value=value):
                serializer = TrendConfigSerializer(data={'sensor': self.sensor.pk, 'antecedencia_os_minutos': value})
                self.assertFalse(serializer.is_valid())
        config = TrendConfig.objects.create(sensor=self.sensor, duracao_minima_minutos=30, antecedencia_os_minutos=480)
        serializer = TrendConfigSerializer(config, data={'ativo': False}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(get_effective_config(self.sensor)['antecedencia_os_minutos'], 480)


class TrendConfigMigrationTests(TransactionTestCase):
    def test_new_fields_preserve_saved_durations(self):
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([('telemetria', '0003_trenddemo')])
            old_apps = executor.loader.project_state([('telemetria', '0003_trenddemo')]).apps
            config = old_apps.get_model('telemetria', 'TrendConfig').objects.create(duracao_minima_minutos=30)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            saved = TrendConfig.objects.get(pk=config.pk)
            self.assertEqual(saved.duracao_minima_minutos, 30)
            self.assertEqual(saved.antecedencia_os_minutos, 120)
            self.assertEqual(TrendConfig().duracao_minima_minutos, 120)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
