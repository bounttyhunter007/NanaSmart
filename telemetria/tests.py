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
            equipamento=self.motor, tipo_sensor="temperatura", unidade_medida="°C", limite_alerta=100.0
        )
        self.leitura_url = reverse('telemetria-list')

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
        self.assertEqual(os.prioridade, 'baixo')

        # 2. Alerta Médio (90% de 100 = 90.0) -> Escalada
        data_medio = {"sensor": self.sensor.id, "valor": 90.0}
        self.client.post(self.leitura_url, data_medio)
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'medio')
        
        os.refresh_from_db()
        self.assertEqual(os.prioridade, 'medio')

        # 3. Alerta Crítico (110% de 100 = 110.0) -> Escalada Máxima
        data_critico = {"sensor": self.sensor.id, "valor": 110.0}
        self.client.post(self.leitura_url, data_critico)
        alerta.refresh_from_db()
        self.assertEqual(alerta.nivel, 'critico')
        
        os.refresh_from_db()
        self.assertEqual(os.prioridade, 'critico')
