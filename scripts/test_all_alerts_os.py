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
from alertas.models import Alerta

def run_all_alerts_test():
    print("\n" + "="*50)
    print("TESTANDO O.S. PARA TODOS OS NÍVEIS DE ALERTA")
    print("="*50)

    # 1. Setup
    Empresa.objects.all().delete()
    Usuario.objects.all().delete()
    empresa = Empresa.objects.create(nome='TestCorp', cnpj='22.222.222/0001-22')
    equip = Equipamento.objects.create(nome='Motor Teste', tipo='Motor Elétrico', numero_serie='SN-TEST', empresa=empresa)
    sensor = Sensor.objects.create(equipamento=equip, tipo_sensor='temperatura', unidade_medida='C', ativo=True)

    # 2. Teste Nível BAIXO (75% de 80 = 60)
    # Supondo limite 80 para Motor Elétrico / Temperatura
    # Alerta Baixo >= 70% (56)
    print("\n[1/3] Enviando valor para Alerta BAIXO (60°C)...")
    Telemetria.objects.create(sensor=sensor, valor=60.0)
    
    os_baixo = OrdemServico.objects.filter(equipamento=equip).first()
    if os_baixo and os_baixo.prioridade == 'baixo':
        print(f"[OK] O.S. de Prioridade BAIXO criada para Alerta Baixo.")
    else:
        print(f"[ERRO] O.S. não criada ou prioridade errada: {os_baixo.prioridade if os_baixo else 'Nula'}")

    # 3. Teste Nível MÉDIO (Escalada)
    # Alerta Médio >= 85% de 85 = 72.25
    print("\n[2/3] Escalando para Alerta MÉDIO (75°C)...")
    Telemetria.objects.create(sensor=sensor, valor=75.0)
    
    os_atualizada = OrdemServico.objects.get(id=os_baixo.id)
    if os_atualizada.prioridade == 'medio':
        print(f"[OK] O.S. Escalada para Prioridade MÉDIO com sucesso.")
    else:
        print(f"[ERRO] Falha na escalada de prioridade: {os_atualizada.prioridade}")

    # 4. Teste Nível CRÍTICO (Escalada Final)
    # Alerta Crítico >= 100% (80)
    print("\n[3/3] Escalando para Alerta CRÍTICO (90°C)...")
    Telemetria.objects.create(sensor=sensor, valor=90.0)
    
    os_final = OrdemServico.objects.get(id=os_baixo.id)
    if os_final.prioridade == 'critico':
        print(f"[OK] O.S. Escalada para Prioridade CRÍTICO com sucesso.")
    else:
        print(f"[ERRO] Falha na escalada final: {os_final.prioridade}")

    print("\n" + "="*50)
    print("TESTES FINALIZADOS")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_all_alerts_test()
