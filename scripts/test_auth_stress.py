import os
import sys
import django

# Setup Django first
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.test.utils import override_settings
from accounts.models import Empresa, Usuario
from rest_framework.test import APIClient
from rest_framework import status

@override_settings(ALLOWED_HOSTS=['testserver'])
def run_auth_tests():
    print("\n" + "="*50)
    print("INICIANDO TESTES DE ESTRESSE DE AUTENTICACAO")
    print("="*50)

    client = APIClient()
    
    # 1. Setup Data
    print("\n[1/5] Preparando dados de teste...")
    Empresa.objects.all().delete()
    Usuario.objects.all().delete()
    
    empresa = Empresa.objects.create(
        nome='Test Industry', cnpj='00.000.000/0001-00', email='test@test.com'
    )
    user = Usuario.objects.create_user(
        username='auth_user', password='password123',
        email='auth@test.com', empresa=empresa
    )
    print("Dados preparados: Usuario 'auth_user' criado.")

    # 2. Login Flow
    print("\n[2/5] Testando Fluxo de Login...")
    resp = client.post('/api/auth/token/', {
        'username': 'auth_user', 'password': 'password123'
    })
    if resp.status_code == 200:
        print("[OK] Login realizado com sucesso.")
        access_token = resp.data['access']
        refresh_token = resp.data['refresh']
    else:
        print(f"[ERRO] Falha no login: {resp.status_code}")
        print(resp.data)
        return

    # 3. Refresh and Blacklist (Rotation)
    print("\n[3/5] Testando Rotacao e Blacklist...")
    # Primeiro refresh
    resp_ref = client.post('/api/auth/token/refresh/', {'refresh': refresh_token})
    if resp_ref.status_code == 200:
        print("[OK] Token renovado com sucesso.")
        new_refresh = resp_ref.data.get('refresh')
        if new_refresh and new_refresh != refresh_token:
            print("[OK] Rotacao de Refresh Token: OK (Novo token gerado)")
        else:
            print("[AVISO] Aviso: Rotacao de Refresh Token nao detectada ou desativada.")
        
        # Testar se o antigo foi para a blacklist
        resp_old = client.post('/api/auth/token/refresh/', {'refresh': refresh_token})
        if resp_old.status_code == 401:
            print("[OK] Blacklist: OK (Token antigo invalidado apos rotacao)")
        else:
            print(f"[ERRO] Falha: Token antigo ainda e valido! Status: {resp_old.status_code}")
    else:
        print(f"[ERRO] Falha na renovacao: {resp_ref.status_code}")

    # 4. /me Endpoint
    print("\n[4/5] Testando endpoint /api/auth/me/...")
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    resp_me = client.get('/api/auth/me/')
    if resp_me.status_code == 200 and resp_me.data['username'] == 'auth_user':
        print("[OK] Endpoint /me retornou dados corretos.")
    else:
        print(f"[ERRO] Falha no endpoint /me: {resp_me.status_code}")

    # 5. Password Change
    print("\n[5/5] Testando Troca de Senha e Invalidacao...")
    resp_pwd = client.post('/api/auth/change-password/', {
        'senha_atual': 'password123',
        'nova_senha': 'new_password_456',
        'confirmar_nova_senha': 'new_password_456'
    })
    if resp_pwd.status_code == 200:
        print("[OK] Senha alterada com sucesso.")
        # Testar login com senha antiga
        client.credentials() # clear
        resp_old_login = client.post('/api/auth/token/', {
            'username': 'auth_user', 'password': 'password123'
        })
        if resp_old_login.status_code == 401:
            print("[OK] Invalidacao da senha antiga: OK")
        else:
            print("[ERRO] Falha: Senha antiga ainda permite login!")
            
        # Testar login com senha nova
        resp_new_login = client.post('/api/auth/token/', {
            'username': 'auth_user', 'password': 'new_password_456'
        })
        if resp_new_login.status_code == 200:
            print("[OK] Login com nova senha: OK")
        else:
            print(f"[ERRO] Falha no login com nova senha: {resp_new_login.status_code}")
    else:
        print(f"[ERRO] Falha na troca de senha: {resp_pwd.status_code}")
        print(resp_pwd.data)

    print("\n" + "="*50)
    print("TESTES FINALIZADOS")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_auth_tests()
