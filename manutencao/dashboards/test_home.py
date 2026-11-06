from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from alertas.models import Alerta
from manutencao.models import OrdemServico
from telemetria.models import Sensor, Telemetria


class HomeDashboardTests(APITestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nome='Empresa A', cnpj='home-a', email='a@example.test')
        self.other_company = Empresa.objects.create(nome='Empresa B', cnpj='home-b', email='b@example.test')
        Empresa.objects.create(nome='Empresa vazia', cnpj='home-empty', email='empty@example.test')
        self.admin = Usuario.objects.create_user(username='home-admin', tipo_usuario='admin')
        self.manager = Usuario.objects.create_user(username='home-manager', tipo_usuario='gestor', empresa=self.company)
        self.tech = Usuario.objects.create_user(username='home-tech', tipo_usuario='tecnico', empresa=self.company)
        self.other_tech = Usuario.objects.create_user(username='home-other', tipo_usuario='tecnico', empresa=self.company)
        self.eq = Equipamento.objects.create(nome='Bomba', numero_serie='home-1', empresa=self.company, status='manutencao')
        self.eq2 = Equipamento.objects.create(nome='Motor', numero_serie='home-2', empresa=self.company)
        self.foreign = Equipamento.objects.create(nome='Outro ativo', numero_serie='home-3', empresa=self.other_company)
        EquipamentoLocalizacao.objects.create(equipamento=self.eq, setor='Produção')
        EquipamentoLocalizacao.objects.create(equipamento=self.eq2, setor='Logística')
        self.mine = OrdemServico.objects.create(equipamento=self.eq, titulo='Minha', responsavel=self.tech, status='andamento')
        self.free = OrdemServico.objects.create(equipamento=self.eq, titulo='Livre')
        self.other = OrdemServico.objects.create(equipamento=self.eq2, titulo='Outro técnico', responsavel=self.other_tech)
        OrdemServico.objects.create(equipamento=self.foreign, titulo='Outra empresa')

    def summary(self, user, **params):
        self.client.force_authenticate(user)
        return self.client.get('/api/dashboards/resumo/', params)

    def test_home_skips_expensive_kpis_and_scopes_all_filtered_counts(self):
        with patch('manutencao.dashboards.views.KpiService.calcular_kpi') as calculate:
            response = self.summary(self.manager, incluir_desempenho='false', setor='Produção', equipamento_id=self.eq.pk)
        self.assertEqual(response.status_code, 200)
        calculate.assert_not_called()
        data = response.data
        self.assertNotIn('kpis_globais', data)
        self.assertEqual(data['resumo_status']['total'], 1)
        self.assertEqual(data['os_abertas'], 2)
        self.assertEqual(data['ordens_sem_tecnico'], 1)
        self.assertEqual({o['id'] for o in data['ordens_prioritarias']}, {self.mine.pk, self.free.pk})
        self.assertEqual(len(data['opcoes_equipamentos']), 2)

    def test_admin_includes_empty_companies_without_join_multiplication(self):
        for n in range(3):
            Alerta.objects.create(equipamento=self.foreign, tipo_alerta=f'Crítico {n}', nivel='critico')
        data = self.summary(self.admin, incluir_desempenho='false').data
        self.assertEqual(data['total_empresas'], 3)
        self.assertEqual(data['empresas_com_alertas_criticos'], 1)
        self.assertEqual(data['empresas'][0]['id'], self.other_company.pk)
        row = next(c for c in data['empresas'] if c['id'] == self.company.pk)
        self.assertEqual(row['equipamentos'], 2)
        self.assertEqual(row['ordens_abertas'], 3)
        self.assertEqual(row['sem_responsavel'], 1)
        selected = self.summary(self.admin, empresa_id=self.company.pk, incluir_desempenho='false').data
        self.assertNotIn('empresas', selected)
        self.assertEqual(selected['resumo_status']['total'], 2)

    def test_active_queue_includes_old_alerts_and_excludes_recent_resolved(self):
        old = Alerta.objects.create(equipamento=self.eq, tipo_alerta='Antigo ativo', nivel='critico')
        Alerta.objects.filter(pk=old.pk).update(data_alerta=timezone.now() - timedelta(days=4))
        Alerta.objects.create(equipamento=self.eq, tipo_alerta='Encerrado', nivel='critico', status='resolvido')
        data = self.summary(self.manager, incluir_desempenho='false').data
        self.assertEqual(data['alertas_ativos']['critico'], 1)
        self.assertEqual(data['alertas_24h']['critico'], 1)
        self.assertEqual([a['id'] for a in data['alertas_prioritarios']], [old.pk])

    def test_technician_only_sees_own_or_free_orders_and_no_finances(self):
        OrdemServico.objects.create(equipamento=self.eq, titulo='Finalizada', status='concluida', responsavel=self.tech)
        data = self.summary(self.tech, empresa_id=self.other_company.pk).data
        self.assertEqual(data['minhas_pendentes'], 0)
        self.assertEqual(data['minhas_em_andamento'], 1)
        self.assertEqual(data['minhas_ordens'], 1)
        self.assertEqual([o['id'] for o in data['minhas_ordens_prioritarias']], [self.mine.pk])
        self.assertEqual([o['id'] for o in data['ordens_disponiveis']], [self.free.pk])
        self.assertEqual([e['id'] for e in data['opcoes_equipamentos']], [self.eq.pk])
        self.assertNotIn('desempenho', data)
        self.assertNotIn('custos_por_dia', data)
        foreign = self.summary(self.tech, equipamento_id=self.foreign.pk).data
        self.assertEqual(foreign['os_abertas'], 0)

    def test_totals_exceed_preview_and_priorities_are_deterministic(self):
        for n in range(55):
            OrdemServico.objects.create(equipamento=self.eq, titulo=f'Pendente {n}')
        OrdemServico.objects.filter(pk=self.free.pk).update(prioridade='A')
        data = self.summary(self.manager, incluir_desempenho='false').data
        self.assertEqual(data['os_abertas'], 58)
        self.assertEqual(len(data['ordens_prioritarias']), 5)
        self.assertEqual(data['ordens_prioritarias'][0]['id'], self.free.pk)

    def test_insufficient_history_is_distinct_from_zero_cost_and_zero_duration(self):
        data = self.summary(self.manager).data
        self.assertIsNone(data['desempenho']['mttr'])
        self.assertIsNone(data['desempenho']['mtbf'])
        self.assertIsNone(data['desempenho']['disponibilidade'])
        self.assertEqual(data['desempenho']['custo'], 0)
        now = timezone.now()
        OrdemServico.objects.create(equipamento=self.eq, titulo='Instantânea', status='concluida', data_abertura=now, data_conclusao=now)
        data = self.summary(self.manager).data
        self.assertEqual(data['desempenho']['mttr'], 0)
        self.assertIsNone(data['desempenho']['mtbf'])
        self.assertIsNone(data['desempenho']['disponibilidade'])

    def test_order_drill_down_filters_survive_pagination(self):
        self.client.force_authenticate(self.tech)
        response = self.client.get('/api/ordens-servico/', {'abertas': 'true', 'responsavel_escopo': 'minhas', 'limit': 1})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.mine.pk)
        response = self.client.get('/api/ordens-servico/', {'abertas': 'true', 'responsavel_escopo': 'livres'})
        self.assertEqual([o['id'] for o in response.data['results']], [self.free.pk])

    def test_live_operational_scope_and_stable_snapshot(self):
        sensor = Sensor.objects.create(equipamento=self.eq, nome='Permitido', tipo='temperatura', unidade_medida='°C', limite_alerta=100)
        hidden = Sensor.objects.create(equipamento=self.eq2, nome='Outro técnico', tipo='temperatura', unidade_medida='°C', limite_alerta=100)
        old = Telemetria.objects.create(sensor=sensor, valor=0)
        Telemetria.objects.create(sensor=sensor, valor=1)
        Telemetria.objects.create(sensor=hidden, valor=2)
        self.client.force_authenticate(self.tech)
        response = self.client.get('/api/telemetria/sensores/', {'escopo_operacional': 'true'})
        self.assertEqual([s['id'] for s in response.data['results']], [sensor.pk])
        response = self.client.get('/api/telemetria/leituras/', {'escopo_operacional': 'true', 'sensor': hidden.pk})
        self.assertEqual(response.data['count'], 0)
        response = self.client.get('/api/telemetria/leituras/', {'escopo_operacional': 'true', 'sensor': sensor.pk, 'id_ate': old.pk})
        self.assertEqual([r['id'] for r in response.data['results']], [old.pk])

    def test_invalid_scope_parameters_return_validation_errors(self):
        self.assertEqual(self.summary(self.manager, equipamento_id='x').status_code, 400)
        self.assertEqual(self.summary(self.manager, dias=-1).status_code, 400)
        unaffiliated = Usuario.objects.create_user(username='sem-empresa', tipo_usuario='gestor')
        self.assertEqual(self.summary(unaffiliated).status_code, 400)
