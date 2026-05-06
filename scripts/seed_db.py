"""
Script de seed robusto e inteligente -- popula o banco com dados realistas, escalaveis e completos.
Uso:
    python scripts/seed_db.py --empresas 3 --equipamentos 20
"""
import os
import sys
import django
import random
import re
import argparse
from datetime import timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command

# Configuracao do Ambiente Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from faker import Faker
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao, PlanoManutencao
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico, HistoricoManutencao
from alertas.models import Alerta

fake = Faker('pt_BR')

# ---------------------------------------------------------------------------
# Configuracoes e Dados Fixos
# ---------------------------------------------------------------------------
FABRICANTES = ['WEG', 'Siemens', 'ABB', 'Schneider Electric', 'Caterpillar', 'Bosch Rexroth', 'Atlas Copco', 'SEW-Eurodrive', 'Danfoss']
TIPOS_EQUIP = [
    ('Motor Eletrico',     ['temperatura', 'vibracao', 'corrente']),
    ('Bomba Hidraulica',   ['pressao', 'vibracao', 'temperatura']),
    ('Compressor',         ['pressao', 'temperatura', 'vibracao']),
    ('Painel Eletrico',    ['corrente', 'temperatura']),
    ('Prensa Hidraulica',  ['vibracao', 'pressao']),
    ('Inversor de Frequencia', ['corrente', 'temperatura']),
    ('Redutor de Velocidade',  ['vibracao', 'temperatura']),
]
SETORES = ['Producao A', 'Producao B', 'Utilidades', 'Usinagem', 'Manutencao', 'Almoxarifado', 'Expedicao']
CONFIG_SENSORES = {
    'temperatura': ('C',   35.0, 75.0),
    'vibracao':    ('mm/s',  0.2,  5.5),
    'pressao':     ('bar',   1.5,  10.0),
    'corrente':    ('A',     5.0, 50.0),
    'umidade':     ('%',    30.0, 80.0),
}

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------
_usernames_usados = set()

def gerar_username_unico(nome):
    nome = re.sub(r'[^\w\s]', '', nome.lower())
    partes = nome.split()
    base = f"{partes[0]}.{partes[1]}" if len(partes) >= 2 else partes[0]
    username = base
    contador = 1
    while username in _usernames_usados or Usuario.objects.filter(username=username).exists():
        username = f"{base}{contador}"
        contador += 1
    _usernames_usados.add(username)
    return username

def log_progresso(etapa, atual, total):
    percentual = (atual / total) * 100
    sys.stdout.write(f"\r[{etapa}] Progresso: {percentual:.1f}% ({atual}/{total})")
    sys.stdout.flush()
    if atual == total: print()

