from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ativos.models import Empresa, Equipamento
from .models import Sensor, Telemetria, TrendConfig
from .trend_analysis import analyze_sensor_trend, get_effective_config
from .serializers import TrendConfigSerializer
from .predictive_service import sync_sensor_trend
from alertas.models import Alerta
from manutencao.models import OrdemServico


class TrendAnalysisRulesTests(TestCase):
    def setUp(self):
        empresa = Empresa.objects.create(nome='Trend Co', cnpj='TREND-TEST', email='trend@test.local')
        equipamento = Equipamento.objects.create(
            empresa=empresa, nome='Motor Trend', numero_serie='TREND-001'
        )
        self.sensor = Sensor.objects.create(
            equipamento=equipamento, nome='Temperatura', tipo='temperatura',
            unidade_medida='C', limite_alerta=100,
        )

    def _readings(self, values, start=None, step_minutes=30):
        start = start or (timezone.now() - timedelta(hours=2))
        leituras = Telemetria.objects.bulk_create([
            Telemetria(sensor=self.sensor, valor=value,
                       timestamp=start + timedelta(minutes=index * step_minutes))
            for index, value in enumerate(values)
        ])
        # auto_now_add substitui timestamp também no bulk_create.
        # Ajustar o relógio da fixture permite testar intervalos reais.
        for index, leitura in enumerate(leituras):
            Telemetria.objects.filter(pk=leitura.pk).update(
                timestamp=start + timedelta(minutes=index * step_minutes)
            )

    def test_uses_the_most_recent_readings(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3, periodo_horas=24)
        self._readings([10, 11, 12, 20, 30])
        result = analyze_sensor_trend(self.sensor.id)
        self.assertEqual(result['readings_count'], 3)
        self.assertEqual([item['valor'] for item in result['readings_summary']], [12, 20, 30])
        self.assertEqual(result['direction'], 'increasing')

    def test_insufficient_data_has_no_projection(self):
        self._readings([40, 41])
        result = analyze_sensor_trend(self.sensor.id)
        self.assertTrue(result['insufficient_data'])
        self.assertIsNone(result['projected_breach_hours'])
        self.assertFalse(result['intervention_recommended'])

    def test_decreasing_series_is_not_upper_limit_breach(self):
        self._readings([90, 80, 70, 60])
        result = analyze_sensor_trend(self.sensor.id)
        self.assertEqual(result['direction'], 'decreasing')
        self.assertIsNone(result['projected_breach_hours'])

    def test_irregular_intervals_are_measured_in_hours(self):
        start = timezone.now() - timedelta(hours=4)
        self._readings([50, 60, 70], start=start, step_minutes=90)
        result = analyze_sensor_trend(self.sensor.id)
        self.assertGreater(result['slope_per_hour'], 0)
        self.assertEqual(result['data_quality'], 'valid')

    def test_relevant_trend_creates_one_predictive_alert_and_work_order(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3, periodo_horas=24)
        self._readings([80, 90, 98])
        sync_sensor_trend(self.sensor.id)
        sync_sensor_trend(self.sensor.id)
        self.assertEqual(Alerta.objects.filter(sensor=self.sensor, origem='tendencia', status='ativo').count(), 1)
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva', alerta_origem__sensor=self.sensor).count(), 1)

    def test_stable_follow_up_resolves_active_trend(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3, periodo_horas=24)
        start = timezone.now() - timedelta(hours=2)
        self._readings([80, 90, 98], start=start)
        sync_sensor_trend(self.sensor.id)
        self._readings([50, 50, 50], start=timezone.now() - timedelta(minutes=40), step_minutes=15)
        sync_sensor_trend(self.sensor.id)
        self.assertFalse(Alerta.objects.filter(sensor=self.sensor, origem='tendencia', status='ativo').exists())
        self.assertTrue(Alerta.objects.filter(sensor=self.sensor, origem='tendencia', status='resolvido').exists())
        self.assertEqual(OrdemServico.objects.get(tipo_os='preditiva').status, 'pendente')

    def test_predictive_order_is_linked_and_not_recreated_after_conclusion(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3, periodo_horas=24)
        self._readings([80, 90, 98])
        sync_sensor_trend(self.sensor.id)
        alerta = Alerta.objects.get(sensor=self.sensor, origem='tendencia', status='ativo')
        ordem = OrdemServico.objects.get(alerta_origem=alerta)
        self.assertEqual(alerta.ordem_servico_id, ordem.pk)
        ordem.status = 'concluida'
        ordem.save()
        sync_sensor_trend(self.sensor.id)
        alerta.refresh_from_db()
        ordem.refresh_from_db()
        self.assertEqual(alerta.status, 'ativo')
        self.assertEqual(ordem.status, 'concluida')
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_configured_minimum_is_required_even_with_valid_slope(self):
        TrendConfig.objects.create(sensor=self.sensor, minimo_leituras=5)
        self._readings([10, 20, 30, 40])
        result = sync_sensor_trend(self.sensor.pk)
        self.assertTrue(result['insufficient_data'])
        self.assertFalse(Alerta.objects.exists())
        self.assertFalse(OrdemServico.objects.exists())

    def test_minimum_and_maximum_are_independent(self):
        TrendConfig.objects.create(sensor=self.sensor, minimo_leituras=4, num_leituras=5)
        self._readings([10, 20, 30, 40])
        result = sync_sensor_trend(self.sensor.pk)
        self.assertFalse(result['insufficient_data'])
        self.assertEqual(result['readings_count'], 4)
        self.assertTrue(result['is_anomalous'])

    def test_burst_does_not_trigger_prediction(self):
        self._readings([10, 20, 30], start=timezone.now() - timedelta(minutes=2), step_minutes=0.5)
        result = sync_sensor_trend(self.sensor.pk)
        self.assertTrue(result['insufficient_data'])
        self.assertFalse(OrdemServico.objects.exists())

    def test_confirmed_trend_opens_order_before_limit_or_warning_threshold(self):
        self._readings([10, 20, 30])
        result = sync_sensor_trend(self.sensor.pk)
        order = OrdemServico.objects.get(tipo_os='preditiva')
        alert = Alerta.objects.get(origem='tendencia')
        self.assertLess(result['current_value'], self.sensor.limite_alerta * 0.7)
        self.assertEqual(order.sensor_origem_id, self.sensor.pk)
        self.assertEqual(alert.equipamento_id, self.sensor.equipamento_id)
        self.assertEqual(result['active_alert_id'], alert.pk)
        self.assertEqual(result['predictive_work_order']['id'], order.pk)
        self.assertIn(self.sensor.nome, alert.descricao)
        self.assertEqual(alert.dados_analise['config_used']['minimo_leituras'], 3)

    def test_far_from_limit_still_generates_inspection_order(self):
        self._readings([10, 11.5, 13])
        result = sync_sensor_trend(self.sensor.pk)
        self.assertGreater(result['projected_breach_hours'], 24)
        self.assertTrue(result['intervention_recommended'])
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)

    def test_decreasing_anomaly_opens_order_only_when_configured(self):
        self._readings([60, 50, 40])
        self.assertFalse(sync_sensor_trend(self.sensor.pk)['is_anomalous'])
        self.assertFalse(Alerta.objects.exists())
        TrendConfig.objects.create(sensor=self.sensor, direcao_alerta='decrescente')
        result = sync_sensor_trend(self.sensor.pk)
        self.assertTrue(result['is_anomalous'])
        self.assertIsNone(result['projected_breach_hours'])
        self.assertIn('redução persistente', Alerta.objects.get().descricao)
        self.assertEqual(OrdemServico.objects.get().tipo_os, 'preditiva')

    def test_direction_change_creates_new_episode(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3, direcao_alerta='ambas')
        self._readings([10, 20, 30], start=timezone.now() - timedelta(hours=3))
        sync_sensor_trend(self.sensor.pk)
        first = Alerta.objects.get()
        self._readings([60, 50, 40], start=timezone.now() - timedelta(hours=1), step_minutes=20)
        result = sync_sensor_trend(self.sensor.pk)
        first.refresh_from_db()
        self.assertEqual(first.status, 'resolvido')
        self.assertEqual(result['direction'], 'decreasing')
        self.assertEqual(Alerta.objects.filter(status='ativo').count(), 1)
        self.assertEqual(OrdemServico.objects.count(), 2)

    def test_sensor_disable_overrides_enabled_global_without_resolving_episode(self):
        TrendConfig.objects.create(ativo=True)
        config = TrendConfig.objects.create(sensor=self.sensor)
        self._readings([10, 20, 30])
        sync_sensor_trend(self.sensor.pk)
        config.ativo = False
        config.save()
        result = sync_sensor_trend(self.sensor.pk)
        self.assertFalse(result['analysis_enabled'])
        self.assertEqual(result['data_quality'], 'disabled')
        self.assertEqual(Alerta.objects.get().status, 'ativo')
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_disabled_global_does_not_fall_back_to_defaults(self):
        TrendConfig.objects.create(ativo=False)
        self._readings([10, 20, 30])
        self.assertFalse(sync_sensor_trend(self.sensor.pk)['analysis_enabled'])
        self.assertFalse(Alerta.objects.exists())

    def test_specific_config_overrides_global_and_latest_global_wins(self):
        TrendConfig.objects.create(sensibilidade='alta')
        TrendConfig.objects.create(sensibilidade='baixa')
        self.assertEqual(get_effective_config(self.sensor)['sensibilidade'], 'baixa')
        TrendConfig.objects.create(sensor=self.sensor, sensibilidade='media')
        config = get_effective_config(self.sensor)
        self.assertEqual(config['sensibilidade'], 'media')
        self.assertEqual(config['source'], 'sensor')

    def test_single_spike_and_oscillation_are_not_persistent(self):
        for values in ([10, 10, 10, 10, 60], [10, 50, 20, 60, 30]):
            with self.subTest(values=values):
                Telemetria.objects.all().delete()
                self._readings(values)
                result = sync_sensor_trend(self.sensor.pk)
                self.assertEqual(result['direction'], 'stable')
                self.assertFalse(result['is_anomalous'])
                self.assertFalse(Alerta.objects.exists())

    def test_persistence_is_checked_independently_of_fit(self):
        config = TrendConfig.objects.create(sensor=self.sensor, persistencia_minima=1, r2_minimo=0.5)
        self._readings([10, 20, 19, 30, 40])
        result = sync_sensor_trend(self.sensor.pk)
        self.assertGreater(result['r_squared'], 0.8)
        self.assertEqual(result['persistence_ratio'], 0.75)
        self.assertFalse(result['is_anomalous'])
        config.persistencia_minima = 0.75
        config.save()
        self.assertTrue(sync_sensor_trend(self.sensor.pk)['is_anomalous'])

    def test_duplicates_do_not_consume_reading_budget(self):
        TrendConfig.objects.create(sensor=self.sensor, num_leituras=3)
        self._readings([10, 20, 30])
        last = Telemetria.objects.first()
        for _ in range(10):
            reading = Telemetria.objects.bulk_create([Telemetria(sensor=self.sensor, valor=30)])[0]
            Telemetria.objects.filter(pk=reading.pk).update(timestamp=last.timestamp)
        result = sync_sensor_trend(self.sensor.pk)
        self.assertEqual(result['readings_count'], 3)
        self.assertEqual([r['valor'] for r in result['readings_summary']], [10, 20, 30])
        self.assertTrue(result['is_anomalous'])

    def test_invalid_old_and_future_readings_are_excluded(self):
        self._readings([10, 20, 30])
        for value, stamp in ((float('inf'), timezone.now()), (90, timezone.now() + timedelta(hours=1)),
                             (90, timezone.now() - timedelta(hours=25))):
            reading = Telemetria.objects.bulk_create([Telemetria(sensor=self.sensor, valor=value)])[0]
            Telemetria.objects.filter(pk=reading.pk).update(timestamp=stamp)
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual([r['valor'] for r in result['readings_summary']], [10, 20, 30])

    def test_expired_data_does_not_resolve_active_episode(self):
        self._readings([10, 20, 30])
        sync_sensor_trend(self.sensor.pk)
        Telemetria.objects.update(timestamp=timezone.now() - timedelta(hours=25))
        self.assertTrue(sync_sensor_trend(self.sensor.pk)['insufficient_data'])
        self.assertEqual(Alerta.objects.get().status, 'ativo')

    def test_real_ingestion_triggers_alert_and_order(self):
        self._readings([10, 20], start=timezone.now() - timedelta(hours=1))
        Telemetria.objects.create(sensor=self.sensor, valor=30)
        self.assertEqual(Alerta.objects.filter(origem='tendencia').count(), 1)
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)

    def test_periodic_command_is_idempotent_and_get_analysis_is_read_only(self):
        self._readings([10, 20, 30])
        analyze_sensor_trend(self.sensor.pk)
        self.assertFalse(Alerta.objects.exists())
        for _ in range(2):
            call_command('analisar_tendencias', stdout=StringIO())
        self.assertEqual(Alerta.objects.count(), 1)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_sensitivity_threshold_changes_detection(self):
        config = TrendConfig.objects.create(sensor=self.sensor, sensibilidade='baixa')
        self._readings([10, 12, 14])  # 4 unidades/h; limiares: 0,5 / 2 / 5.
        self.assertFalse(sync_sensor_trend(self.sensor.pk)['is_anomalous'])
        config.sensibilidade = 'media'
        config.save()
        self.assertTrue(sync_sensor_trend(self.sensor.pk)['is_anomalous'])

    def test_invalid_criteria_are_rejected_in_model_and_api(self):
        for values in ({'minimo_leituras': 2}, {'minimo_leituras': 51}, {'num_leituras': 501},
                       {'periodo_horas': 0}, {'duracao_minima_minutos': 0},
                       {'duracao_minima_minutos': 1441}, {'persistencia_minima': 0.49},
                       {'r2_minimo': float('inf')}, {'r2_minimo': float('nan')}):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    TrendConfig.objects.create(sensor=self.sensor, **values)
                serializer = TrendConfigSerializer(data={'sensor': self.sensor.pk, **values})
                self.assertFalse(serializer.is_valid())

    def test_partial_update_validates_against_existing_criteria(self):
        config = TrendConfig.objects.create(sensor=self.sensor, minimo_leituras=20)
        serializer = TrendConfigSerializer(config, data={'num_leituras': 10}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('minimo_leituras', serializer.errors)

    def test_window_and_duration_boundaries_are_inclusive(self):
        now = timezone.now()
        TrendConfig.objects.create(sensor=self.sensor, periodo_horas=1, duracao_minima_minutos=60)
        self._readings([10, 20, 30], start=now - timedelta(hours=1))
        with patch('telemetria.trend_analysis.timezone.now', return_value=now):
            result = analyze_sensor_trend(self.sensor.pk)
        self.assertFalse(result['insufficient_data'])
        self.assertEqual(result['sample_duration_minutes'], 60)

class TrendPresentationTests(TestCase):
    setUp = TrendAnalysisRulesTests.setUp
    _readings = TrendAnalysisRulesTests._readings

    def test_regression_line_uses_sample_times_and_centered_full_precision_fit(self):
        start = timezone.now() - timedelta(hours=3)
        self._readings([40, 61, 70], start=start, step_minutes=45)
        result = analyze_sensor_trend(self.sensor.pk)
        line = result['regression_line']
        self.assertEqual(len(line), 2)
        self.assertEqual(line[0]['timestamp'], result['readings_summary'][0]['timestamp'])
        self.assertEqual(line[-1]['timestamp'], result['readings_summary'][-1]['timestamp'])
        self.assertAlmostEqual((line[0]['valor'] + line[-1]['valor']) / 2, (40 + 61 + 70) / 3)
        self.assertAlmostEqual(line[-1]['valor'] - line[0]['valor'], 30)

    def test_forecast_date_is_anchored_to_last_measurement_not_query_clock(self):
        clock = timezone.now()
        self._readings([40, 50, 60], start=clock - timedelta(hours=2))
        with patch('telemetria.trend_analysis.timezone.now', return_value=clock):
            first = analyze_sensor_trend(self.sensor.pk)
        with patch('telemetria.trend_analysis.timezone.now', return_value=clock + timedelta(minutes=10)):
            later = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual(first['projected_breach_at'], (clock + timedelta(hours=1)).isoformat())
        self.assertEqual(first['projected_breach_at'], later['projected_breach_at'])
        self.assertEqual(first['regression_line'], later['regression_line'])

    def test_insufficient_or_disabled_analysis_has_no_fitted_line_or_date(self):
        self._readings([40, 41])
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertIsNone(result['regression_line'])
        self.assertIsNone(result['projected_breach_at'])
        TrendConfig.objects.create(sensor=self.sensor, ativo=False)
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertIsNone(result['regression_line'])
        self.assertIsNone(result['projected_breach_at'])

    def test_decreasing_constant_or_poor_fit_has_no_forecast_date(self):
        for values in ([80, 70, 60], [50, 50, 50], [40, 60, 41, 59, 42]):
            Telemetria.objects.filter(sensor=self.sensor).delete()
            self._readings(values, start=timezone.now() - timedelta(hours=3))
            result = analyze_sensor_trend(self.sensor.pk)
            self.assertIsNotNone(result['regression_line'])
            self.assertIsNone(result['projected_breach_at'])

    def test_already_reached_limit_does_not_invent_future_date(self):
        self._readings([80, 100, 120])
        result = analyze_sensor_trend(self.sensor.pk)
        self.assertEqual(result['projected_breach_hours'], 0)
        self.assertIsNone(result['projected_breach_at'])
