from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from manutencao.models import OrdemServico, HistoricoManutencao
from alertas.models import Alerta
from telemetria.models import Sensor, Telemetria


class GeminiApiTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Gamma", cnpj="99999999999999", email="gamma@example.com")
        self.gestor = Usuario.objects.create_user(
            username="gestor_gemini",
            password="123456",
            tipo_usuario="gestor",
            empresa=self.empresa,
        )
        self.tecnico = Usuario.objects.create_user(
            username="tecnico_gemini",
            password="123456",
            tipo_usuario="tecnico",
            empresa=self.empresa,
        )
        self.equipamento = Equipamento.objects.create(
            empresa=self.empresa,
            nome="Bomba Teste",
            tipo="bomba_hidraulica",
            numero_serie="BPT-001",
        )

        self.os_aberta = OrdemServico.objects.create(
            equipamento=self.equipamento,
            titulo="Troca de vedação",
            descricao="Verificar vazamento",
            status="pendente",
            prioridade="medio",
        )
        self.os_atribuida = OrdemServico.objects.create(
            equipamento=self.equipamento,
            titulo="Inspeção elétrica",
            descricao="Verificar painel",
            responsavel=self.tecnico,
            status="andamento",
            prioridade="critico",
        )
        self.os_concluida = OrdemServico.objects.create(
            equipamento=self.equipamento,
            titulo="Revisão geral",
            descricao="Revisão finalizada",
            status="concluida",
            prioridade="medio",
        )
        HistoricoManutencao.objects.update_or_create(
            ordem_servico=self.os_concluida,
            defaults={
                'descricao_servico': "Troca de rolamentos",
                'data_execucao': "2026-05-20",
                'custo_pecas': 120.00,
                'custo_mao_de_obra': 80.00,
            },
        )
        Alerta.objects.create(
            equipamento=self.equipamento,
            tipo_alerta="Vazamento",
            nivel="medio",
            descricao="Vazamento detectado no acoplamento",
            status="ativo",
        )
        sensor = Sensor.objects.create(
            equipamento=self.equipamento,
            nome="Sensor de Pressão",
            tipo="pressao",
            unidade_medida="bar",
            limite_alerta=10.0,
            ativo=True,
        )
        Telemetria.objects.create(sensor=sensor, valor=8.5)

    @patch.dict('os.environ', {'GEMINI_API_KEY': ''})
    def test_chat_endpoint_returns_missing_key_message(self):
        self.client.force_authenticate(user=self.gestor)
        url = reverse('gemini_chat')
        response = self.client.post(url, {'message': 'Qual é a situação atual?'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('GEMINI_API_KEY', response.data['response'])
        self.assertIn('habilitar o chat', response.data['response'])

    @patch.dict('os.environ', {'GEMINI_API_KEY': ''})
    def test_os_analysis_endpoint_returns_missing_key_message(self):
        self.client.force_authenticate(user=self.gestor)
        url = reverse('gemini_ordens_analise')
        response = self.client.post(url, {'message': 'Preciso de prioridade nas ordens.'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('GEMINI_API_KEY', response.data['response'])
        self.assertIn('habilitar este endpoint', response.data['response'])

    @patch.dict('os.environ', {'GEMINI_API_KEY': ''})
    def test_unassigned_orders_endpoint_returns_missing_key_message(self):
        self.client.force_authenticate(user=self.gestor)
        url = reverse('gemini_ordens_sem_atribuicao')
        response = self.client.post(url, {'message': 'Como devo alocar as ordens?'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('GEMINI_API_KEY', response.data['response'])
        self.assertIn('habilitar este endpoint', response.data['response'])

    def test_finance_endpoint_for_tecnico_is_forbidden(self):
        self.client.force_authenticate(user=self.tecnico)
        url = reverse('gemini_gestao_financeira')
        response = self.client.post(url, {'message': 'Como reduzir custos?'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('técnico', response.data['response'].lower())

    @patch.dict('os.environ', {'GEMINI_API_KEY': ''})
    def test_finance_endpoint_for_gestor_returns_missing_key_message(self):
        self.client.force_authenticate(user=self.gestor)
        url = reverse('gemini_gestao_financeira')
        response = self.client.post(url, {'message': 'Preciso de um plano financeiro.'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('GEMINI_API_KEY', response.data['response'])
        self.assertIn('habilitar este endpoint', response.data['response'])

    def test_missing_message_returns_bad_request(self):
        self.client.force_authenticate(user=self.gestor)
        url = reverse('gemini_chat')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)
        self.assertGreater(len(response.data['message']), 0)

    def test_trend_analysis_rejects_sensor_from_another_company(self):
        outra_empresa = Empresa.objects.create(
            nome='Outra Empresa',
            cnpj='88888888888888',
            email='outra@example.com',
        )
        outro_equipamento = Equipamento.objects.create(
            empresa=outra_empresa,
            nome='Outra Bomba',
            tipo='bomba_hidraulica',
            numero_serie='BPT-002',
        )
        outro_sensor = Sensor.objects.create(
            equipamento=outro_equipamento,
            nome='Sensor privado',
            tipo='pressao',
            unidade_medida='bar',
            limite_alerta=10.0,
        )
        self.client.force_authenticate(user=self.gestor)

        response = self.client.post(
            reverse('gemini_tendencia'),
            {'message': 'Analise o sensor', 'sensor_id': outro_sensor.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trend_analysis_rejects_invalid_sensor_id(self):
        self.client.force_authenticate(user=self.gestor)

        response = self.client.post(
            reverse('gemini_tendencia'),
            {'message': 'Analise o sensor', 'sensor_id': 'invalid'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_edit_and_reset_prompt_configuration(self):
        admin = Usuario.objects.create_user(
            username='admin_prompts',
            password='password123',
            tipo_usuario='admin',
        )
        self.client.force_authenticate(user=admin)

        list_response = self.client.get(reverse('gemini_prompts_list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        prompt_id = list_response.data[0]['id']

        detail_url = reverse('gemini_prompts_detail', args=[prompt_id])
        update_response = self.client.patch(
            detail_url,
            {'custom_text': 'Instrução customizada'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['custom_text'], 'Instrução customizada')

        reset_response = self.client.post(
            reverse('gemini_prompts_reset', args=[prompt_id]),
            format='json',
        )
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reset_response.data['custom_text'], '')

    @patch('gemini_api.views.is_gemini_available', return_value=True)
    @patch('gemini_api.views.generate_content', return_value=('Análise simulada', 'teste'))
    def test_trend_analysis_uses_authorized_sensor(self, mock_generate, mock_available):
        self.client.force_authenticate(user=self.gestor)

        response = self.client.post(
            reverse('gemini_tendencia'),
            {'message': 'Analise o sensor', 'sensor_id': self.equipamento.sensores.first().id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model_used'], 'teste')
        mock_generate.assert_called_once()