# ---------------------------------------------------------------------------
# Logica Principal
# ---------------------------------------------------------------------------
def run_seed(num_empresas, equip_por_empresa):
    print(f"\n[START] Iniciando Seed Inteligente: {num_empresas} empresas, ~{equip_por_empresa} ativos/empresa.")
    
    # 1. Limpeza
    print("\n[CLEAN] Limpando banco de dados (preservando admins)...")
    models_to_clear = [Alerta, HistoricoManutencao, OrdemServico, Telemetria, Sensor, PlanoManutencao, EquipamentoLocalizacao, Equipamento, Empresa]
    for model in models_to_clear:
        model.objects.all().delete()
    Usuario.objects.filter(is_superuser=False).delete()
    _usernames_usados.clear()

    # 2. Admin
    print("Garantindo superusuario admin...")
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(username='admin', email='admin@admin.com', password='admin123', tipo_usuario='admin')

    # 3. Empresas e Usuarios
    print("Criando empresas e hierarquia de usuarios...")
    empresas = []
    for i in range(num_empresas):
        emp = Empresa.objects.create(nome=fake.company(), cnpj=fake.cnpj(), email=fake.company_email(), telefone=fake.phone_number(), endereco=fake.address())
        empresas.append(emp)
        
        # 1 Gestor
        gestor_nome = fake.name()
        Usuario.objects.create_user(username=gerar_username_unico(gestor_nome), email=fake.email(), password='123', empresa=emp, tipo_usuario='gestor', first_name=gestor_nome.split()[0], cargo='Gerente Industrial')
        
        # 4 Tecnicos
        for _ in range(4):
            tec_nome = fake.name()
            Usuario.objects.create_user(username=gerar_username_unico(tec_nome), email=fake.email(), password='123', empresa=emp, tipo_usuario='tecnico', first_name=tec_nome.split()[0], cargo='Tecnico de Manutencao')
        log_progresso("Empresas", i + 1, num_empresas)

    # 4. Equipamentos, Planos e Sensores
    print("\nGerando Ativos, Planos de Manutencao e Sensores...")
    now = timezone.now()
    inicio_historico = now - timedelta(days=60)
    todos_sensores = []
    count = 0
    total_equip = num_empresas * equip_por_empresa
    
    for emp in empresas:
        for _ in range(equip_por_empresa):
            tipo_nome, sensores_list = random.choice(TIPOS_EQUIP)
            status = random.choices(['ativo', 'manutencao', 'inativo'], weights=[0.8, 0.15, 0.05])[0]
            
            eq = Equipamento.objects.create(
                empresa=emp, nome=f'{tipo_nome} {fake.bothify(text="##-??")}', tipo=tipo_nome,
                fabricante=random.choice(FABRICANTES), modelo=fake.bothify(text="MOD-####"),
                numero_serie=fake.unique.bothify(text="SN-####-####").upper(),
                data_instalacao=fake.date_between(start_date='-2y', end_date='-6m'),
                status=status, horimetro=random.uniform(500, 5000)
            )
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=random.choice(SETORES))

            # Cria 1-2 Planos de Manutencao por Horimetro
            PlanoManutencao.objects.create(
                equipamento=eq, nome_servico="Troca de Oleo / Filtros", 
                intervalo_horas=random.choice([250.0, 500.0]), prioridade='medio'
            )
            if random.random() > 0.7:
                PlanoManutencao.objects.create(
                    equipamento=eq, nome_servico="Revisao Geral do Sistema", 
                    intervalo_horas=2000.0, prioridade='critico'
                )

            # Cria Sensores
            for s_tipo in sensores_list:
                unidade, min_v, max_v = CONFIG_SENSORES.get(s_tipo, ('un', 0, 100))
                sensor = Sensor.objects.create(equipamento=eq, tipo_sensor=s_tipo, unidade_medida=unidade)
                todos_sensores.append((sensor, min_v, max_v))
            
            count += 1
            log_progresso("Equipamentos", count, total_equip)

    # 5. Telemetria (Bulk para performance)
    print("\nGerando historico de telemetria (60 dias)...")
    leituras_bulk = []
    for sensor, min_v, max_v in todos_sensores:
        for d in range(60):
            ponto = inicio_historico + timedelta(days=d)
            val = random.uniform(min_v, max_v)
            if random.random() > 0.95: val *= 1.3 # Injetar algumas anomalias
            leituras_bulk.append(Telemetria(sensor=sensor, valor=round(val, 2), data_hora=ponto))
        if len(leituras_bulk) > 5000:
            Telemetria.objects.bulk_create(leituras_bulk)
            leituras_bulk = []
    if leituras_bulk: Telemetria.objects.bulk_create(leituras_bulk)
    print(f"OK: {Telemetria.objects.count()} leituras geradas.")

    # 6. Ordens de Servico e Alertas
    print("\nCriando Ordens de Servico e Alertas historicos...")
    tecnicos = list(Usuario.objects.filter(tipo_usuario='tecnico'))
    equips = Equipamento.objects.all()
    total_eq = equips.count()
    
    for idx, eq in enumerate(equips):
        if random.random() > 0.5: # 50% dos equips têm histórico de OS
            for _ in range(random.randint(1, 3)):
                abertura = now - timedelta(days=random.randint(5, 55))
                os_obj = OrdemServico.objects.create(
                    equipamento=eq, responsavel=random.choice([t for t in tecnicos if t.empresa == eq.empresa] or [None]),
                    titulo=f"Manutencao em {eq.nome}", descricao=fake.sentence(),
                    status='concluida', tipo_os=random.choice(['corretiva', 'preventiva']),
                    prioridade=random.choice(['baixo', 'medio', 'critico']), data_abertura=abertura
                )
                HistoricoManutencao.objects.create(
                    ordem_servico=os_obj, data_execucao=abertura.date(),
                    descricao_servico="Servico executado com sucesso.",
                    custo_pecas=Decimal(random.uniform(50, 500)), custo_mao_de_obra=Decimal(random.uniform(100, 300))
                )
        
        # Alertas Ativos
        if random.random() > 0.8:
            Alerta.objects.create(
                equipamento=eq, tipo_alerta="Sobrecarga Termica", nivel=random.choice(['medio', 'critico']),
                descricao="Temperatura acima do limite operacional.", status='ativo'
            )
        log_progresso("Finalizando", idx + 1, total_eq)

    print(f"\n[DONE] Seed finalizado com sucesso! Explore o Dashboard e a API.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed robusto para o sistema de manutencao.')
    parser.add_argument('--empresas', type=int, default=3, help='Numero de empresas a criar')
    parser.add_argument('--equipamentos', type=int, default=15, help='Numero de equipamentos por empresa')
    args = parser.parse_args()
    
    try:
        run_seed(args.empresas, args.equipamentos)
    except Exception as e:
        print(f"\n[ERROR] Erro durante o seed: {e}")
