import os
import sys
import django
import time
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from ativos.models import Equipamento
from telemetria.models import Sensor, Telemetria
from accounts.models import Empresa

def run_stress_test():
    print("Iniciando Teste de Carga de Telemetria e Alertas...")
    
    # 1. Setup
    empresa, _ = Empresa.objects.get_or_create(nome='StressCorp', cnpj='99.999.999/0001-99', email='stress@corp.com')
    equipamento, _ = Equipamento.objects.get_or_create(
        empresa=empresa, nome='Motor Stress', tipo='Motor Elétrico', numero_serie='STRESS-001'
    )
    sensor, _ = Sensor.objects.get_or_create(
        equipamento=equipamento, tipo_sensor='temperatura', unidade_medida='C'
    )
    
    # Limpa leituras antigas para este sensor
    Telemetria.objects.filter(sensor=sensor).delete()
    
    # Vamos inserir 500 leituras concorrentes
    # Destas, algumas passarão o limite (ex: 85C, 100C) para acionar alertas.
    # O limite do Motor Elétrico para Temperatura costuma ser ao redor de 80-100 na regra de negócio.
    # Vou enviar valores flutuando entre 50 e 110.
    import random
    
    def insert_reading(val):
        Telemetria.objects.create(sensor=sensor, valor=val)
        
    valores = [random.uniform(50, 110) for _ in range(500)]
    
    start_time = time.time()
    
    # Executa as inserções com 10 threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(insert_reading, valores)
        
    end_time = time.time()
    
    print(f"500 inserções completadas em {end_time - start_time:.2f} segundos.")
    
    from alertas.models import Alerta
    alertas_gerados = Alerta.objects.filter(equipamento=equipamento).count()
    print(f"Alertas gerados durante o stress test: {alertas_gerados}")
    
    if alertas_gerados > 0:
         alerta_atual = Alerta.objects.filter(equipamento=equipamento, status='ativo').first()
         print(f"Alerta atual ativo: {alerta_atual.nivel if alerta_atual else 'Nenhum'}")

if __name__ == '__main__':
    run_stress_test()
