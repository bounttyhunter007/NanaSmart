from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from manutencao.models import OrdemServico
from telemetria.models import Sensor, Telemetria, TrendConfig
from telemetria.predictive_service import sync_sensor_trend
from .admin import AlertaAdmin
from .models import Alerta


class AlertHistoryTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Histórico', cnpj='HIST', email='h@example.com')
        self.outra = Empresa.objects.create(nome='Outra', cnpj='OTHER', email='o@example.com')
        self.user = Usuario.objects.create_user(username='gestor', tipo_usuario='gestor', empresa=self.empresa)
        self.client.force_authenticate(self.user)
        self.equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Motor', numero_serie='HIST', criticidade='C')
        self.sensor = Sensor.objects.create(equipamento=self.equipamento, nome='Temperatura', tipo='temperatura',
                                           unidade_medida='°C', limite_alerta=100)
        TrendConfig.objects.create(sensor=self.sensor, ativo=False)

    def read(self, value):
        return Telemetria.objects.create(sensor=self.sensor, valor=value)

    def test_todos_os_perfis_consultam_sem_escrever(self):
        self.read(90)
        alerta = Alerta.objects.get()
        url = reverse('alertas-detail', args=[alerta.pk])
        for role in ('admin', 'gestor', 'tecnico'):
            self.user.tipo_usuario = role
            self.user.save()
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.post(reverse('alertas-list'), {}, format='json').status_code, 405)
            for method in ('put', 'patch', 'delete'):
                self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 405)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_evidencias_preservam_cinquenta_leituras_e_nao_mudam(self):
        for i in range(55):
            self.read(0 if i == 6 else 20)
        trigger = self.read(75)
        alerta = Alerta.objects.get()
        snapshot = deepcopy(alerta.dados_deteccao)
        self.assertEqual(len(snapshot['leituras']), 50)
        self.assertEqual(snapshot['leituras'][-1]['id'], trigger.pk)
        self.assertEqual(snapshot['leituras'][0]['valor'], 0)
        self.assertEqual(snapshot['nivel'], 'baixo')
        self.assertEqual(snapshot['analise']['limites_pct']['medio'], 85)
        self.read(110)
        self.sensor.nome = 'Renomeado'
        self.sensor.limite_alerta = 120
        self.sensor.save()
        self.read(10)
        normal = self.read(10)
        alerta.refresh_from_db()
        self.assertEqual(alerta.dados_deteccao, snapshot)
        self.assertEqual(alerta.nivel, 'critico')
        self.assertEqual(alerta.data_normalizacao, normal.timestamp)
        self.assertEqual(alerta.ordem_servico.status, 'pendente')
        self.sensor.delete()
        data = self.client.get(reverse('alertas-detail', args=[alerta.pk])).data
        self.assertIsNone(data['sensor'])
        self.assertEqual(data['sensor_nome'], 'Temperatura')
        self.assertEqual(data['dados_deteccao'], snapshot)

    def test_equipamento_com_historico_deve_ser_desativado(self):
        self.read(90)
        with self.assertRaises(ProtectedError):
            self.equipamento.delete()
        response = self.client.delete(reverse('equipamentos-detail', args=[self.equipamento.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn('Desative', str(response.data))
        self.assertEqual(self.client.patch(reverse('equipamentos-detail', args=[self.equipamento.pk]),
                                           {'status': 'inativo'}, format='json').status_code, 200)

    def test_recorrencia_preserva_snapshot_e_reutiliza_ordem_aberta(self):
        self.read(90)
        anterior = Alerta.objects.get()
        self.read(20)
        self.read(20)
        self.read(110)
        atual = Alerta.objects.latest('pk')
        self.assertNotEqual(atual.pk, anterior.pk)
        self.assertEqual(atual.ordem_servico_id, anterior.ordem_servico_id)
        self.assertEqual(atual.dados_deteccao['nivel'], 'critico')
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_tendencia_preserva_janela_nivel_maximo_e_normalizacao(self):
        now = timezone.now()
        sample = {
            'analysis_enabled': True, 'insufficient_data': False, 'is_anomalous': True,
            'intervention_recommended': True, 'direction': 'increasing', 'risk_level': 'critico',
            'readings_count': 3, 'sample_duration_minutes': 60, 'r_squared': 1,
            'persistence_ratio': 1, 'slope_per_hour': 20, 'current_value': 60,
            'projected_breach_hours': 2, 'config_used': {'r2_minimo': 0.8},
            'readings_summary': [{'valor': 40, 'timestamp': (now - timedelta(hours=1)).isoformat()},
                                 {'valor': 50, 'timestamp': (now - timedelta(minutes=30)).isoformat()},
                                 {'valor': 60, 'timestamp': now.isoformat()}],
        }
        with patch('telemetria.predictive_service.analyze_sensor_trend', return_value=sample):
            sync_sensor_trend(self.sensor.pk)
        alerta = Alerta.objects.get()
        snapshot = deepcopy(alerta.dados_deteccao)
        lower = dict(sample, risk_level='medio', readings_summary=[{'valor': 30, 'timestamp': now.isoformat()}])
        with patch('telemetria.predictive_service.analyze_sensor_trend', return_value=lower):
            sync_sensor_trend(self.sensor.pk)
        with patch('telemetria.predictive_service.analyze_sensor_trend', return_value=dict(lower, is_anomalous=False)):
            sync_sensor_trend(self.sensor.pk)
        alerta.refresh_from_db()
        self.assertEqual(alerta.dados_deteccao, snapshot)
        self.assertEqual(alerta.nivel, 'critico')
        self.assertIsNotNone(alerta.data_normalizacao)
        self.assertEqual(alerta.ordem_servico.status, 'pendente')

    def legacy(self, equipamento=None, **kwargs):
        # Registros históricos de versões anteriores não passam pela API.
        return Alerta.objects.bulk_create([Alerta(
            equipamento=equipamento or self.equipamento, origem='manual',
            tipo_alerta='Registro legado', descricao='Verificação antiga', **kwargs,
        )])[0]

    def test_filtros_exportacao_e_ordenacao_usam_o_mesmo_historico(self):
        now = timezone.now()
        first = self.legacy(nivel='medio', sensor=self.sensor)
        second = self.legacy(nivel='medio', sensor=self.sensor)
        self.legacy(nivel='baixo')
        Alerta.objects.filter(pk__in=[first.pk, second.pk]).update(data_alerta=now)
        params = {'equipamento': self.equipamento.pk, 'sensor': self.sensor.pk, 'origem': 'manual',
                  'nivel': 'medio', 'search': 'legado', 'data_de': (now - timedelta(minutes=1)).isoformat(),
                  'data_ate': now.isoformat(), 'limit': 1}
        response = self.client.get(reverse('alertas-list'), params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], second.pk)
        self.assertTrue(response.data['results'][0]['legado'])
        self.assertEqual(self.client.get(response.data['next']).data['results'][0]['id'], first.pk)
        with patch('exportacao.views._despachar_formato', side_effect=lambda *args: Response({'rows': args[-1]})):
            exported = self.client.get(reverse('exportar-alertas', args=['csv']), params)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual([row[0] for row in exported.data['rows']], [second.pk, first.pk])
        invalid = dict(params, data_de='invalido')
        self.assertEqual(self.client.get(reverse('alertas-list'), invalid).status_code, 400)
        self.assertEqual(self.client.get(reverse('exportar-alertas', args=['csv']), invalid).status_code, 400)

    def test_gravidade_precede_data_e_paginacao_tambem_na_exportacao(self):
        now = timezone.now()
        low = self.legacy(nivel='baixo')
        medium = self.legacy(nivel='medio')
        critical_old = self.legacy(nivel='critico', status='resolvido')
        critical_new = self.legacy(nivel='critico')
        for alerta, age in ((low, 0), (medium, 1), (critical_new, 24), (critical_old, 48)):
            Alerta.objects.filter(pk=alerta.pk).update(data_alerta=now - timedelta(hours=age))
        response = self.client.get(reverse('alertas-list'), {'limit': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual([row['id'] for row in response.data['results']], [critical_new.pk, critical_old.pk])
        following = self.client.get(response.data['next'])
        self.assertEqual([row['id'] for row in following.data['results']], [medium.pk, low.pk])
        with patch('exportacao.views._despachar_formato', side_effect=lambda *args: Response({'rows': args[-1]})):
            exported = self.client.get(reverse('exportar-alertas', args=['csv']))
        self.assertEqual([row[0] for row in exported.data['rows']],
                         [critical_new.pk, critical_old.pk, medium.pk, low.pk])

    def test_isolamento_de_empresa_na_lista_detalhe_exportacao_e_dashboard(self):
        other_eq = Equipamento.objects.create(empresa=self.outra, nome='Outro', numero_serie='OTHER')
        foreign = self.legacy(equipamento=other_eq)
        self.assertEqual(self.client.get(reverse('alertas-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('alertas-detail', args=[foreign.pk])).status_code, 404)
        with patch('exportacao.views._despachar_formato', side_effect=lambda *args: Response({'rows': args[-1]})):
            self.assertEqual(self.client.get(reverse('exportar-alertas', args=['csv']),
                                             {'empresa': self.outra.pk}).data['rows'], [])
        self.assertEqual(self.client.get(reverse('dashboard-summary')).data['alertas_24h']['total'], 0)

    def test_exportacoes_reais_suportam_motivos_longos_e_texto_literal(self):
        self.read(90)
        alerta = Alerta.objects.get()
        evidence = dict(alerta.dados_deteccao, descricao='Temperatura < limite & motor <A>. ' * 120)
        Alerta.objects.filter(pk=alerta.pk).update(dados_deteccao=evidence)
        for formato, content_type in [('csv', 'text/csv'), ('excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('pdf', 'application/pdf')]:
            response = self.client.get(reverse('exportar-alertas', args=[formato]), {'sensor': self.sensor.pk})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Type'].startswith(content_type))
            if formato == 'pdf':
                self.assertTrue(response.content.startswith(b'%PDF'))
            elif formato == 'csv':
                self.assertIn('Temperatura < limite & motor <A>', response.content.decode('utf-8-sig'))

    def test_dashboard_conta_aberturas_de_24h_inclusive_normalizadas(self):
        now = timezone.now()
        old = self.legacy(status='ativo')
        Alerta.objects.filter(pk=old.pk).update(data_alerta=now - timedelta(hours=25), data_ultima_analise=now)
        future = self.legacy()
        Alerta.objects.filter(pk=future.pk).update(data_alerta=now + timedelta(minutes=1))
        for i in range(8):
            recent = self.legacy(nivel='medio', status='resolvido')
            Alerta.objects.filter(pk=recent.pk).update(data_alerta=now - timedelta(minutes=i))
        boundary = self.legacy(nivel='critico')
        Alerta.objects.filter(pk=boundary.pk).update(data_alerta=now - timedelta(hours=24))
        with patch('manutencao.dashboards.views.timezone.now', return_value=now):
            data = self.client.get(reverse('dashboard-summary')).data
        self.assertEqual(data['alertas_24h']['total'], 9)
        self.assertEqual(data['alertas_24h']['medio'], 8)
        self.assertEqual(len(data['alertas_recentes']), 6)
        self.assertNotIn(old.pk, [row['id'] for row in data['alertas_recentes']])
        self.assertEqual(data['alertas_ativos']['total'], 3)

    def test_admin_exibe_registro_sem_permissoes_de_mutacao(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        request = RequestFactory().get('/')
        request.user = self.user
        admin = AlertaAdmin(Alerta, AdminSite())
        self.assertTrue(admin.has_view_permission(request))
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request))
        self.assertFalse(admin.has_delete_permission(request))
