from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Empresa, Usuario

class AuthTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome="Empresa Teste",
            cnpj="12.345.678/0001-99",
            email="teste@empresa.com"
        )
        self.user_password = "password123"
        self.user = Usuario.objects.create_user(
            username="testuser",
            password=self.user_password,
            empresa=self.empresa,
            tipo_usuario="gestor"
        )
        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')

    def test_login_success(self):
        """Testa se o usuário consegue obter o token JWT com credenciais válidas."""
        data = {
            "username": "testuser",
            "password": self.user_password
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_password(self):
        """Testa se o login falha com senha incorreta."""
        data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Testa se o token de acesso pode ser renovado usando o refresh token."""
        login_data = {
            "username": "testuser",
            "password": self.user_password
        }
        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.data['refresh']

        refresh_data = {"refresh": refresh_token}
        response = self.client.post(self.refresh_url, refresh_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

class UserProfileTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Alpha", cnpj="111", email="a@a.com")
        self.user = Usuario.objects.create_user(
            username="admin_test", password="123", tipo_usuario="admin"
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('usuario-list')

    def test_create_user_admin(self):
        """Testa se um Admin pode criar novos usuários."""
        data = {
            "username": "novo_tecnico",
            "password": "password123",
            "email": "tec@teste.com",
            "tipo_usuario": "tecnico",
            "empresa": self.empresa.id
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Usuario.objects.filter(username="novo_tecnico").count(), 1)
