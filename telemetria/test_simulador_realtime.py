"""Regressões do simulador usando apenas o banco descartável de testes."""
import random
from unittest.mock import patch

from django.db import OperationalError
from django.test import TransactionTestCase

from accounts.models import Empresa
from ativos.models import Equipamento
from alertas.models import Alerta
from telemetria.models import Sensor, Telemetria
from scripts import simulador_realtime as sim


class SimulatorTests(TransactionTestCase):
    # O simulador fecha conexões como um processo real. TestCase manteria uma
    # transação externa aberta nessa conexão, invalidando os testes no PostgreSQL.
    def setUp(self):
        empresa = Empresa.objects.create(nome='Simulação', cnpj='SIM', email='sim@example.com')
        self.equipamento = Equipamento.objects.create(empresa=empresa, nome='Motor', numero_serie='SIM')
        self.sensor = Sensor.objects.create(equipamento=self.equipamento, nome='Temperatura',
            tipo='temperatura', unidade_medida='C', limite_alerta=10,
            limite_alerta_baixo_pct=40, limite_alerta_medio_pct=60, limite_alerta_critico_pct=80)

    def test_cenarios_respeitam_percentuais_personalizados(self):
        for fase, minimo, maximo in [('normal', 0, 4), ('baixo', 4, 6),
                                     ('medio', 6, 8), ('critico', 8, 10), ('recuperacao', 0, 4)]:
            valor, *_ = sim.gerar_valor_sensor(self.sensor, 100, random.Random(7), fase)
            self.assertGreaterEqual(valor, minimo)
            self.assertLess(valor, maximo)

    def test_fluxo_real_escala_e_recupera_alerta(self):
        memoria = {self.sensor.pk: 3.0}
        with patch('telemetria.signals.sync_sensor_trend'):
            for fase in ['baixo', 'medio', 'critico', 'recuperacao', 'recuperacao']:
                resumo = sim.rodar_ciclo([self.sensor], memoria, rng=random.Random(1), cenario=fase)
                self.assertEqual(resumo['gravadas'], 1)
        alerta = Alerta.objects.get(sensor=self.sensor, origem='limite')
        self.assertEqual(alerta.nivel, 'critico')
        self.assertEqual(alerta.status, 'resolvido')
        self.assertEqual(Telemetria.objects.count(), 5)

    def test_dry_run_nao_grava_nem_dispara_sinais(self):
        with patch('telemetria.signals.sync_sensor_trend') as tendencia:
            resultado = sim.rodar_ciclo([self.sensor], {self.sensor.pk: 3}, dry_run=True)
        self.assertEqual(resultado['simuladas'], 1)
        self.assertFalse(Telemetria.objects.exists())
        self.assertFalse(Alerta.objects.exists())
        tendencia.assert_not_called()

    def test_falha_de_sinal_desfaz_leitura_e_preserva_memoria(self):
        outro = Sensor.objects.create(equipamento=self.equipamento, nome='Outro',
            tipo='pressao', unidade_medida='bar', limite_alerta=100)
        memoria = {self.sensor.pk: 3, outro.pk: 50}
        with patch('telemetria.signals.sync_sensor_trend', side_effect=[OperationalError('falha'), None]):
            resumo = sim.rodar_ciclo([self.sensor, outro], memoria, cenario='normal')
        self.assertEqual(resumo['falhas'], 1)
        self.assertEqual(resumo['gravadas'], 1)
        self.assertEqual(memoria[self.sensor.pk], 3)
        self.assertFalse(Telemetria.objects.filter(sensor=self.sensor).exists())
        self.assertTrue(Telemetria.objects.filter(sensor=outro).exists())

    def test_memoria_consulta_apenas_novos_e_ultima_leitura(self):
        with patch('telemetria.signals.sync_sensor_trend'):
            Telemetria.objects.create(sensor=self.sensor, valor=1)
            Telemetria.objects.create(sensor=self.sensor, valor=2)
        with self.assertNumQueries(1):
            memoria = sim.inicializar_memoria_sensores([self.sensor], {})
        self.assertEqual(memoria[self.sensor.pk], 2)
        with self.assertNumQueries(0):
            self.assertEqual(sim.inicializar_memoria_sensores([self.sensor], memoria), memoria)

    def test_filtros_e_mudanca_de_status(self):
        self.assertEqual(list(sim.obter_sensores_ativos(empresa_ids=[self.equipamento.empresa_id])), [self.sensor])
        self.assertFalse(sim.obter_sensores_ativos(sensor_ids=[self.sensor.pk + 100]).exists())
        self.equipamento.status = 'manutencao'
        self.equipamento.save()
        resumo = sim.rodar_ciclo([self.sensor], {self.sensor.pk: 3})
        self.assertEqual(resumo['ignoradas'], 1)
        self.assertFalse(sim.obter_sensores_ativos().exists())

    def test_argumentos_invalidos(self):
        for argv in [['--interval-min', 'nan'], ['--interval-max', 'inf'], ['--cycles', '-1'],
                     ['--chance-anomalia', '2'], ['--sensor', '0'], ['--fase-ciclos', '0']]:
            with self.assertRaises(SystemExit), patch('sys.stderr'):
                sim.parse_args(argv)

    def test_execucao_finita_sem_espera_final(self):
        args = sim.parse_args(['--cycles', '1', '--dry-run'])
        with patch.object(sim, 'verificar_banco'), patch.object(sim, 'obter_sensores_ativos', return_value=[]), \
                patch('time.sleep') as dormir:
            self.assertEqual(sim.run_simulator(args), 0)
        dormir.assert_not_called()

    def test_gravacao_com_analise_preditiva_real(self):
        memoria = {self.sensor.pk: 2}
        resumo = sim.rodar_ciclo([self.sensor], memoria, cenario='normal')
        self.assertEqual(resumo['gravadas'], 1)
        self.assertFalse(Alerta.objects.filter(sensor=self.sensor, origem='limite').exists())

    def test_falhas_consecutivas_encerram_execucao(self):
        args = sim.parse_args(['--max-falhas', '2'])
        with patch.object(sim, 'verificar_banco'), \
                patch.object(sim, 'obter_sensores_ativos', side_effect=OperationalError('offline')) as consulta, \
                patch('time.sleep'):
            self.assertEqual(sim.run_simulator(args), 1)
        self.assertEqual(consulta.call_count, 2)
