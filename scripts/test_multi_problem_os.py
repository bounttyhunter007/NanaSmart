import os
import sys
import django

# Setup Django first
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico

def run_multi_problem_test():
    print("\n" + "="*50)
    print("TESTANDO O.S. MÚLTIPLAS PARA PROBLEMAS DIFERENTES")
    print("="*50)

    # 1. Setup
    Empresa.objects.all().delete()
    empresa = Empresa.objects.create(nome='MultiCorp', cnpj='33.333.333/0001-33')
    equip = Equipamento.objects.create(nome='Motor Combo', tipo='Motor Elétrico', numero_serie='SN-COMBO', empresa=empresa)
    
    s_temp = Sensor.objects.create(equipamento=equip, tipo_sensor='temperatura', unidade_medida='C', ativo=True)
    s_vibr = Sensor.objects.create(equipamento=equip, tipo_sensor='vibracao', unidade_medida='mm/s', ativo=True)

    # 2. Problema 1: Temperatura
    print("\n[1/3] Gerando Alerta de Temperatura...")
    Telemetria.objects.create(sensor=s_temp, valor=90.0)
    
    os_temp = OrdemServico.objects.filter(equipamento=equip, titulo__contains='Temperatura').first()
    if os_temp:
        print(f"[OK] O.S. de Temperatura criada: ID #{os_temp.id}")
    else:
        print("[ERRO] O.S. de Temperatura não encontrada.")

    # 3. Problema 2: Vibração (Deve gerar SEGUNDA O.S.)
    print("\n[2/3] Gerando Alerta de Vibração (Mesmo Equipamento)...")
    Telemetria.objects.create(sensor=s_vibr, valor=15.0)
    
    os_vibr = OrdemServico.objects.filter(equipamento=equip, titulo__contains='Vibração').first()
    if os_vibr and os_vibr.id != os_temp.id:
        print(f"[OK] SEGUNDA O.S. (Vibração) criada com sucesso: ID #{os_vibr.id}")
    else:
        print(f"[ERRO] Segunda O.S. não criada ou ID duplicado.")

    # 4. Repetição de Problema 1 (Deve apenas escalar)
    print("\n[3/3] Gerando novo Alerta de Temperatura (Mesmo Equipamento)...")
    # Já criamos um crítico antes, vamos apenas garantir que não cria uma terceira OS
    count_antes = OrdemServico.objects.count()
    Telemetria.objects.create(sensor=s_temp, valor=95.0)
    count_depois = OrdemServico.objects.count()
    
    if count_depois == count_antes:
        print("[OK] Deduplicação para o mesmo problema funcionando (Não criou 3ª O.S.).")
    else:
        print(f"[ERRO] Criou O.S. duplicada para o mesmo problema! Total: {count_depois}")

    print("\n" + "="*50)
    print("TESTES FINALIZADOS")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_multi_problem_test()
