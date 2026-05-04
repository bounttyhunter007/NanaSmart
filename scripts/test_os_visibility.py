import os
import sys
import django

# Setup Django first
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.test.utils import override_settings
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico
from rest_framework.test import APIClient

@override_settings(ALLOWED_HOSTS=['testserver'])
def run_visibility_tests():
    print("\n" + "="*50)
    print("TESTANDO VISIBILIDADE E AUTOMAÇÃO DE O.S.")
    print("="*50)

    # 1. Setup
    print("\n[1/5] Preparando cenário...")
    Empresa.objects.all().delete()
    Usuario.objects.all().delete()
    
    empresa = Empresa.objects.create(nome='TechCorp', cnpj='11.111.111/0001-11', email='tech@corp.com')
    gestor = Usuario.objects.create_user(username='gestor1', password='pwd', tipo_usuario='gestor', empresa=empresa)
    tech_a = Usuario.objects.create_user(username='techa', password='pwd', tipo_usuario='tecnico', empresa=empresa)
    tech_b = Usuario.objects.create_user(username='techb', password='pwd', tipo_usuario='tecnico', empresa=empresa)
    
    equip = Equipamento.objects.create(nome='Motor A', tipo='Motor Elétrico', numero_serie='SN-A', empresa=empresa)
    sensor = Sensor.objects.create(equipamento=equip, tipo_sensor='temperatura', unidade_medida='C', ativo=True)
    
    print("Cenário preparado: Empresa, Gestor e 2 Técnicos (A e B).")

    # 2. Trigger Auto OS
    print("\n[2/5] Enviando Telemetria CRÍTICA (110°C)...")
    # Limite padrão para Motor Elétrico / Temperatura costuma ser 80 ou similar (config_alertas.py)
    # Vamos garantir que 110 é crítico.
    Telemetria.objects.create(sensor=sensor, valor=110.0)
    
    os_gerada = OrdemServico.objects.filter(equipamento=equip).first()
    if os_gerada and os_gerada.prioridade == 'urgente':
        print(f"[OK] O.S. Gerada Automaticamente: ID #{os_gerada.id} - {os_gerada.titulo}")
    else:
        print("[ERRO] O.S. automática não foi gerada ou não é urgente.")
        return

    # 3. Visibilidade Inicial
    print("\n[3/5] Verificando visibilidade inicial para Técnicos...")
    client_a = APIClient()
    client_a.force_authenticate(user=tech_a)
    resp_a = client_a.get('/api/ordens-servico/')
    
    client_b = APIClient()
    client_b.force_authenticate(user=tech_b)
    resp_b = client_b.get('/api/ordens-servico/')
    
    if len(resp_a.data) == 1 and len(resp_b.data) == 1:
        print("[OK] Ambos os técnicos veem a O.S. não atribuída.")
    else:
        print(f"[ERRO] Visibilidade incorreta. A: {len(resp_a.data)}, B: {len(resp_b.data)}")

    # 4. Atribuição (Picking)
    print("\n[4/5] Técnico A assume a O.S. #1...")
    resp_pick = client_a.patch(f'/api/ordens-servico/{os_gerada.id}/', {'responsavel': tech_a.id, 'status': 'andamento'})
    if resp_pick.status_code == 200:
        print("[OK] Técnico A assumiu a O.S. com sucesso.")
    else:
        print(f"[ERRO] Técnico A falhou em assumir: {resp_pick.status_code} {resp_pick.data}")

    # 5. Visibilidade Restrita
    print("\n[5/5] Verificando visibilidade após atribuição...")
    resp_a_pos = client_a.get('/api/ordens-servico/')
    resp_b_pos = client_b.get('/api/ordens-servico/')
    
    if len(resp_a_pos.data) == 1 and len(resp_b_pos.data) == 0:
        print("[OK] Visibilidade Restrita FUNCIONANDO!")
        print("     - Técnico A ainda vê sua O.S.")
        print("     - Técnico B não vê mais a O.S. alheia.")
    else:
        print(f"[ERRO] Falha na restrição. A vê: {len(resp_a_pos.data)}, B vê: {len(resp_b_pos.data)}")

    # 6. Teste de Edição proibida
    print("\n[EXTRA] Técnico B tenta editar O.S. do Técnico A...")
    resp_hack = client_b.patch(f'/api/ordens-servico/{os_gerada.id}/', {'status': 'concluida'})
    if resp_hack.status_code == 404: # 404 porque o queryset nem retorna o objeto para ele
        print("[OK] Técnico B recebeu 404 (Objeto oculto pelo queryset).")
    elif resp_hack.status_code == 403:
        print("[OK] Técnico B recebeu 403 Forbidden.")
    else:
        print(f"[ERRO] Técnico B conseguiu interagir ou recebeu erro inesperado: {resp_hack.status_code}")

    print("\n" + "="*50)
    print("TESTES FINALIZADOS")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_visibility_tests()
