"""Contrato da base de apresentação, sempre no banco descartável de testes."""
from contextlib import redirect_stdout
from datetime import timedelta
from io import StringIO
import random
from unittest.mock import patch

from django.core.validators import validate_email
from django.db.models import F
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, PlanoManutencao
from alertas.models import Alerta
from manutencao.dashboards.views import DashboardSummaryView, KpiService
from manutencao.models import HistoricoManutencao, OrdemServico
from scripts import seed_db as seed
from scripts import simulador_realtime as sim
from telemetria.models import Sensor, Telemetria


def popular(**kwargs):
    with redirect_stdout(StringIO()):
        return seed.run_seed(**kwargs)


class PresentationShapeTests(SimpleTestCase):
    def test_cenarios_longos_tem_juncao_suave_e_nao_usam_datas_futuras(self):
        now = timezone.now()
        for perfil in ['preditiva', 'ativo', 'recuperado', 'recorrencia']:
            for minimo, limite in [(35, 85), (.2, 7), (2, 12)]:
                with self.subTest(perfil=perfil, limite=limite):
                    rows = list(seed.gerar_historico_apresentacao(
                        minimo, limite, now - timedelta(days=3), now, perfil, random.Random(23)))
                    self.assertTrue(all(a[0] < b[0] for a, b in zip(rows, rows[1:])))
                    self.assertLess(max(abs(b[1] - a[1]) for a, b in zip(rows, rows[1:])), limite * .06)
                    self.assertEqual(rows[-1][0], now - timedelta(minutes=5))


class PresentationDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manifesto = popular(num_empresas=2, equip_por_empresa=5, dias_historico=2,
                               funcionarios_por_empresa=4, rng_seed=17)

    def test_cadastros_datas_e_responsaveis_coerentes(self):
        self.assertFalse(OrdemServico.objects.filter(data_conclusao__lt=F('data_abertura')).exists())
        self.assertFalse(OrdemServico.objects.filter(data_abertura__gt=timezone.now()).exists())
        self.assertFalse(OrdemServico.objects.filter(data_abertura__date__lt=F('equipamento__data_instalacao')).exists())
        self.assertFalse(Telemetria.objects.filter(timestamp__date__lt=F('sensor__equipamento__data_instalacao')).exists())
        self.assertFalse(OrdemServico.objects.filter(responsavel__isnull=False).exclude(
            responsavel__empresa_id=F('equipamento__empresa_id')).exists())
        for usuario in Usuario.objects.all():
            validate_email(usuario.email)
        for eq in Equipamento.objects.all():
            self.assertEqual(eq.fabricante, seed.FABRICANTES_POR_TIPO[eq.tipo])
            self.assertTrue(eq.sensores.filter(leituras__isnull=False).exists())
            self.assertEqual(eq.criticidade, eq.ordens_servico.first().criticidade_na_abertura)
        for empresa in Empresa.objects.all():
            self.assertEqual(set(empresa.equipamentos.values_list('criticidade', flat=True)), {'A', 'B', 'C'})

    def test_kpis_recentes_e_trabalho_garantidos(self):
        for dias in [7, 30]:
            concluidas = OrdemServico.objects.filter(status='concluida',
                data_abertura__gte=timezone.now() - timedelta(days=dias))
            for eq in Equipamento.objects.all():
                kpi = KpiService.calcular_kpi(eq, concluidas)
                self.assertGreater(kpi['mttr_hours'], 0)
                self.assertGreater(kpi['amostras_mtbf'], 0)
                self.assertGreater(kpi['mtbf_hours'], 0)
                self.assertGreater(kpi['custo_total_manutencao'], 0)
                self.assertGreater(kpi['disponibilidade_porcentagem'], 0)
                self.assertLessEqual(kpi['disponibilidade_porcentagem'], 100)
        for tecnico in Usuario.objects.filter(tipo_usuario='tecnico'):
            for status in ['pendente', 'andamento']:
                self.assertTrue(tecnico.minhas_os.filter(status=status).exists())
            self.assertTrue(OrdemServico.objects.filter(equipamento__empresa=tecnico.empresa,
                status='pendente', responsavel__isnull=True).exists())
        self.assertEqual(HistoricoManutencao.objects.count(), OrdemServico.objects.filter(status='concluida').count())

    def test_alertas_tem_evidencia_escalada_recuperacao_e_recorrencia(self):
        for empresa in Empresa.objects.all():
            alertas = Alerta.objects.filter(equipamento__empresa=empresa, origem='limite')
            self.assertTrue(alertas.filter(status='ativo', nivel='critico').exists())
            self.assertTrue(alertas.filter(status='resolvido', nivel='critico').exists())
            for alerta in alertas:
                self.assertEqual(alerta.dados_deteccao['sensor_id'], alerta.sensor_id)
                self.assertTrue(alerta.dados_deteccao['leituras'])
                self.assertEqual(alerta.ordem_servico.sensor_origem_id, alerta.sensor_id)
                self.assertLessEqual(alerta.ordem_servico.data_abertura, alerta.data_alerta)
                self.assertGreaterEqual(alerta.data_ultima_analise, alerta.data_alerta)
                if alerta.data_normalizacao:
                    self.assertGreater(alerta.data_normalizacao, alerta.data_alerta)
                for evento in alerta.historico_niveis:
                    self.assertIn(evento['nivel'], ['medio', 'critico'])
                    self.assertGreaterEqual(evento['ocorrido_em'], alerta.data_alerta.isoformat())
                self.assertIn(timezone.localtime(alerta.data_alerta).strftime('%d/%m/%Y %H:%M:%S'),
                              alerta.ordem_servico.descricao)
            recorrente = Sensor.objects.get(equipamento__empresa=empresa, descricao__contains='Perfil histórico: recorrencia.')
            ocorrencias = list(Alerta.objects.filter(sensor=recorrente, origem='limite').order_by('data_alerta'))
            self.assertEqual(len(ocorrencias), 2)
            self.assertEqual(ocorrencias[0].ordem_servico_id, ocorrencias[1].ordem_servico_id)
            self.assertTrue(all(a.status == 'resolvido' for a in ocorrencias))
            ordem = OrdemServico.objects.get(equipamento__empresa=empresa,
                tipo_os='preditiva', alerta_origem__origem='tendencia')
            self.assertTrue(ordem.evidencia_preditiva)
            self.assertLess(ordem.evidencia_preditiva['analise']['current_value'],
                            ordem.evidencia_preditiva['limite_operacional'])

    def test_dashboards_dos_tres_perfis_e_isolamento(self):
        factory = APIRequestFactory()
        for usuario in Usuario.objects.all():
            request = factory.get('/api/dashboards/resumo/', {'dias': 30})
            force_authenticate(request, user=usuario)
            response = DashboardSummaryView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertGreater(response.data['ordens_sem_tecnico'], 0)
            self.assertGreater(response.data['alertas_24h']['total'], 0)
            if usuario.tipo_usuario == 'tecnico':
                self.assertGreater(response.data['minhas_pendentes'], 0)
                self.assertGreater(response.data['minhas_em_andamento'], 0)
            else:
                self.assertGreater(response.data['desempenho']['custo'], 0)
            if usuario.tipo_usuario != 'admin':
                self.assertTrue(all(eq['empresa'] == usuario.empresa_id
                                    for eq in response.data['opcoes_equipamentos']))

    def test_horimetro_dispara_uma_ordem_pelo_fluxo_real(self):
        plano = PlanoManutencao.objects.select_related('equipamento').order_by('pk').first()
        eq = plano.equipamento
        titulo = f'[PREDITIVA] {plano.nome_servico}'
        self.assertFalse(OrdemServico.objects.filter(equipamento=eq, titulo=titulo).exists())
        eq.horimetro = plano.horimetro_ultima_os + plano.intervalo_horas
        eq.save(update_fields=['horimetro'])
        eq.save(update_fields=['horimetro'])
        self.assertEqual(OrdemServico.objects.filter(equipamento=eq, titulo=titulo).count(), 1)

    def test_reprocessar_historico_nao_redatera_ocorrencias_nem_duplica_os(self):
        sensor = Sensor.objects.filter(descricao__contains='Perfil histórico: recorrencia.').first()
        antes = list(Alerta.objects.filter(sensor=sensor).order_by('pk').values(
            'id', 'data_alerta', 'data_normalizacao', 'ordem_servico_id', 'historico_niveis'))
        total = OrdemServico.objects.count()
        seed.reprocessar_limites_historicos(sensor, timezone.now() - timedelta(hours=24))
        depois = list(Alerta.objects.filter(sensor=sensor).order_by('pk').values(
            'id', 'data_alerta', 'data_normalizacao', 'ordem_servico_id', 'historico_niveis'))
        self.assertEqual(antes, depois)
        self.assertEqual(OrdemServico.objects.count(), total)

    def test_simulador_retorna_a_ultima_leitura_e_preserva_estado_na_retomada(self):
        sensores = list(sim.obter_sensores_ativos())
        self.assertTrue(sensores)
        self.assertTrue(all(s.equipamento.status == 'ativo' and s.ativo for s in sensores))
        memoria = sim.inicializar_memoria_sensores(sensores, {})
        for sensor in sensores:
            ultima = sensor.leituras.order_by('-timestamp', '-pk').first()
            self.assertEqual(memoria[sensor.pk], ultima.valor)
        resultado = sim.rodar_ciclo(sensores, memoria, cenario='normal')
        self.assertEqual(resultado['gravadas'], len(sensores))
        retomada = sim.inicializar_memoria_sensores(sensores, {})
        self.assertEqual(memoria, retomada)


class SeedSafetyTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Preservar até commit', cnpj='ORIGINAL', email='original@example.com')
        self.admin = Usuario.objects.create_superuser(username='admin', password='senha-existente',
            empresa=self.empresa, tipo_usuario='admin')
        self.admin_perfil = Usuario.objects.create_user(username='perfil_admin', password='outra-senha',
            empresa=self.empresa, tipo_usuario='admin')

    def test_validacao_precede_qualquer_limpeza(self):
        for kwargs in [{'num_empresas': 0}, {'equip_por_empresa': -1}, {'dias_historico': 0},
                       {'funcionarios_por_empresa': 1}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                popular(**kwargs)
            self.assertTrue(Empresa.objects.filter(pk=self.empresa.pk).exists())
            self.admin.refresh_from_db()
            self.assertEqual(self.admin.empresa_id, self.empresa.pk)

    def test_migracao_pendente_impede_limpeza(self):
        with patch('django.db.migrations.executor.MigrationExecutor.migration_plan', return_value=['pendente']):
            with self.assertRaisesRegex(RuntimeError, 'migrações pendentes'):
                popular(clean_only=True)
        self.assertTrue(Empresa.objects.filter(pk=self.empresa.pk).exists())

    def test_falha_depois_da_limpeza_restaura_base_e_admin(self):
        with patch.object(seed, 'validar_populacao', side_effect=RuntimeError('falha ao validar')):
            with self.assertRaisesRegex(RuntimeError, 'falha ao validar'):
                popular(num_empresas=1, equip_por_empresa=1, dias_historico=1, funcionarios_por_empresa=2)
        self.assertEqual(list(Empresa.objects.values_list('nome', flat=True)), ['Preservar até commit'])
        self.assertFalse(Telemetria.objects.exists())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.empresa_id, self.empresa.pk)
        self.assertTrue(self.admin.check_password('senha-existente'))

    def test_limpeza_preserva_admins_senhas_e_desvincula_empresa(self):
        popular(clean_only=True)
        self.assertFalse(Empresa.objects.exists())
        for user, password in [(self.admin, 'senha-existente'), (self.admin_perfil, 'outra-senha')]:
            user.refresh_from_db()
            self.assertIsNone(user.empresa_id)
            self.assertTrue(user.check_password(password))

    def test_superusuario_tem_perfil_administrativo_na_aplicacao(self):
        Usuario.objects.filter(pk=self.admin.pk).update(tipo_usuario='tecnico')
        popular(clean_only=True)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.tipo_usuario, 'admin')
        self.assertTrue(self.admin.check_password('senha-existente'))

    def test_check_nao_altera_a_base(self):
        popular(check_only=True)
        self.assertTrue(Empresa.objects.filter(pk=self.empresa.pk).exists())
        self.assertEqual(Usuario.objects.count(), 2)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.empresa_id, self.empresa.pk)

    def test_email_normaliza_acentos_e_colisoes(self):
        for _ in range(2):
            username, email = seed.gerar_credenciais_reais('João Conceição', 'Indústria Açúcar & Cia, Ltda.')
            validate_email(email)
            self.assertTrue(username.isascii())
            self.assertTrue(email.endswith('.example.com'))

    def test_janelas_curta_e_longa_tem_kpis_recentes(self):
        for dias in [1, 120, 365]:
            with self.subTest(dias=dias):
                popular(num_empresas=1, equip_por_empresa=1, dias_historico=dias, funcionarios_por_empresa=2)
                eq = Equipamento.objects.get()
                concluidas = OrdemServico.objects.filter(status='concluida',
                    data_abertura__gte=timezone.now() - timedelta(days=7))
                kpi = KpiService.calcular_kpi(eq, concluidas)
                self.assertGreater(kpi['amostras_mtbf'], 0)
                self.assertGreater(kpi['custo_total_manutencao'], 0)

    def test_um_dia_tambem_cobre_cenarios_e_inativos_tem_historico(self):
        popular(num_empresas=1, equip_por_empresa=5, dias_historico=1, funcionarios_por_empresa=2)
        for sensor in Sensor.objects.all():
            self.assertTrue(sensor.leituras.exists())
        self.assertTrue(Alerta.objects.filter(status='ativo', nivel='critico').exists())
        self.assertTrue(Alerta.objects.filter(status='resolvido', nivel='critico').exists())

    def test_mesma_seed_reproduz_cadastros_e_valores(self):
        amostras = []
        for _ in range(2):
            popular(num_empresas=1, equip_por_empresa=1, dias_historico=1, funcionarios_por_empresa=2, rng_seed=9)
            amostras.append((list(Empresa.objects.values_list('nome', 'cnpj')),
                            list(Usuario.objects.filter(tipo_usuario='tecnico').values_list('username', 'email')),
                            list(Telemetria.objects.order_by('pk').values_list('valor', flat=True))))
        self.assertEqual(amostras[0], amostras[1])

    def test_cli_retorna_falha_quando_geracao_falha(self):
        with patch.object(seed, 'run_seed', side_effect=RuntimeError('falha')), \
                patch('sys.stderr', new_callable=StringIO):
            self.assertEqual(seed.main([]), 1)
