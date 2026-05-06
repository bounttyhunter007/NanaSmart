"""
Script de Teste de Carga (Stress Test) para Telemetria e Alertas.
Testa a capacidade do sistema de processar múltiplas leituras e gerar alertas/O.S. concorrentemente.
Uso:
    python scripts/stress_telemetry.py --leituras 1000 --threads 20
"""
import os
import sys
import django
import time
import argparse
import concurrent.futures
import random

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from ativos.models import Equipamento
from telemetria.models import Sensor, Telemetria
from accounts.models import Empresa
from alertas.models import Alerta

def run_stress_test(num_leituras, num_threads):
    print(f"\n[STRESS] Iniciando Stress Test: {num_leituras} leituras com {num_threads} threads...")
    
    # 1. Setup de um cenário controlado
    empresa, _ = Empresa.objects.get_or_create(
        nome='StressTest_Lab', cnpj='00.000.000/0001-00', email='lab@stress.com'
    )
    equipamento, _ = Equipamento.objects.get_or_create(
        empresa=empresa, nome='Turbina de Alta Carga', tipo='Motor Elétrico', numero_serie='STRESS-MAX-01'
    )
    # Garante um sensor de temperatura com limite conhecido
    sensor, _ = Sensor.objects.get_or_create(
        equipamento=equipamento, tipo_sensor='temperatura', 
        defaults={'unidade_medida': '°C', 'limite_alerta': 100.0}
    )
    
    # Limpa dados anteriores para precisão do teste
    Telemetria.objects.filter(sensor=sensor).delete()
    Alerta.objects.filter(equipamento=equipamento).delete()
    
    print(f"Alvo: {equipamento.nome} | Sensor: {sensor.tipo_sensor} (Limite: {sensor.limite_alerta}C)")

    def insert_reading(val):
        try:
            # O save() da Telemetria dispara signals que verificam alertas e criam O.S.
            Telemetria.objects.create(sensor=sensor, valor=val)
        except Exception as e:
            return f"Erro: {e}"
        return "OK"

    # Gera valores que flutuam em torno do limite para forçar disparos e escaladas
    valores = [random.uniform(70, 120) for _ in range(num_leituras)]
    
    start_time = time.time()
    
    # Execução Concorrente
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(insert_reading, valores))
        
    end_time = time.time()
    duration = end_time - start_time
    
    # 2. Resultados
    success = results.count("OK")
    errors = len(results) - success
    
    print(f"\n[FINISH] Teste Finalizado!")
    print(f"Tempo total: {duration:.2f}s")
    print(f"Taxa: {num_leituras / duration:.2f} leituras/segundo")
    print(f"Sucessos: {success}")
    if errors > 0: print(f"Erros: {errors}")

    # Verifica o estado final do sistema
    alerta_final = Alerta.objects.filter(equipamento=equipamento, status='ativo').first()
    from manutencao.models import OrdemServico
    os_gerada = OrdemServico.objects.filter(equipamento=equipamento).first()

    print("\n--- Estado Final do Sistema ---")
    if alerta_final:
        print(f"Alerta Ativo: Nivel {alerta_final.nivel.upper()} (Valor final processado)")
    if os_gerada:
        print(f"O.S. Vinculada: #{os_gerada.id} | Prioridade: {os_gerada.prioridade.upper()}")
    
    print("-" * 30)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulador de carga para telemetria.')
    parser.add_argument('--leituras', type=int, default=100, help='Total de leituras para enviar')
    parser.add_argument('--threads', type=int, default=5, help='Número de threads concorrentes')
    args = parser.parse_args()
    
    run_stress_test(args.leituras, args.threads)
