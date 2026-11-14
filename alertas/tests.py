from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Usuario
from ativos.models import Empresa, Equipamento
from manutencao.models import OrdemServico
from telemetria.models import Sensor, Telemetria
from .models import Alerta


class SensorHistoryTests(APITestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nome='Operação', cnpj='SENSOR-HISTORY', email='qa@example.test')
        self.equipment = Equipamento.objects.create(empresa=self.company, nome='Bomba', numero_serie='SN-HISTORY')
        self.sensor = Sensor.objects.create(equipamento=self.equipment, nome='Pressão', tipo='pressao',
            unidade_medida='bar', limite_alerta=12, limite_alerta_baixo_pct=60,
            limite_alerta_medio_pct=85, limite_alerta_critico_pct=98)
        self.manager = Usuario.objects.create_user(username='history-manager', tipo_usuario='gestor', empresa=self.company)
        self.tech = Usuario.objects.create_user(username='history-tech', tipo_usuario='tecnico', empresa=self.company)
        self.other = Usuario.objects.create_user(username='history-other', tipo_usuario='tecnico', empresa=self.company)
        self.client.force_authenticate(self.manager)

    def alert(self, **kwargs):
        return Alerta.objects.create(equipamento=self.equipment, sensor=self.sensor,
            tipo_alerta='Ocorrência', descricao='Condição observada', **kwargs)

    def history(self, **kwargs):
        return self.client.get('/api/alertas/', {'sensor':self.sensor.pk, **kwargs})

    def test_severity_is_default_and_recent_order_is_explicit_before_pagination(self):
        old = self.alert(nivel='critico')
        newer = self.alert(nivel='baixo')
        newest = self.alert(nivel='medio')
        Alerta.objects.filter(pk=old.pk).update(data_alerta=timezone.now()-timedelta(days=3))
        self.assertEqual([a['id'] for a in self.history().data['results']], [old.pk, newest.pk, newer.pk])
        first = self.history(ordenacao='recentes', limit=1)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['count'], 3)
        self.assertEqual(first.data['results'][0]['id'], newest.pk)
        second = self.client.get(first.data['next'])
        self.assertEqual(second.data['results'][0]['id'], newer.pk)
        self.assertEqual(self.history(ordenacao='invalid').status_code, 400)
        # Mesmo instante: ID desempata deterministicamente.
        Alerta.objects.all().update(data_alerta=timezone.now())
        self.assertEqual([a['id'] for a in self.history(ordenacao='recentes').data['results']], [newest.pk, newer.pk, old.pk])

    @patch('telemetria.signals.sync_sensor_trend')
    def test_two_normalized_occurrences_keep_one_pending_corrective_without_predictive(self, _trend):
        for value in (7.3, 10.3, 13.17, 5.6, 5.6, 8, 5.6, 5.642):
            Telemetria.objects.create(sensor=self.sensor, valor=value)
        occurrences = self.history(ordenacao='recentes', limit=10).data['results']
        self.assertEqual(len(occurrences), 2)
        self.assertTrue(all(a['status'] == 'resolvido' and a['data_normalizacao'] for a in occurrences))
        self.assertEqual(occurrences[1]['nivel'], 'critico')
        self.assertEqual([h['nivel'] for h in occurrences[1]['historico_niveis']], ['medio','critico'])
        open_orders = self.client.get('/api/ordens-servico/', {'sensor_origem':self.sensor.pk, 'abertas':'true', 'limit':3})
        self.assertEqual(open_orders.data['count'], 1)
        order = open_orders.data['results'][0]
        self.assertEqual((order['tipo_os'], order['status']), ('corretiva','pendente'))
        self.assertEqual({a['ordem_servico_id'] for a in occurrences}, {order['id']})
        self.assertTrue(all(a['ordem_servico_acessivel'] for a in occurrences))
        self.assertFalse(OrdemServico.objects.filter(tipo_os='preditiva').exists())
        self.assertEqual(self.client.get('/api/ordens-servico/', {'sensor_origem':self.sensor.pk}).data['count'], 1)

    def test_order_links_respect_role_visibility_including_legacy_reverse_link(self):
        restricted = self.alert(origem='tendencia')
        hidden_order = OrdemServico.objects.create(equipamento=self.equipment, sensor_origem=self.sensor,
            alerta_origem=restricted, responsavel=self.other, tipo_os='preditiva', titulo='Acesso restrito')
        accessible = self.alert(origem='limite', ordem_servico=hidden_order)
        own_order = OrdemServico.objects.create(equipamento=self.equipment, sensor_origem=self.sensor,
            responsavel=self.tech, tipo_os='corretiva', titulo='Inspecionar bomba')
        Alerta.objects.filter(pk=accessible.pk).update(ordem_servico=own_order)
        self.client.force_authenticate(self.tech)
        rows = {a['id']:a for a in self.history(ordenacao='recentes').data['results']}
        self.assertFalse(rows[restricted.pk]['ordem_servico_acessivel'])
        self.assertTrue(rows[accessible.pk]['ordem_servico_acessivel'])
        self.assertNotIn('titulo', rows[restricted.pk])
        self.assertEqual(self.client.get(f'/api/ordens-servico/{hidden_order.pk}/').status_code, 404)
        other_company = Empresa.objects.create(nome='Outra', cnpj='OTHER-HISTORY', email='other@example.test')
        outsider = Usuario.objects.create_user(username='history-foreign', tipo_usuario='gestor', empresa=other_company)
        self.client.force_authenticate(outsider)
        self.assertEqual(self.history(ordenacao='recentes').data['count'], 0)
        self.assertEqual(self.client.get('/api/ordens-servico/', {'sensor_origem':self.sensor.pk}).data['count'], 0)

    def test_open_summary_and_all_orders_include_closed_and_other_types_with_pagination(self):
        for i in range(12):
            OrdemServico.objects.create(equipamento=self.equipment, sensor_origem=self.sensor,
                tipo_os='corretiva' if i % 2 else 'preditiva', titulo=f'Inspeção {i}',
                status='pendente' if i < 4 else 'cancelada' if i % 2 else 'concluida',
                data_abertura=timezone.now()-timedelta(days=20))
        opened = self.client.get('/api/ordens-servico/', {'sensor_origem':self.sensor.pk, 'abertas':'true','limit':3})
        self.assertEqual(opened.data['count'], 4)
        self.assertEqual(len(opened.data['results']), 3)
        history = self.client.get('/api/ordens-servico/', {'sensor_origem':self.sensor.pk, 'limit':10})
        self.assertEqual(history.data['count'], 12)
        self.assertEqual(len(history.data['results']), 10)
        self.assertEqual(len(self.client.get(history.data['next']).data['results']), 2)
        empty_sensor = Sensor.objects.create(equipamento=self.equipment, nome='Sem dados', tipo='pressao', unidade_medida='bar',limite_alerta=12)
        self.assertEqual(self.client.get('/api/alertas/', {'sensor':empty_sensor.pk,'ordenacao':'recentes'}).data['count'], 0)
