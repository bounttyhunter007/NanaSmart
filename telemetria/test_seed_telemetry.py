"""Dados do seed: tempo irregular, variação suave e análise pelo fluxo real."""
import math
import random
from contextlib import redirect_stdout
from datetime import timedelta
from io import StringIO

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from scripts.seed_db import gerar_historico_sensor, salvar_telemetria_bulk, run_seed
from telemetria.models import Sensor, Telemetria
from telemetria.predictive_service import sync_sensor_trend
from telemetria.trend_analysis import analyze_sensor_trend


class SeedTelemetryShapeTests(SimpleTestCase):
    def test_irregular_intervals_stay_bounded_and_end_with_recent_data(self):
        now = timezone.now()
        rows = list(gerar_historico_sensor(35, 85, now - timedelta(days=2), now,
                                         rng=random.Random(4)))
        intervals = [(b[0] - a[0]).total_seconds() / 60 for a, b in zip(rows, rows[1:])]
        self.assertTrue(all(40 <= minutes <= 85 for minutes in intervals))
        self.assertGreater(len({round(minutes) for minutes in intervals}), 10)
        self.assertTrue(all(now - timedelta(days=2) <= stamp < now for stamp, _ in rows))
        self.assertTrue(2 <= (now - rows[-1][0]).total_seconds() / 60 <= 12)

    def test_long_histories_and_small_sensors_do_not_drift_to_a_flat_ceiling(self):
        now = timezone.now()
        for limit, minimum in [(7, .2), (12, 2), (85, 35), (150, 10)]:
            for profile in ['estavel', 'crescente', 'recuperacao']:
                with self.subTest(limit=limit, profile=profile):
                    rows = list(gerar_historico_sensor(minimum, limit, now - timedelta(days=120), now,
                                                     profile, random.Random(9)))
                    values = [value for _, value in rows]
                    self.assertTrue(all(math.isfinite(value) and minimum * .8 <= value <= limit * 1.1 for value in values))
                    self.assertLess(max(abs(b - a) for a, b in zip(values, values[1:])), limit * .06)
                    recent = [value for stamp, value in rows if stamp >= now - timedelta(hours=24)]
                    if profile == 'crescente':
                        self.assertGreater(recent[-1] - recent[0], limit * .45)
                    elif profile == 'recuperacao':
                        self.assertLess(recent[-1] - recent[0], -limit * .20)
                    else:
                        self.assertLess(max(recent) - min(recent), limit * .04)
                    self.assertGreater(len(set(values[-48:])), 30)

    def test_fixed_random_seed_reproduces_timestamps_and_values(self):
        now = timezone.now()
        args = (35, 85, now - timedelta(days=1), now, 'crescente')
        self.assertEqual(list(gerar_historico_sensor(*args, rng=random.Random(12))),
                         list(gerar_historico_sensor(*args, rng=random.Random(12))))


class SeedTelemetryIntegrationTests(TestCase):
    def setUp(self):
        company = Empresa.objects.create(nome='Seed', cnpj='SEED-TEST', email='seed@test.local')
        equipment = Equipamento.objects.create(empresa=company, nome='Motor', numero_serie='SEED-TEST')
        self.sensor = Sensor.objects.create(equipamento=equipment, nome='Temperatura', tipo='temperatura',
                                           unidade_medida='C', limite_alerta=100)

    def populate(self, profile):
        now = timezone.now()
        rows = list(gerar_historico_sensor(35, 100, now - timedelta(days=2), now,
                                         profile, random.Random(7)))
        salvar_telemetria_bulk([Telemetria(sensor=self.sensor, timestamp=stamp, valor=value)
                               for stamp, value in rows])
        self.assertEqual(list(Telemetria.objects.filter(sensor=self.sensor).order_by('timestamp').values_list('timestamp', 'valor')), rows)

    def test_rising_profile_is_detected_without_relaxing_operational_criteria(self):
        self.populate('crescente')
        self.assertFalse(Alerta.objects.exists())
        self.assertFalse(OrdemServico.objects.exists())
        result = sync_sensor_trend(self.sensor.pk)
        self.assertEqual(result['direction'], 'increasing')
        self.assertGreater(result['slope_per_hour'], 2)
        self.assertTrue(result['is_anomalous'])
        self.assertEqual(Alerta.objects.filter(origem='tendencia').count(), 1)
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)

    def test_stable_and_recovering_profiles_do_not_confirm_an_increase(self):
        for profile, direction in [('estavel', 'stable'), ('recuperacao', 'stable')]:
            with self.subTest(profile=profile):
                Telemetria.objects.all().delete()
                self.populate(profile)
                result = analyze_sensor_trend(self.sensor.pk)
                self.assertEqual(result['direction'], direction)
                self.assertFalse(result['is_anomalous'])
                if profile == 'recuperacao':
                    self.assertLess(result['slope_per_hour'], 0)

    def test_complete_small_seed_preserves_recent_history_without_artificial_final_spikes(self):
        with redirect_stdout(StringIO()):
            run_seed(num_empresas=1, equip_por_empresa=1, dias_historico=2, funcionarios_por_empresa=2)
        for sensor in Sensor.objects.all():
            rows = list(Telemetria.objects.filter(sensor=sensor).order_by('-timestamp')[:3])
            self.assertEqual(len(rows), 3)
            self.assertGreater((timezone.now() - rows[0].timestamp).total_seconds(), 60)
            self.assertTrue(all(abs(b.valor - a.valor) < sensor.limite_alerta * .06
                                for a, b in zip(rows, rows[1:])))
