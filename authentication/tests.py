from datetime import timedelta
from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Usuario
from app import settings as runtime_settings


class RuntimeDatabaseTests(SimpleTestCase):
    def test_base_existente_continua_postgresql_e_testes_tem_settings_proprios(self):
        self.assertEqual(runtime_settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(runtime_settings.DATABASES['default']['NAME'], 'manutencao')


class AuthenticationRecoveryTests(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='gestor', password='senha', tipo_usuario='gestor')

    def test_falha_no_banco_durante_login_retorna_json_503(self):
        with patch('django.contrib.auth.backends.ModelBackend.authenticate',
                   side_effect=OperationalError('Detalhe técnico do banco')), self.assertLogs('app.exceptions', 'ERROR'):
            response = self.client.post('/api/auth/login/', {'username': 'gestor', 'password': 'senha'}, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('banco de dados', response.json()['detail'])
        self.assertNotIn('Detalhe técnico', response.content.decode())

    def test_falha_no_banco_durante_refresh_nao_parece_credencial_invalida(self):
        refresh = str(RefreshToken.for_user(self.user))
        with patch('django.db.models.query.QuerySet.get', side_effect=OperationalError('Sem conexão')), \
                self.assertLogs('app.exceptions', 'ERROR'):
            response = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertIn('banco de dados', response.json()['detail'])
        recovered = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(recovered.status_code, 200)
        self.assertIn('access', recovered.data)

    def test_token_de_acesso_expirado_pode_renovar_sem_novo_login(self):
        refresh = RefreshToken.for_user(self.user)
        access = refresh.access_token
        access.set_exp(from_time=timezone.now() - timedelta(minutes=10), lifetime=timedelta(minutes=1))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.client.credentials()
        response = self.client.post('/api/auth/refresh/', {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)

    def test_credencial_incorreta_continua_401_json(self):
        response = self.client.post('/api/auth/login/', {'username': 'gestor', 'password': 'errada'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Content-Type'], 'application/json')
