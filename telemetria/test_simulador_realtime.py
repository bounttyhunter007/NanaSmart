"""Regressões do simulador usando apenas o banco descartável de testes."""
import random
from contextlib import redirect_stdout
from datetime import timedelta
from io import BytesIO, TextIOWrapper
from unittest.mock import patch

from django.db import OperationalError
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import Empresa
from ativos.models import Equipamento
from alertas.models import Alerta
from telemetria.models import Sensor, Telemetria, TrendConfig
from manutencao.models import OrdemServico
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
            valor, *_ = sim.gerar_valor_sensor(self.sensor, (minimo + maximo) / 2, random.Random(7), fase)
            self.assertGreaterEqual(valor, minimo)
            self.assertLess(valor, maximo)

    def test_fluxo_real_escala_e_recupera_alerta(self):
        memoria = {self.sensor.pk: 3.0}
        dinamica = {}
        rng = random.Random(1)
        with patch('telemetria.signals.sync_sensor_trend'):
            for fase in ['baixo', 'medio', 'critico', 'recuperacao']:
                for _ in range(80):
                    resumo = sim.rodar_ciclo([self.sensor], memoria, rng=rng, cenario=fase, memoria_dinamica=dinamica)
                    self.assertEqual(resumo['gravadas'], 1)
        alerta = Alerta.objects.get(sensor=self.sensor, origem='limite')
        self.assertEqual(alerta.nivel, 'critico')
        self.assertEqual(alerta.status, 'resolvido')
        self.assertEqual(Telemetria.objects.count(), 320)
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_dry_run_nao_grava_nem_dispara_sinais(self):
        dinamica = {}
        with patch('telemetria.signals.sync_sensor_trend') as tendencia:
            resultado = sim.rodar_ciclo([self.sensor], {self.sensor.pk: 3}, dry_run=True, memoria_dinamica=dinamica)
        self.assertEqual(resultado['simuladas'], 1)
        self.assertFalse(Telemetria.objects.exists())
        self.assertFalse(Alerta.objects.exists())
        tendencia.assert_not_called()
        self.assertIn('alvo', dinamica[self.sensor.pk])

    def test_falha_de_sinal_desfaz_leitura_e_preserva_memoria(self):
        outro = Sensor.objects.create(equipamento=self.equipamento, nome='Outro',
            tipo='pressao', unidade_medida='bar', limite_alerta=100)
        memoria = {self.sensor.pk: 3, outro.pk: 50}
        dinamica = {self.sensor.pk: {'restantes': 5, 'alvo': 3.5}}
        anterior = dict(dinamica[self.sensor.pk])
        with patch('telemetria.signals.sync_sensor_trend', side_effect=[OperationalError('falha'), None]):
            resumo = sim.rodar_ciclo([self.sensor, outro], memoria, cenario='normal', memoria_dinamica=dinamica)
        self.assertEqual(resumo['falhas'], 1)
        self.assertEqual(resumo['gravadas'], 1)
        self.assertEqual(memoria[self.sensor.pk], 3)
        self.assertEqual(dinamica[self.sensor.pk], anterior)
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
                     ['--chance-anomalia', '2'], ['--sensor', '0'], ['--fase-ciclos', '0'],
                     ['--variacao-max-pct', '0'], ['--variacao-max-pct', 'nan'],
                     ['--variacao-max-pct', '6']]:
            with self.assertRaises(SystemExit), patch('sys.stderr'):
                sim.parse_args(argv)

    def test_execucao_finita_sem_espera_final(self):
        args = sim.parse_args(['--cycles', '1', '--dry-run'])
        with patch.object(sim, 'verificar_banco'), \
                patch('time.sleep') as dormir:
            self.assertEqual(sim.run_simulator(args), 0)
        dormir.assert_not_called()

    def test_execucao_finita_sem_sensores_falha_sem_esperar(self):
        args = sim.parse_args(['--cycles', '1', '--sensor', str(self.sensor.pk + 100)])
        with patch.object(sim, 'verificar_banco'), patch('time.sleep') as dormir:
            self.assertEqual(sim.run_simulator(args), 1)
        dormir.assert_not_called()
        self.assertFalse(Telemetria.objects.exists())

    def test_check_consulta_sem_gerar_leituras(self):
        args = sim.parse_args(['--check'])
        with patch.object(sim, 'verificar_banco'), patch.object(sim, 'rodar_ciclo') as ciclo, \
                patch('time.sleep') as dormir:
            self.assertEqual(sim.run_simulator(args), 0)
        ciclo.assert_not_called()
        dormir.assert_not_called()
        self.assertFalse(Telemetria.objects.exists())
        self.assertFalse(Alerta.objects.exists())

    def test_check_sem_sensores_e_limites_invalidos(self):
        Sensor.objects.filter(pk=self.sensor.pk).update(limite_alerta=0)
        with patch.object(sim, 'verificar_banco'):
            self.assertEqual(sim.run_simulator(sim.parse_args(['--check'])), 1)
            self.assertEqual(sim.run_simulator(sim.parse_args(['--check', '--sensor', '999999'])), 1)

    def test_falha_intermediaria_nao_vira_sucesso_no_ultimo_ciclo(self):
        args = sim.parse_args(['--cycles', '2'])
        falha = dict(gravadas=0, simuladas=0, falhas=1, ignoradas=0)
        sucesso = dict(gravadas=1, simuladas=0, falhas=0, ignoradas=0)
        with patch.object(sim, 'verificar_banco'), patch('time.sleep'), \
                patch.object(sim, 'rodar_ciclo', side_effect=[falha, sucesso]):
            self.assertEqual(sim.run_simulator(args), 1)

    def test_help_funciona_no_terminal_windows_sem_acessar_banco(self):
        saida = TextIOWrapper(BytesIO(), encoding='cp1252')
        with redirect_stdout(saida), self.assertRaises(SystemExit) as result:
            sim.parse_args(['--help'])
        saida.flush()
        self.assertEqual(result.exception.code, 0)
        saida.close()

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

    def test_transicao_nao_salta_diretamente_para_faixa_alvo(self):
        estado = {}
        valor, _, minimo, _ = sim.gerar_valor_sensor(self.sensor, 3, random.Random(2), 'critico', estado=estado)
        self.assertLessEqual(valor - 3, .1 + 1e-12)
        self.assertLess(valor, minimo)
        self.assertGreaterEqual(estado['alvo'], minimo)
        recuperando, *_ = sim.gerar_valor_sensor(self.sensor, 9, random.Random(2), 'recuperacao')
        self.assertGreaterEqual(recuperando, 8.9 - 1e-12)

    def test_evento_misto_persiste_em_vez_de_virar_pico_isolado(self):
        rng = random.Random(5)
        estado, valor, fases = {}, 3, []
        for index in range(25):
            valor, *_ = sim.gerar_valor_sensor(self.sensor, valor, rng, 'misto',
                                              chance_anomalia=1 if index == 0 else 0, estado=estado)
            fases.append(estado['fase'])
        self.assertIn(fases[0], ['baixo', 'medio', 'critico'])
        self.assertEqual(len(set(fases)), 1)
        anterior = valor
        for _ in range(150):
            valor, *_ = sim.gerar_valor_sensor(self.sensor, valor, rng, 'misto', chance_anomalia=0, estado=estado)
        self.assertEqual(estado['fase'], 'normal')
        self.assertLess(valor, anterior)

    def test_limite_de_variacao_e_preservado_mesmo_com_historico_fora_da_faixa(self):
        for anterior in [-10, 0, 3, 100]:
            for fase in ['normal', 'baixo', 'medio', 'critico', 'recuperacao', 'tendencia', 'oscilacao']:
                with self.subTest(anterior=anterior, fase=fase):
                    valor, *_ = sim.gerar_valor_sensor(self.sensor, anterior, random.Random(8), fase,
                                                      variacao_max_pct=.5)
                    self.assertLessEqual(abs(valor - anterior), .05 + 1e-12)

    def test_alvo_e_compartilhado_apenas_entre_leituras_do_mesmo_sensor(self):
        rng, estado = random.Random(5), {}
        sim.gerar_valor_sensor(self.sensor, 3, rng, 'normal', estado=estado)
        alvo = estado['alvo']
        for _ in range(10):
            sim.gerar_valor_sensor(self.sensor, 3, rng, 'normal', estado=estado)
            self.assertEqual(estado['alvo'], alvo)
        self.sensor.limite_alerta = 20
        sim.gerar_valor_sensor(self.sensor, 3, rng, 'normal', estado=estado)
        self.assertNotEqual(estado['alvo'], alvo)

    def test_oscilacao_tem_subidas_e_quedas_suaves_em_escala_pequena(self):
        self.sensor.limite_alerta = .01
        self.sensor.limite_alerta_baixo_pct = 70
        self.sensor.limite_alerta_medio_pct = 85
        self.sensor.limite_alerta_critico_pct = 100
        rng, estado, valor, valores = random.Random(42), {}, .0055, []
        for _ in range(200):
            novo, *_ = sim.gerar_valor_sensor(self.sensor, valor, rng, 'oscilacao', estado=estado)
            self.assertLessEqual(abs(novo - valor), .0001 + 1e-12)
            valores.append(novo)
            valor = novo
        self.assertTrue(any(b > a for a, b in zip(valores, valores[1:])))
        self.assertTrue(any(b < a for a, b in zip(valores, valores[1:])))
        self.assertTrue(all(0 < valor < .007 for valor in valores))
        self.assertGreater(len(set(valores)), 150)

    def test_ritmo_da_tendencia_acompanha_tempo_e_nao_quantidade_de_leituras(self):
        resultados = []
        for passos, delta in [(60, 5), (30, 10)]:
            rng, estado, valor = random.Random(42), {}, 3
            for _ in range(passos):
                novo, *_ = sim.gerar_valor_sensor(self.sensor, valor, rng, 'tendencia',
                                                estado=estado, delta_segundos=delta)
                self.assertGreater(novo, valor)
                valor = novo
            resultados.append(valor)
        esperado = 3 + 10 * .15 * 300 / 3600
        for valor in resultados:
            self.assertAlmostEqual(valor, esperado, delta=.005)

    def test_tendencia_gera_os_pelos_criterios_reais_sem_inventar_horarios(self):
        TrendConfig.objects.create(sensor=self.sensor, minimo_leituras=7, duracao_minima_minutos=1, antecedencia_os_minutos=480)
        memoria, dinamica, rng = {self.sensor.pk: 2.9}, {}, random.Random(4)
        inicio = timezone.now() - timedelta(minutes=1)
        for index in range(7):
            agora = inicio + timedelta(seconds=index * 10)
            with patch('django.utils.timezone.now', return_value=agora):
                sim.rodar_ciclo([self.sensor], memoria, rng=rng, cenario='tendencia',
                                memoria_dinamica=dinamica, delta_segundos=10)
            if index < 6:
                self.assertFalse(Alerta.objects.filter(origem='tendencia').exists())
        self.assertEqual(Telemetria.objects.count(), 7)
        self.assertEqual(Alerta.objects.filter(origem='tendencia').count(), 1)
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)
        self.assertFalse(Alerta.objects.filter(origem='limite').exists())
