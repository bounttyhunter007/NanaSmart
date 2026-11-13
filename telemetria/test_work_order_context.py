from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Usuario
from ativos.models import Empresa, Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from .models import Sensor
from .work_order_context import attach_predictive_order_summaries


class PredictiveAttendanceTests(APITestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nome='Atendimento', cnpj='ATTEND', email='qa@example.test')
        self.equipment = Equipamento.objects.create(empresa=self.company, nome='Motor', numero_serie='ATTEND')
        self.sensor = self.make_sensor('Mancal')
        self.manager = Usuario.objects.create_user(username='attendance-manager', tipo_usuario='gestor', empresa=self.company)
        self.technician = Usuario.objects.create_user(username='attendance-tech', tipo_usuario='tecnico', empresa=self.company)
        self.other_technician = Usuario.objects.create_user(username='attendance-other', tipo_usuario='tecnico', empresa=self.company)
        self.client.force_authenticate(self.manager)

    def make_sensor(self, name):
        return Sensor.objects.create(equipamento=self.equipment, nome=name, tipo='temperatura',
                                     unidade_medida='°C', limite_alerta=100)

    def order(self, status='pendente', sensor=None, **kwargs):
        return OrdemServico.objects.create(equipamento=self.equipment, sensor_origem=sensor or self.sensor,
                                            tipo_os='preditiva', titulo='Inspecionar mancal', status=status, **kwargs)

    def summary(self):
        response = self.client.get(f'/api/telemetria/tendencias/?sensor_id={self.sensor.pk}')
        self.assertEqual(response.status_code, 200)
        return response.data['predictive_orders_summary']

    def test_open_order_remains_visible_after_alert_normalizes_and_analysis_is_insufficient(self):
        alert = Alerta.objects.create(equipamento=self.equipment, sensor=self.sensor, origem='tendencia',
                                      tipo_alerta='Tendência', status='resolvido', descricao='Normalizou')
        order = self.order(alerta_origem=alert)
        result = self.summary()
        self.assertEqual(result['open_count'], 1)
        self.assertEqual(result['primary_order']['id'], order.pk)
        self.assertEqual(result['primary_order']['status'], 'pendente')
        order.status = 'andamento'
        order.save()
        self.assertEqual(self.summary()['primary_order']['status'], 'andamento')

    def test_multiple_open_orders_are_counted_and_latest_open_precedes_recent_closed(self):
        self.order(data_abertura=timezone.now() - timedelta(days=3))
        latest_open = self.order('andamento', data_abertura=timezone.now() - timedelta(days=2))
        self.order('concluida')
        result = self.summary()
        self.assertEqual(result['total'], 3)
        self.assertEqual(result['open_count'], 2)
        self.assertEqual(result['primary_order']['id'], latest_open.pk)

    def test_latest_closed_is_returned_without_open_orders(self):
        self.order('concluida', data_abertura=timezone.now() - timedelta(days=1))
        latest = self.order('cancelada')
        result = self.summary()
        self.assertEqual(result['open_count'], 0)
        self.assertEqual(result['primary_order']['id'], latest.pk)
        self.assertEqual(result['primary_order']['status'], 'cancelada')

    def test_corrective_orders_and_other_sensors_do_not_count(self):
        other = self.make_sensor('Outro mancal')
        self.order(sensor=other)
        OrdemServico.objects.create(equipamento=self.equipment, sensor_origem=self.sensor,
                                     tipo_os='corretiva', titulo='Limite real')
        self.assertEqual(self.summary(), {'total': 0, 'open_count': 0, 'primary_order': None})

    def test_technician_only_sees_own_or_unassigned_orders_in_summary_and_history(self):
        assigned = self.order(responsavel=self.technician)
        unassigned = self.order()
        hidden = self.order(responsavel=self.other_technician)
        self.client.force_authenticate(self.technician)
        result = self.summary()
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['primary_order']['id'], unassigned.pk)
        history = self.client.get(f'/api/ordens-servico/?sensor_origem={self.sensor.pk}&historico_preditivo=true')
        self.assertEqual(history.status_code, 200)
        self.assertEqual({row['id'] for row in history.data['results']}, {assigned.pk, unassigned.pk})
        self.assertNotIn(hidden.pk, {row['id'] for row in history.data['results']})

    def test_company_isolation_in_summary_history_and_direct_sensor_query(self):
        self.order()
        foreign_company = Empresa.objects.create(nome='Outra', cnpj='FOREIGN-ATTEND', email='other@example.test')
        foreign = Usuario.objects.create_user(username='attendance-foreign', tipo_usuario='gestor', empresa=foreign_company)
        self.client.force_authenticate(foreign)
        self.assertEqual(self.client.get(f'/api/telemetria/tendencias/?sensor_id={self.sensor.pk}').status_code, 404)
        history = self.client.get(f'/api/ordens-servico/?sensor_origem={self.sensor.pk}&historico_preditivo=true')
        self.assertEqual(history.data['count'], 0)

    def test_history_filters_legacy_sensor_link_and_orders_open_first_with_pagination(self):
        alert = Alerta.objects.create(equipamento=self.equipment, sensor=self.sensor, origem='tendencia',
                                      tipo_alerta='Legado', status='resolvido', descricao='Detecção anterior')
        legacy = OrdemServico.objects.create(equipamento=self.equipment, alerta_origem=alert,
                                             tipo_os='preditiva', titulo='Legado')
        closed = self.order('concluida')
        self.assertEqual(self.summary()['primary_order']['id'], legacy.pk)
        first = self.client.get(f'/api/ordens-servico/?sensor_origem={self.sensor.pk}&historico_preditivo=true&limit=1')
        self.assertEqual(first.data['count'], 2)
        self.assertEqual(first.data['results'][0]['id'], legacy.pk)
        second = self.client.get(first.data['next'])
        self.assertEqual(second.data['results'][0]['id'], closed.pk)

    def test_summaries_use_two_queries_regardless_of_sensor_count_and_exclude_heavy_fields(self):
        sensors = [self.sensor] + [self.make_sensor(str(i)) for i in range(12)]
        for sensor in sensors:
            self.order(sensor=sensor)
        trends = [{'sensor_id': sensor.pk} for sensor in sensors]
        with CaptureQueriesContext(connection) as captured:
            attach_predictive_order_summaries(trends, self.manager)
        self.assertEqual(len(captured), 2)
        self.assertTrue(all(t['predictive_orders_summary']['open_count'] == 1 for t in trends))
        for query in captured:
            self.assertNotIn('evidencia_preditiva', query['sql'])
            self.assertNotIn('"descricao"', query['sql'])

    def test_list_endpoint_includes_the_same_summaries_as_individual_sensor(self):
        order = self.order()
        response = self.client.get('/api/telemetria/tendencias/?all=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['predictive_orders_summary']['primary_order']['id'], order.pk)
