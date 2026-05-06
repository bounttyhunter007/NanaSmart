"""
Script de seed profissional e ultra-realista -- popula o banco com dados industriais completos.
Gera hierarquia de empresas, usuários com cargos reais, ativos detalhados e telemetria coerente.
"""
import os
import sys
import django
import random
import re
import argparse
import time
from datetime import timedelta, datetime
from decimal import Decimal
from django.utils import timezone

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
# Dados Industriais Realistas
# ---------------------------------------------------------------------------
FABRICANTES = [
    'WEG', 'Siemens', 'ABB', 'Schneider Electric', 'Caterpillar', 
    'Bosch Rexroth', 'Atlas Copco', 'SEW-Eurodrive', 'Danfoss', 
    'SKF', 'NSK', 'Parker Hannifin', 'Rockwell Automation'
]

CARGOS_GESTOR = [
    'Gerente de Manutenção', 'Supervisor de Manutenção', 
    'Coordenador de Confiabilidade', 'Engenheiro de Planejamento (PCM)'
]

CARGOS_TECNICO = [
    'Técnico Mecânico III', 'Técnico de Eletrotécnica', 
    'Mecânico de Manutenção Industrial', 'Eletricista de Manutenção',
    'Técnico em Instrumentação', 'Lubrificador Industrial'
]

TIPOS_EQUIP = [
    ('Motor Elétrico Trifásico', ['temperatura', 'vibracao', 'corrente'], 'WEG W22 Premium'),
    ('Bomba Centrífuga', ['pressao', 'vibracao', 'temperatura'], 'KSB MegaCPK'),
    ('Compressor de Parafuso', ['pressao', 'temperatura', 'vibracao'], 'Atlas Copco GA37'),
    ('Painel de Comando (CCM)', ['corrente', 'temperatura'], 'Siemens Sivacon S8'),
    ('Redutor de Velocidade', ['vibracao', 'temperatura'], 'SEW Eurodrive X-Series'),
    ('Transformador de Potência', ['temperatura', 'corrente'], 'ABB Trafo 500kVA'),
    ('Prensa Hidráulica', ['pressao', 'vibracao'], 'Schuler P-1000'),
]

SETORES = [
    'Linha de Produção A', 'Linha de Produção B', 'Utilidades (Caldeiras)', 
    'Tratamento de Efluentes (ETA)', 'Usinagem de Precisão', 
    'Almoxarifado Central', 'Expedição e Logística', 'Subestação Elétrica'
]

CONFIG_SENSORES = {
    'temperatura': ('°C', 35.0, 85.0),
    'vibracao': ('mm/s RMS', 0.2, 7.0),
    'pressao': ('bar', 2.0, 12.0),
    'corrente': ('A', 10.0, 150.0),
}

ACOES_MANUTENCAO = {
    'preventiva': [
        "Substituição preventiva de rolamentos (Padrão SKF/NSK).",
        "Troca de óleo lubrificante ISO VG 68 e limpeza de filtros.",
        "Reaperto de conexões elétricas e inspeção termográfica.",
        "Calibração de instrumentação e sensores de campo.",
        "Limpeza técnica e desobstrução de dutos de ventilação.",
        "Alinhamento a laser de eixos e ajuste de acoplamentos.",
    ],
    'corretiva': [
        "Reparo emergencial em bobinagem de motor queimado.",
        "Substituição de selo mecânico por vazamento excessivo.",
        "Troca de contatora de potência após falha de acionamento.",
        "Correção de desbalanceamento em hélice de exaustor.",
        "Reparo em linha de pressão após rompimento de mangueira.",
        "Substituição de sensor de temperatura com leitura intermitente.",
    ]
}

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------
_usernames_usados = set()

def gerar_credenciais_reais(nome, empresa_nome):
    """Gera username e email profissionais baseados no nome real."""
    nome_limpo = re.sub(r'[^\w\s]', '', nome.lower())
    partes = nome_limpo.split()
    if len(partes) >= 2:
        username = f"{partes[0]}.{partes[-1]}"
        email = f"{partes[0]}.{partes[-1]}@{empresa_nome.lower().replace(' ', '').split(',')[0]}.com.br"
    else:
        username = partes[0]
        email = f"{partes[0]}@{empresa_nome.lower().replace(' ', '').split(',')[0]}.com.br"
    
    base = username
    contador = 1
    while username in _usernames_usados or Usuario.objects.filter(username=username).exists():
        username = f"{base}{contador}"
        contador += 1
    
    _usernames_usados.add(username)
    return username, email

def log_progresso(etapa, atual, total):
    percentual = (atual / total) * 100
    sys.stdout.write(f"\r[{etapa}] Progresso: {percentual:.1f}% ({atual}/{total})")
    sys.stdout.flush()
    if atual == total: print()

