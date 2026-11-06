from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from .models import CriteriosCriticidade, Equipamento, HistoricoCriticidadeEquipamento
from .services import CRITERIOS_SUGERIDOS


class CriteriosABCTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='ABC', cnpj='ABC', email='abc@example.com')
        self.outra = Empresa.objects.create(nome='Outra', cnpj='OUTRA-ABC', email='o@example.com')
        self.gestor = Usuario.objects.create_user(username='abc', tipo_usuario='gestor', empresa=self.empresa)
        self.tecnico = Usuario.objects.create_user(username='abc-tec', tipo_usuario='tecnico', empresa=self.empresa)
        self.client.force_authenticate(self.gestor)
        self.url = reverse('criterios-criticidade-list')
        self.payload = dict(CRITERIOS_SUGERIDOS, empresa=self.empresa.pk,
                            representante_manutencao='Representante de teste', data_validacao=str(timezone.localdate()))
        self.equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Motor', numero_serie='ABC')

    def test_consultar_sugestao_nao_publica_criterios(self):
        response = self.client.get(reverse('criterios-criticidade-atual'), {'empresa': self.empresa.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['revisao'])
        self.assertEqual(response.data['criterio_a'], CRITERIOS_SUGERIDOS['criterio_a'])
        self.assertFalse(CriteriosCriticidade.objects.exists())

    def test_publicacao_e_revisoes_imutaveis_com_isolamento(self):
        primeira = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(primeira.status_code, 201, primeira.data)
        segunda = self.client.post(self.url, dict(self.payload, criterio_b='Impacto intermediário revisado'), format='json')
        self.assertEqual(segunda.data['revisao'], 2)
        antiga = CriteriosCriticidade.objects.get(pk=primeira.data['id'])
        self.assertEqual(antiga.criterio_b, CRITERIOS_SUGERIDOS['criterio_b'])
        detail = reverse('criterios-criticidade-detail', args=[antiga.pk])
        self.assertEqual(self.client.patch(detail, {'criterio_a': 'Sobrescrita'}).status_code, 405)
        self.assertEqual(self.client.delete(detail).status_code, 405)
        self.assertEqual(self.client.post(self.url, dict(self.payload, empresa=self.outra.pk)).status_code, 400)
        self.assertEqual(self.client.get(reverse('criterios-criticidade-atual'), {'empresa': self.outra.pk}).status_code, 404)

    def test_dados_de_validacao_obrigatorios_e_sem_data_futura(self):
        for field in ('criterio_a', 'criterio_b', 'criterio_c', 'representante_manutencao', 'data_validacao'):
            with self.subTest(field=field):
                self.assertEqual(self.client.post(self.url, dict(self.payload, **{field: '  '})).status_code, 400)
        futura = str(timezone.localdate() + timedelta(days=1))
        self.assertEqual(self.client.post(self.url, dict(self.payload, data_validacao=futura)).status_code, 400)

    def test_tecnico_consulta_mas_nao_publica(self):
        self.client.force_authenticate(self.tecnico)
        self.assertEqual(self.client.get(reverse('criterios-criticidade-atual')).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.payload).status_code, 403)

    def test_classificacao_requer_guia_e_motivo_e_audita_revisao(self):
        detail = reverse('equipamentos-detail', args=[self.equipamento.pk])
        payload = {'criticidade': 'A', 'justificativa_criticidade': 'Sem redundância; para o processo.'}
        self.assertEqual(self.client.patch(detail, payload).status_code, 400)
        guia = self.client.post(self.url, self.payload, format='json').data
        self.assertEqual(self.client.patch(detail, dict(payload, justificativa_criticidade='   ')).status_code, 400)
        response = self.client.patch(detail, payload)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['criterios_utilizados']['id'], guia['id'])
        self.client.post(self.url, dict(self.payload, criterio_a='Nova interpretação'), format='json')
        equipment = self.client.get(detail).data
        self.assertEqual(equipment['criterios_utilizados']['revisao'], 1)
        self.assertEqual(self.client.patch(detail, {'justificativa_criticidade': 'Parada total confirmada.'}).status_code, 200)
        historico = HistoricoCriticidadeEquipamento.objects.filter(equipamento=self.equipamento)
        self.assertEqual(historico.count(), 2)
        self.assertEqual(historico.first().criterios_criticidade.revisao, 2)
        self.assertEqual(historico.last().criterios_criticidade.revisao, 1)
        self.assertEqual(historico.first().alterado_por, self.gestor)
        self.assertEqual(historico.first().dados_anteriores['justificativa'], payload['justificativa_criticidade'])

    def test_historico_restrito_ao_equipamento_e_empresa(self):
        other = Equipamento.objects.create(empresa=self.outra, nome='Outro', numero_serie='ABC-OUTRO')
        HistoricoCriticidadeEquipamento.objects.create(equipamento=other, criticidade_nova='B')
        HistoricoCriticidadeEquipamento.objects.create(equipamento=self.equipamento, criticidade_nova='C')
        response = self.client.get(reverse('historico-criticidade-list'), {'equipamento': other.pk})
        self.assertEqual(response.data['count'], 0)
        response = self.client.get(reverse('historico-criticidade-list'), {'equipamento': self.equipamento.pk})
        self.assertEqual(response.data['count'], 1)

    def test_classe_d_e_transferencia_de_empresa_rejeitadas(self):
        self.client.force_authenticate(Usuario.objects.create_user(username='abc-admin', tipo_usuario='admin'))
        detail = reverse('equipamentos-detail', args=[self.equipamento.pk])
        self.assertEqual(self.client.patch(detail, {'criticidade': 'D'}).status_code, 400)
        self.assertEqual(self.client.patch(detail, {'empresa': self.outra.pk}).status_code, 400)
