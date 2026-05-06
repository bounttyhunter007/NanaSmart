from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import OrdemServico, HistoricoManutencao
from ativos.models import Equipamento, Empresa
from accounts.models import Usuario

class OSTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Delta", cnpj="444", email="d@d.com")
        self.gestor = Usuario.objects.create_user(
            username="gestor_os", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.tecnico1 = Usuario.objects.create_user(
            username="tecnico_1", password="123", tipo_usuario="tecnico", empresa=self.empresa
        )
        self.tecnico2 = Usuario.objects.create_user(
            username="tecnico_2", password="123", tipo_usuario="tecnico", empresa=self.empresa
        )
        self.motor = Equipamento.objects.create(
            nome="Motor OS", tipo="Motor", numero_serie="OS-001", empresa=self.empresa
        )
        self.os_url = reverse('ordemservico-list')

    def test_tecnico_visibility(self):
        """Testa se o técnico vê apenas O.S. sem responsável ou atribuídas a ele."""
        # 1. OS sem responsável (Todos os técnicos da empresa devem ver)
        os_livre = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Livre", descricao="Teste", responsavel=None
        )
        # 2. OS atribuída ao Tecnico 1
        os_tec1 = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Tec 1", descricao="Teste", responsavel=self.tecnico1
        )
        # 3. OS atribuída ao Tecnico 2
        os_tec2 = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Tec 2", descricao="Teste", responsavel=self.tecnico2
        )

        # Autentica como Tecnico 1
        self.client.force_authenticate(user=self.tecnico1)
        response = self.client.get(self.os_url)
        
        # Deve ver a "Livre" e a "Tec 1", mas NÃO a "Tec 2"
        self.assertEqual(len(response.data), 2)
        titulos = [item['titulo'] for item in response.data]
        self.assertIn("OS Livre", titulos)
        self.assertIn("OS Tec 1", titulos)
        self.assertNotIn("OS Tec 2", titulos)

    def test_tecnico_cannot_delete(self):
        """Garante que técnicos não podem deletar ordens de serviço."""
        os = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Protegida", descricao="Teste"
        )
        self.client.force_authenticate(user=self.tecnico1)
        url = reverse('ordemservico-detail', args=[os.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
