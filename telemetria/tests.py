from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Sensor, Telemetria
from ativos.models import Equipamento, Empresa
from alertas.models import Alerta
from manutencao.models import OrdemServico
from accounts.models import Usuario

class TelemetriaAlertTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Gamma", cnpj="333", email="g@g.com")
        self.user = Usuario.objects.create_user(
            username="gestor_telemetria", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.client.force_authenticate(user=self.user)
        self.motor = Equipamento.objects.create(
            nome="Motor Telemetria", tipo="Motor Elétrico", numero_serie="TEL-001", empresa=self.empresa
        )
        self.sensor = Sensor.objects.create(
            equipamento=self.motor,
            nome="Sensor Temp",
            tipo="temperatura",
            unidade_medida="°C",
            limite_alerta=100.0
        )
        self.leitura_url = reverse('leituras-list')

    def test_alert_escalation(self):
        """Testa se os alertas e O.S. são gerados e escalados conforme o valor da leitura."""
        # 1. Alerta Baixo (75% de 100 = 75.0)
        data_baixo = {"sensor": self.sensor.id, "valor": 75.0}
        self.client.post(self.leitura_url, data_baixo)
        alerta = Alerta.objects.filter(equipamento=self.motor, status='ativo').first()
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.nivel, 'baixo')
        
        os = OrdemServico.objects.filter(equipamento=self.motor, status='pendente').first()
        self.assertIsNotNone(os)
        self.assertEqual(os.prioridade, 'alta')  # Sem criticidade avaliada: triagem conservadora.

        # 2. Alerta Médio (90% de 100 = 90.0) -> Escalada
        data_medio = {"sensor": self.sensor.id, "valor": 90.0}
        self.client.post(self.leitura_url, data_medio)
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'medio')
        
        os.refresh_from_db()
        self.assertEqual(os.prioridade, 'alta')

        # 3. Alerta Crítico (110% de 100 = 110.0) -> Escalada Máxima
        data_critico = {"sensor": self.sensor.id, "valor": 110.0}
        self.client.post(self.leitura_url, data_critico)
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'critico')
        
        os.refresh_from_db()
        self.assertEqual(os.prioridade, 'critica')

    def test_custom_alert_thresholds(self):
        sensor = Sensor.objects.create(
            equipamento=self.motor,
            nome="Sensor Temp Custom",
            tipo="temperatura",
            unidade_medida="°C",
            limite_alerta=120.0,
            limite_alerta_baixo_pct=60.0,
            limite_alerta_medio_pct=90.0,
            limite_alerta_critico_pct=95.0,
        )

        # Alerta baixo quando atingir 72.0 (60% de 120)
        self.client.post(self.leitura_url, {"sensor": sensor.id, "valor": 72.0})
        alerta = Alerta.objects.filter(equipamento=self.motor, tipo_alerta=f"Alerta de {sensor.get_tipo_display()}", status='ativo').first()
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.nivel, 'baixo')

        # Escalada para médio aos 108.0 (90% de 120)
        self.client.post(self.leitura_url, {"sensor": sensor.id, "valor": 108.0})
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'medio')

        # Escalada para crítico aos 114.0 (95% de 120)
        self.client.post(self.leitura_url, {"sensor": sensor.id, "valor": 114.0})
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'critico')

    def test_tecnico_nao_pode_inserir_leitura(self):
        tecnico = Usuario.objects.create_user(
            username='tecnico_leitura', password='123', tipo_usuario='tecnico', empresa=self.empresa
        )
        self.client.force_authenticate(user=tecnico)

        response = self.client.post(self.leitura_url, {'sensor': self.sensor.id, 'valor': 10.0}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_gestor_cannot_write_telemetry_resources_for_another_company(self):
        outra_empresa = Empresa.objects.create(
            nome='Outra Gamma', cnpj='334', email='outra@g.com'
        )
        outro_motor = Equipamento.objects.create(
            nome='Motor de outra empresa',
            numero_serie='TEL-CROSS',
            empresa=outra_empresa,
        )
        outro_sensor = Sensor.objects.create(
            equipamento=outro_motor,
            nome='Sensor privado',
            tipo='temperatura',
            unidade_medida='°C',
            limite_alerta=100,
        )

        sensor_response = self.client.post(
            reverse('sensores-list'),
            {
                'equipamento': outro_motor.id,
                'nome': 'Sensor indevido',
                'tipo': 'temperatura',
                'unidade_medida': '°C',
                'limite_alerta': 100,
            },
            format='json',
        )
        reading_response = self.client.post(
            self.leitura_url,
            {'sensor': outro_sensor.id, 'valor': 80},
            format='json',
        )
        alert_response = self.client.post(
            reverse('alertas-list'),
            {
                'equipamento': outro_motor.id,
                'tipo_alerta': 'Alerta indevido',
                'nivel': 'critico',
                'descricao': 'Teste',
                'status': 'ativo',
            },
            format='json',
        )
        trend_response = self.client.post(
            reverse('trend-config-list'),
            {
                'sensor': outro_sensor.id,
                'periodo_horas': 24,
                'num_leituras': 50,
                'sensibilidade': 'media',
                'ativo': True,
            },
            format='json',
        )
        global_config_response = self.client.post(
            reverse('trend-config-list'),
            {
                'sensor': None,
                'periodo_horas': 24,
                'num_leituras': 50,
                'sensibilidade': 'media',
                'ativo': True,
            },
            format='json',
        )

        for response in (
            sensor_response,
            reading_response,
            alert_response,
            trend_response,
            global_config_response,
        ):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TrendDashboardTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome='Empresa A', cnpj='TREND-001', email='a@example.com'
        )
        self.outra_empresa = Empresa.objects.create(
            nome='Empresa B', cnpj='TREND-002', email='b@example.com'
        )
        self.gestor = Usuario.objects.create_user(
            username='gestor_tendencia',
            password='password123',
            tipo_usuario='gestor',
            empresa=self.empresa,
        )
        self.equipamento = Equipamento.objects.create(
            empresa=self.empresa,
            nome='Motor A',
            numero_serie='TREND-EQ-001',
        )
        self.sensor = Sensor.objects.create(
            equipamento=self.equipamento,
            nome='Temperatura A',
            tipo='temperatura',
            unidade_medida='°C',
            limite_alerta=100,
        )
        outro_equipamento = Equipamento.objects.create(
            empresa=self.outra_empresa,
            nome='Motor B',
            numero_serie='TREND-EQ-002',
        )
        self.sensor_outra_empresa = Sensor.objects.create(
            equipamento=outro_equipamento,
            nome='Temperatura B',
            tipo='temperatura',
            unidade_medida='°C',
            limite_alerta=100,
        )
        self.client.force_authenticate(user=self.gestor)
        self.url = reverse('trend-dashboard')

    def test_sensor_trend_is_available_to_its_company(self):
        response = self.client.get(self.url, {'sensor_id': self.sensor.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sensor_id'], self.sensor.id)

    def test_sensor_trend_is_hidden_from_other_companies(self):
        response = self.client.get(
            self.url, {'sensor_id': self.sensor_outra_empresa.id}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_sensor_id_returns_bad_request(self):
        response = self.client.get(self.url, {'sensor_id': 'invalid'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
