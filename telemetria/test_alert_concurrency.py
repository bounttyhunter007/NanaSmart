from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from manutencao.services import PrioridadeOSService
from .models import Sensor, Telemetria
from .predictive_service import sync_sensor_trend


@skipUnlessDBFeature('has_select_for_update')
class AlertConcurrencyTests(TransactionTestCase):
    def setUp(self):
        empresa = Empresa.objects.create(nome='Concorrência', cnpj='CONCOR', email='c@example.com')
        equipamento = Equipamento.objects.create(empresa=empresa, nome='Motor', numero_serie='CONCOR')
        self.sensor = Sensor.objects.create(
            equipamento=equipamento, nome='Temperatura', tipo='temperatura',
            unidade_medida='C', limite_alerta=100,
        )

    def paralelo(self, acao):
        barreira = Barrier(2)

        def executar():
            close_old_connections()
            try:
                barreira.wait(timeout=10)
                acao()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = [pool.submit(executar) for _ in range(2)]
            for resultado in resultados:
                resultado.result(timeout=30)

    @patch('telemetria.signals.sync_sensor_trend')
    def test_ingestao_simultanea_nao_duplica_ocorrencia_ou_os(self, _):
        self.paralelo(lambda: Telemetria.objects.create(sensor_id=self.sensor.pk, valor=90))
        self.assertEqual(Telemetria.objects.count(), 2)
        self.assertEqual(Alerta.objects.filter(origem='limite').count(), 1)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_processamento_simultaneo_de_alerta_nao_duplica_os(self):
        # bulk_create evita o sinal apenas para preparar um alerta ainda sem OS.
        alerta = Alerta.objects.bulk_create([Alerta(
            equipamento=self.sensor.equipamento, origem='manual',
            tipo_alerta='Inspeção', descricao='Investigar',
        )])[0]
        self.paralelo(lambda: PrioridadeOSService.criar_por_alerta(alerta))
        self.assertEqual(OrdemServico.objects.filter(alerta_origem=alerta).count(), 1)

    def test_analise_simultanea_nao_duplica_alerta_e_os_preditiva(self):
        readings = Telemetria.objects.bulk_create([
            Telemetria(sensor=self.sensor, valor=value) for value in (10, 20, 30)
        ])
        start = timezone.now() - timedelta(hours=1)
        for index, reading in enumerate(readings):
            Telemetria.objects.filter(pk=reading.pk).update(timestamp=start + timedelta(minutes=index * 20))
        self.paralelo(lambda: sync_sensor_trend(self.sensor.pk))
        self.assertEqual(Alerta.objects.filter(origem='tendencia', status='ativo').count(), 1)
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)
