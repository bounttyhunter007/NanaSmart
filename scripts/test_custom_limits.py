import os
import sys
import django

# Setup Django first
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import Empresa
from ativos.models import Equipamento
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico

def run_custom_limits_test():
    print("\n" + "="*50)
    print("TESTANDO LIMITES CUSTOMIZADOS POR EQUIPAMENTO")
    print("="*50)

    # 1. Setup
    Empresa.objects.all().delete()
    empresa = Empresa.objects.create(nome='LimitCorp', cnpj='44.444.444/0001-44')
    
    # Maquina 1: Motor Sensível (Limite 50.0)
    m1 = Equipamento.objects.create(nome='Motor Sensível', tipo='Motor Elétrico', numero_serie='SN-SENSE', empresa=empresa)
    s1 = Sensor.objects.create(equipamento=m1, tipo_sensor='temperatura', unidade_medida='°C', limite_alerta=50.0)
    
    # Maquina 2: Motor Robusto (Limite 100.0)
    m2 = Equipamento.objects.create(nome='Motor Robusto', tipo='Motor Elétrico', numero_serie='SN-ROBUST', empresa=empresa)
    s2 = Sensor.objects.create(equipamento=m2, tipo_sensor='temperatura', unidade_medida='°C', limite_alerta=100.0)

    # 2. Teste: Mesmo valor (85.0) enviado para ambos
    print(f"\n[1/2] Enviando 85°C para o Motor Sensível (Limite 50)...")
    Telemetria.objects.create(sensor=s1, valor=85.0)
    os1 = OrdemServico.objects.filter(equipamento=m1).first()
    if os1 and os1.prioridade == 'critico':
        print(f"[OK] Motor Sensível gerou O.S. CRÍTICO (85 > 50).")
    else:
        print(f"[ERRO] Falha no Motor Sensível.")

    print(f"\n[2/2] Enviando os mesmos 85°C para o Motor Robusto (Limite 100)...")
    Telemetria.objects.create(sensor=s2, valor=85.0)
    os2 = OrdemServico.objects.filter(equipamento=m2).first()
    # 85 de 100 = 85% -> Deve ser Médio
    if os2 and os2.prioridade == 'medio':
        print(f"[OK] Motor Robusto gerou O.S. MÉDIO (85% do limite 100).")
    else:
        print(f"[ERRO] Falha no Motor Robusto. Prioridade: {os2.prioridade if os2 else 'Nenhuma'}")

    print("\n" + "="*50)
    print("TESTES FINALIZADOS")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_custom_limits_test()
