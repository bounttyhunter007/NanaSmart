from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Empresa, Equipamento, PlanoManutencao
from manutencao.models import OrdemServico
from accounts.models import Usuario

class AtivosTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Alpha", cnpj="111", email="a@a.com")
        self.user = Usuario.objects.create_user(
            username="gestor_ativos", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.client.force_authenticate(user=self.user)
        self.equip_url = reverse('equipamento-list')

    def test_create_equipamento(self):
        """Testa a criação de equipamento e se o horímetro padrão é 0.0."""
        data = {
            "nome": "Motor Teste",
            "tipo": "Motor",
            "numero_serie": "SN-001",
            "empresa": self.empresa.id
        }
        response = self.client.post(self.equip_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['horimetro'], 0.0)

class PlanoManutencaoTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Beta", cnpj="222", email="b@b.com")
        self.user = Usuario.objects.create_user(
            username="gestor_planos", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.client.force_authenticate(user=self.user)
        self.motor = Equipamento.objects.create(
            nome="Motor Preditivo", tipo="Motor", numero_serie="PRED-999", 
            empresa=self.empresa, horimetro=200.0
        )
        self.plano_url = reverse('planomanutencao-list')

    def test_horimetro_trigger(self):
        """Testa se a O.S. preditiva é gerada corretamente ao atingir o horímetro."""
        # Cria plano de 100h (proximo disparo em 300h pois o motor já tem 200h)
        plano_data = {
            "equipamento": self.motor.id,
            "nome_servico": "Troca de Óleo",
            "descricao": "Serviço de teste",
            "intervalo_horas": 100.0,
            "prioridade": "medio"
        }
        self.client.post(self.plano_url, plano_data)
        
        # 1. Atualiza para 250h (não deve gerar OS)
        self.motor.horimetro = 250.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 0)

        # 2. Atualiza para 310h (DEVE gerar OS)
        self.motor.horimetro = 310.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)
        
        # 3. Teste anti-duplicação (315h não gera nova OS)
        self.motor.horimetro = 315.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)