# ---------------------------------------------------------------------------
# Logica Principal
# ---------------------------------------------------------------------------
def run_seed(num_empresas, equip_por_empresa):
    start_total = time.time()
    print(f"\n[START] Iniciando Seed Industrial: {num_empresas} empresas, ~{equip_por_empresa} ativos/empresa.")
    
    # 1. Limpeza
    t_start = time.time()
    print("\n[CLEAN] Limpando banco de dados...")
    models_to_clear = [Alerta, HistoricoManutencao, OrdemServico, Telemetria, Sensor, PlanoManutencao, EquipamentoLocalizacao, Equipamento, Empresa]
    for model in models_to_clear:
        model.objects.all().delete()
    Usuario.objects.filter(is_superuser=False).delete()
    _usernames_usados.clear()
    print(f"OK (Duracao: {time.time() - t_start:.2f}s)")

    # 2. Admin
    print("\n[ADMIN] Configurando acesso administrativo...")
    t_start = time.time()
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(username='admin', email='suporte@bughunter.com', password='admin', tipo_usuario='admin')
    print(f"OK (Duracao: {time.time() - t_start:.2f}s)")

    # 3. Empresas e Usuarios
    t_start = time.time()
    empresas = []
    for i in range(num_empresas):
        emp_nome = fake.company()
        emp = Empresa.objects.create(
            nome=emp_nome, cnpj=fake.cnpj(), email=fake.company_email(), 
            telefone=fake.phone_number(), endereco=fake.address()
        )
        empresas.append(emp)
        
        # Gestor
        g_nome = fake.name()
        u_name, u_email = gerar_credenciais_reais(g_nome, emp_nome)
        Usuario.objects.create_user(
            username=u_name, email=u_email, password='123', 
            empresa=emp, tipo_usuario='gestor', 
            first_name=g_nome.split()[0], last_name=" ".join(g_nome.split()[1:]),
            cargo=random.choice(CARGOS_GESTOR)
        )
        
        # Técnicos
        for _ in range(random.randint(3, 5)):
            t_nome = fake.name()
            u_name, u_email = gerar_credenciais_reais(t_nome, emp_nome)
            Usuario.objects.create_user(
                username=u_name, email=u_email, password='123', 
                empresa=emp, tipo_usuario='tecnico', 
                first_name=t_nome.split()[0], last_name=" ".join(t_nome.split()[1:]),
                cargo=random.choice(CARGOS_TECNICO)
            )
        log_progresso("Empresas", i + 1, num_empresas)
    print(f"OK (Duracao: {time.time() - t_start:.2f}s)")

    # 4. Equipamentos, Planos e Sensores
    t_start = time.time()
    print("\n[ASSETS] Gerando Ativos e Instrumentação...")
    now = timezone.now()
    inicio_historico = now - timedelta(days=120) # Aumentado para 4 meses
    todos_sensores = []
    total_equip = num_empresas * equip_por_empresa
    count = 0
    
    for emp in empresas:
        for _ in range(equip_por_empresa):
            tipo_nome, sensores_list, modelo_base = random.choice(TIPOS_EQUIP)
            status = random.choices(['ativo', 'manutencao', 'inativo'], weights=[0.85, 0.10, 0.05])[0]
            
            eq = Equipamento.objects.create(
                empresa=emp, nome=f"{tipo_nome} {fake.bothify(text='##-??')}", tipo=tipo_nome,
                fabricante=random.choice(FABRICANTES), modelo=f"{modelo_base} {fake.bothify(text='-####')}",
                numero_serie=fake.unique.bothify(text="SN-####-####").upper(),
                data_instalacao=fake.date_between(start_date='-3y', end_date='-6m'),
                status=status, horimetro=random.uniform(100, 8000)
            )
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=random.choice(SETORES))

            # Planos
            PlanoManutencao.objects.create(
                equipamento=eq, nome_servico="Revisão Periódica Nível 1", 
                intervalo_horas=random.choice([500.0, 1000.0]), prioridade='medio'
            )
            if random.random() > 0.6:
                PlanoManutencao.objects.create(
                    equipamento=eq, nome_servico="Inspeção Geral de Segurança (NR-12/NR-13)", 
                    intervalo_horas=4000.0, prioridade='critico'
                )

            # Sensores
            for s_tipo in sensores_list:
                unidade, min_v, max_v = CONFIG_SENSORES.get(s_tipo, ('un', 0, 100))
                sensor = Sensor.objects.create(equipamento=eq, tipo_sensor=s_tipo, unidade_medida=unidade)
                todos_sensores.append((sensor, min_v, max_v))
            
            count += 1
            log_progresso("Ativos", count, total_equip)
    print(f"OK (Duracao: {time.time() - t_start:.2f}s)")

    # 5. Telemetria (Simulação Coerente)
    t_start = time.time()
    print("\n[TELEMETRY] Gerando histórico (120 dias com tendências)...")
    leituras_bulk = []
    for sensor, min_v, max_v in todos_sensores:
        base_val = random.uniform(min_v, (min_v + max_v) / 2)
        trend = random.uniform(-0.01, 0.05) # Pequena tendência de desgaste
        
        for h in range(120 * 24): # Horário (1 leitura por hora durante 120 dias)
            ponto = inicio_historico + timedelta(hours=h)
            fluctuacao = random.uniform(-0.5, 0.5)
            val = base_val + (h * trend) + fluctuacao
            
            # Garantir limites
            val = max(min_v * 0.8, min(val, max_v * 1.5))
            
            leituras_bulk.append(Telemetria(sensor=sensor, valor=round(val, 2), data_hora=ponto))
            
            if len(leituras_bulk) > 5000:
                Telemetria.objects.bulk_create(leituras_bulk)
                leituras_bulk = []
                
    if leituras_bulk: Telemetria.objects.bulk_create(leituras_bulk)
    print(f"OK: {Telemetria.objects.count()} registros de telemetria. (Duracao: {time.time() - t_start:.2f}s)")

    # 6. Ordens de Serviço e Histórico
    t_start = time.time()
    print("\n[MAINTENANCE] Criando Ordens de Serviço e Alertas...")
    equips = Equipamento.objects.all()
    tecnicos = Usuario.objects.filter(tipo_usuario='tecnico')
    
    for idx, eq in enumerate(equips):
        tecnicos_empresa = list(tecnicos.filter(empresa=eq.empresa))
        
        # Histórico de OS Concluídas
        for _ in range(random.randint(2, 6)): # Mais OS por conta do período maior
            data_os = now - timedelta(days=random.randint(5, 115))
            tipo_os = random.choice(['preventiva', 'corretiva'])
            os_obj = OrdemServico.objects.create(
                equipamento=eq, responsavel=random.choice(tecnicos_empresa) if tecnicos_empresa else None,
                titulo=f"{tipo_os.capitalize()} - {eq.nome}", 
                descricao=f"Atendimento de rotina para {eq.tipo}.",
                status='concluida', tipo_os=tipo_os,
                prioridade=random.choice(['baixo', 'medio', 'critico']),
                data_abertura=data_os
            )
            
            HistoricoManutencao.objects.create(
                ordem_servico=os_obj, data_execucao=data_os.date(),
                descricao_servico=random.choice(ACOES_MANUTENCAO[tipo_os]),
                custo_pecas=Decimal(random.uniform(100, 2500)),
                custo_mao_de_obra=Decimal(random.uniform(200, 1500))
            )

        # Alertas e OS em aberto
        if eq.status == 'manutencao':
            os_ativa = OrdemServico.objects.create(
                equipamento=eq, responsavel=random.choice(tecnicos_empresa) if tecnicos_empresa else None,
                titulo=f"Manutenção em Andamento - {eq.nome}",
                descricao="Equipamento parado para intervenção técnica.",
                status='em_andamento', tipo_os='corretiva', prioridade='critico',
                data_abertura=now - timedelta(hours=random.randint(1, 12))
            )
            Alerta.objects.create(
                equipamento=eq, tipo_alerta="Parada Não Programada", nivel='critico',
                descricao="Alerta gerado automaticamente por interrupção de operação.",
                status='ativo'
            )
        
        elif random.random() > 0.85: # Alertas esporádicos em equipamentos ativos
            Alerta.objects.create(
                equipamento=eq, tipo_alerta="Anomalia de Vibração", nivel='medio',
                descricao="Nível de vibração RMS acima da zona A (ISO 10816).",
                status='ativo'
            )

        log_progresso("Finalizando", idx + 1, equips.count())
    print(f"OK (Duracao: {time.time() - t_start:.2f}s)")

    total_time = time.time() - start_total
    print(f"\n[DONE] Banco de dados populado com sucesso em {total_time:.2f}s!")
    print(f"Resumo: {Usuario.objects.count()} usuários, {Equipamento.objects.count()} ativos.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed industrial para o sistema BugHunter.')
    parser.add_argument('--empresas', type=int, default=2, help='Numero de empresas a criar')
    parser.add_argument('--equipamentos', type=int, default=10, help='Numero de equipamentos por empresa')
    args = parser.parse_args()
    
    try:
        run_seed(args.empresas, args.equipamentos)
    except Exception as e:
        print(f"\n[ERROR] Falha crítica no seed: {e}")
        import traceback
        traceback.print_exc()
