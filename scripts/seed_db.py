"""
Script de seed profissional e ultra-realista -- popula o banco com dados industriais completos.
Gera hierarquia de empresas, usuários com cargos reais, ativos detalhados, telemetria coerente,
configurações de IA (Gemini PromptConfig), tendências de sensores (TrendConfig) e ordens de serviço.
"""
import os
import sys
import django
import random
import re
import argparse
import time
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

# Configuração do Ambiente Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from faker import Faker
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao, PlanoManutencao, TipoEquipamento
from ativos.services import aplicar_criticidade
from telemetria.models import Sensor, Telemetria, TrendConfig
from manutencao.models import OrdemServico, HistoricoManutencao
from manutencao.services import PrioridadeOSService
from alertas.models import Alerta
from gemini_api.models import PromptConfig
from gemini_api.prompt_builder import DEFAULTS as GEMINI_DEFAULTS

fake = Faker('pt_BR')

# ---------------------------------------------------------------------------
# Dados Industriais Realistas
# ---------------------------------------------------------------------------
CIDADES_ESTADOS = [
    ('Joinville', 'SC'),
    ('São Paulo', 'SP'),
    ('Caxias do Sul', 'RS'),
    ('Belo Horizonte', 'MG'),
    ('Curitiba', 'PR'),
    ('Campinas', 'SP'),
    ('Manaus', 'AM'),
    ('Contagem', 'MG'),
]

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
    (
        'Motor Elétrico Trifásico', 
        ['temperatura', 'vibracao', 'corrente'], 
        'WEG W22 Premium',
        'Motor trifásico industrial para acionamento de cargas pesadas com alta eficiência energética IE3.'
    ),
    (
        'Bomba Centrífuga', 
        ['pressao', 'vibracao', 'temperatura'], 
        'KSB MegaCPK',
        'Bomba química e industrial para fluidos agressivos e limpos com vedação por selo mecânico.'
    ),
    (
        'Compressor de Parafuso', 
        ['pressao', 'temperatura', 'vibracao'], 
        'Atlas Copco GA37',
        'Compressor rotativo de parafuso lubrificado para suprimento contínuo de ar comprimido industrial.'
    ),
    (
        'Painel de Comando (CCM)', 
        ['corrente', 'temperatura'], 
        'Siemens Sivacon S8',
        'Centro de controle de motores (CCM) modular para distribuição de energia e acionamento seguro.'
    ),
    (
        'Redutor de Velocidade', 
        ['vibracao', 'temperatura'], 
        'SEW Eurodrive X-Series',
        'Redutor de engrenagens helicoidais para acionamento de elevadores de carga e esteiras transportadoras.'
    ),
    (
        'Transformador de Potência', 
        ['temperatura', 'corrente'], 
        'ABB Trafo 500kVA',
        'Transformador a seco trifásico para subestações abrigadas de média tensão.'
    ),
    (
        'Prensa Hidráulica', 
        ['pressao', 'vibracao'], 
        'Schuler P-1000',
        'Prensa hidráulica de conformação metálica com sistema de automação e sensores de segurança.'
    ),
]

CRITICIDADE_TIPOS = {
    'Motor Elétrico Trifásico': ('B', 'Sugestão inicial para motor de acionamento industrial; validar conforme redundância e impacto da parada.'),
    'Bomba Centrífuga': ('A', 'Sugestão inicial para bomba de processo; validar conforme fluido, redundância e impacto ambiental.'),
    'Compressor de Parafuso': ('B', 'Sugestão inicial para compressor de utilidades; validar conforme redundância e impacto na produção.'),
    'Painel de Comando (CCM)': ('A', 'Sugestão inicial para centro de controle de motores; validar conforme cargas atendidas e riscos elétricos.'),
    'Redutor de Velocidade': ('B', 'Sugestão inicial para redutor de acionamento; validar conforme impacto da parada e redundância.'),
    'Transformador de Potência': ('A', 'Sugestão inicial para transformador de potência; validar conforme redundância e impacto no fornecimento.'),
    'Prensa Hidráulica': ('A', 'Sugestão inicial para prensa industrial; validar conforme análise de risco e impacto da parada.'),
}

SETORES = [
    'Linha de Produção A', 'Linha de Produção B', 'Utilidades (Caldeiras)', 
    'Tratamento de Efluentes (ETA)', 'Usinagem de Precisão', 
    'Almoxarifado Central', 'Expedição e Logística', 'Subestação Elétrica'
]

CONFIG_SENSORES = {
    'temperatura': ('°C', 35.0, 85.0, 70.0, 85.0, 100.0),
    'vibracao': ('mm/s RMS', 0.2, 7.0, 65.0, 80.0, 95.0),
    'pressao': ('bar', 2.0, 12.0, 60.0, 85.0, 98.0),
    'corrente': ('A', 10.0, 150.0, 75.0, 90.0, 100.0),
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
    ],
    'preditiva': [
        "Análise de vibração e espectro de frequências para identificação de folga mecânica.",
        "Inspeção termográfica para identificação de pontos quentes em conexões elétricas.",
        "Análise físico-química do óleo lubrificante e contagem de partículas.",
        "Inspeção ultrassônica para detecção de vazamentos em linhas de ar comprimido.",
    ]
}

PROMPT_LABELS = {
    'system_instruction_tecnico': 'Instrução de Sistema — Técnico',
    'system_instruction_gestor': 'Instrução de Sistema — Gestor',
    'system_instruction_admin': 'Instrução de Sistema — Administrador',
    'chat_context': 'Contextualização do Chat',
    'os_analysis': 'Análise de Ordens de Serviço',
    'unassigned_orders': 'Ordens Sem Atribuição',
    'finance': 'Gestão Financeira',
    'trend_analysis': 'Análise de Tendência de Sensores',
}

# ---------------------------------------------------------------------------
# Utilitários
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
    percentual = (atual / total) * 100 if total > 0 else 100.0
    sys.stdout.write(f"\r[{etapa}] Progresso: {percentual:.1f}% ({atual}/{total})")
    sys.stdout.flush()
    if atual == total: print()

def escolher_responsavel(tecnicos_empresa, tecnicos_global, obrigatorio=False):
    """Retorna um técnico da empresa, ou fallback global se obrigatório."""
    if tecnicos_empresa:
        return random.choice(tecnicos_empresa)
    if obrigatorio and tecnicos_global:
        return random.choice(tecnicos_global)
    return None

def salvar_telemetria_bulk(leituras):
    timestamps = [leitura.timestamp for leitura in leituras]
    Telemetria.objects.bulk_create(leituras)
    for leitura, timestamp in zip(leituras, timestamps):
        leitura.timestamp = timestamp
    Telemetria.objects.bulk_update(leituras, ['timestamp'], batch_size=5000)

# ---------------------------------------------------------------------------
# Lógica Principal
# ---------------------------------------------------------------------------
def run_seed(num_empresas=2, equip_por_empresa=10, dias_historico=120, clean_only=False):
    start_total = time.time()
    
    # 1. Limpeza
    t_start = time.time()
    print("\n[CLEAN] Limpando banco de dados...")
    models_to_clear = [
        Alerta, 
        HistoricoManutencao, 
        OrdemServico, 
        Telemetria, 
        TrendConfig, 
        Sensor, 
        PlanoManutencao, 
        EquipamentoLocalizacao, 
        Equipamento, 
        TipoEquipamento,
        PromptConfig, 
        Empresa
    ]
    for model in models_to_clear:
        model.objects.all().delete()
        
    Usuario.objects.filter(is_superuser=False).delete()
    _usernames_usados.clear()
    print(f"OK: Banco de dados limpo com sucesso! (Duração: {time.time() - t_start:.2f}s)")

    if clean_only:
        print("\n[INFO] Modo apenas limpeza executado. Encerrando.")
        return

    print(f"\n[START] Populando banco de dados: {num_empresas} empresas, ~{equip_por_empresa} ativos/empresa, {dias_historico} dias de histórico.")

    # 2. Configurações Globais (Prompts Gemini e TrendConfig)
    print("\n[CONFIG] Configurando Prompts do Gemini AI e TrendConfig padrão...")
    t_start = time.time()
    for key, text in GEMINI_DEFAULTS.items():
        label = PROMPT_LABELS.get(key, key.replace('_', ' ').capitalize())
        PromptConfig.objects.create(
            key=key,
            label=label,
            original_text=text,
            custom_text='',
        )

    TrendConfig.objects.create(
        sensor=None,
        periodo_horas=24,
        num_leituras=50,
        sensibilidade='media',
        ativo=True
    )
    print(f"OK (Duração: {time.time() - t_start:.2f}s)")

    # 3. Admin
    print("\n[ADMIN] Configurando acesso administrativo...")
    t_start = time.time()
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(
            username='admin', 
            email='suporte@bughunter.com', 
            password='admin', 
            tipo_usuario='admin',
            cargo='Administrador do Sistema'
        )
    print(f"OK (Duração: {time.time() - t_start:.2f}s)")

    # 4. Empresas e Usuários
    t_start = time.time()
    empresas = []
    tipos_por_empresa = {}
    print("\n[USERS] Criando Empresas, Gestores e Técnicos...")
    for i in range(num_empresas):
        emp_nome = fake.company()
        cidade, estado = random.choice(CIDADES_ESTADOS)
        emp = Empresa.objects.create(
            nome=emp_nome, 
            cnpj=fake.cnpj(), 
            email=fake.company_email(), 
            telefone=fake.phone_number(), 
            cidade=cidade,
            estado=estado,
            endereco=fake.address()
        )
        empresas.append(emp)
        tipos_por_empresa[emp.id] = {}
        for tipo_nome, (criticidade_padrao, criterios) in CRITICIDADE_TIPOS.items():
            tipo_catalogo = TipoEquipamento.objects.create(
                empresa=emp,
                nome=tipo_nome,
                criticidade_padrao=criticidade_padrao,
                descricao_criterios=criterios,
            )
            tipos_por_empresa[emp.id][tipo_nome] = tipo_catalogo
        
        # Gestor
        g_nome = fake.name()
        u_name, u_email = gerar_credenciais_reais(g_nome, emp_nome)
        Usuario.objects.create_user(
            username=u_name, 
            email=u_email, 
            password='123', 
            empresa=emp, 
            tipo_usuario='gestor', 
            first_name=g_nome.split()[0], 
            last_name=" ".join(g_nome.split()[1:]),
            cargo=random.choice(CARGOS_GESTOR),
            telefone=fake.phone_number()
        )
        
        # Técnicos (3 a 5 por empresa)
        for _ in range(random.randint(3, 5)):
            t_nome = fake.name()
            u_name, u_email = gerar_credenciais_reais(t_nome, emp_nome)
            Usuario.objects.create_user(
                username=u_name, 
                email=u_email, 
                password='123', 
                empresa=emp, 
                tipo_usuario='tecnico', 
                first_name=t_nome.split()[0], 
                last_name=" ".join(t_nome.split()[1:]),
                cargo=random.choice(CARGOS_TECNICO),
                telefone=fake.phone_number()
            )
        log_progresso("Empresas", i + 1, num_empresas)
    print(f"OK (Duração: {time.time() - t_start:.2f}s)")

    # 5. Equipamentos, Planos e Sensores
    t_start = time.time()
    print("\n[ASSETS] Gerando Ativos, Planos de Manutenção e Sensores...")
    now = timezone.now()
    inicio_historico = now - timedelta(days=dias_historico)
    todos_sensores = []
    total_equip = num_empresas * equip_por_empresa
    count = 0
    
    for emp in empresas:
        for _ in range(equip_por_empresa):
            tipo_nome, sensores_list, modelo_base, desc_equip = random.choice(TIPOS_EQUIP)
            status = random.choices(['ativo', 'manutencao', 'inativo'], weights=[0.85, 0.10, 0.05])[0]
            criticidade_sugerida = CRITICIDADE_TIPOS[tipo_nome][0]
            
            eq = Equipamento.objects.create(
                empresa=emp, 
                nome=f"{tipo_nome} {fake.bothify(text='##-??')}", 
                tipo=tipo_nome,
                tipo_equipamento=tipos_por_empresa[emp.id][tipo_nome],
                fabricante=random.choice(FABRICANTES), 
                modelo=f"{modelo_base} {fake.bothify(text='-####')}",
                numero_serie=fake.unique.bothify(text="SN-####-####").upper(),
                descricao=desc_equip,
                data_instalacao=fake.date_between(start_date='-3y', end_date='-6m'),
                status=status, 
                horimetro=random.uniform(150.0, 9500.0)
            )
            aplicar_criticidade(
                eq,
                eq.tipo_equipamento.criticidade_padrao,
                eq.tipo_equipamento.descricao_criterios,
                origem='tipo',
            )
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=random.choice(SETORES))

            # Planos de Manutenção
            PlanoManutencao.objects.create(
                equipamento=eq, 
                nome_servico="Revisão Periódica Nível 1", 
                descricao="Revisão preventiva de rotina com checagem de alinhamento, torqueamento e lubrificação.",
                intervalo_horas=random.choice([250.0, 500.0, 1000.0]), 
                prioridade='media',
                ativo=True
            )
            if random.random() > 0.5:
                PlanoManutencao.objects.create(
                    equipamento=eq, 
                    nome_servico="Inspeção Geral de Segurança e Confiabilidade (NR-12/NR-13)", 
                    descricao="Inspeção técnica completa para atendimento às normas regulamentadoras e teste de intertravamentos.",
                    intervalo_horas=random.choice([2000.0, 4000.0]), 
                    prioridade='critica' if criticidade_sugerida == 'A' else 'alta',
                    ativo=True
                )

            # Sensores
            for s_tipo in sensores_list:
                unidade, min_v, max_v, low_pct, med_pct, crit_pct = CONFIG_SENSORES.get(
                    s_tipo, ('un', 0.0, 100.0, 70.0, 85.0, 100.0)
                )
                sensor = Sensor.objects.create(
                    equipamento=eq, 
                    tipo=s_tipo, 
                    unidade_medida=unidade,
                    nome=f"Sensor de {s_tipo.capitalize()}",
                    limite_alerta=max_v,
                    limite_alerta_baixo_pct=low_pct,
                    limite_alerta_medio_pct=med_pct,
                    limite_alerta_critico_pct=crit_pct,
                    descricao=f"Sensor industrial de monitoramento contínuo de {s_tipo}.",
                    ativo=True
                )
                todos_sensores.append((sensor, min_v, max_v))
            
            count += 1
            log_progresso("Ativos", count, total_equip)
    print(f"OK (Duração: {time.time() - t_start:.2f}s)")

    # 6. Telemetria (Simulação Coerente com Tendências e Ruído Realista)
    t_start = time.time()
    print(f"\n[TELEMETRY] Gerando histórico de telemetria ({dias_historico} dias)...")
    leituras_bulk = []
    total_horas = dias_historico * 24
    
    for sensor, min_v, max_v in todos_sensores:
        base_val = random.uniform(min_v, (min_v + max_v) / 2)
        trend = random.uniform(-0.005, 0.03) # Tendência sutil de desgaste
        
        # Gerar 1 leitura por hora
        for h in range(total_horas):
            ponto = inicio_historico + timedelta(hours=h)
            fluctuacao = random.uniform(-0.4, 0.4)
            val = base_val + (h * trend) + fluctuacao
            
            # Garantir limites seguros
            val = max(min_v * 0.8, min(val, max_v * 1.4))
            
            leituras_bulk.append(Telemetria(sensor=sensor, valor=round(val, 2), timestamp=ponto))
            
            if len(leituras_bulk) >= 5000:
                salvar_telemetria_bulk(leituras_bulk)
                leituras_bulk = []
                
    if leituras_bulk: 
        salvar_telemetria_bulk(leituras_bulk)
    print(f"OK: {Telemetria.objects.count()} registros de telemetria gerados. (Duração: {time.time() - t_start:.2f}s)")

    # 7. Ordens de Serviço, Histórico e Alertas
    t_start = time.time()
    print("\n[MAINTENANCE] Criando Ordens de Serviço, Histórico e Alertas...")
    equips = list(Equipamento.objects.all())
    tecnicos = list(Usuario.objects.filter(tipo_usuario='tecnico'))
    total_equips = len(equips)
    
    for idx, eq in enumerate(equips):
        tecnicos_empresa = [t for t in tecnicos if t.empresa_id == eq.empresa_id]
        
        # Gerar conjunto de OS passadas e recentes
        num_os = random.randint(3, 8)
        janela_inicial = now - timedelta(days=dias_historico)
        data_os = janela_inicial + timedelta(days=random.randint(0, 5), hours=random.randint(0, 23))
        if data_os > now:
            data_os = now - timedelta(days=7)

        for ordem_idx in range(num_os):
            tipo_os = random.choice(['preventiva', 'corretiva', 'preditiva'])
            gravidade = (
                random.choice(['baixa', 'moderada', 'alta', 'critica'])
                if tipo_os == 'corretiva' else 'ausente'
            )
            dados_prioridade = PrioridadeOSService.preencher({
                'tipo_os': tipo_os,
                'gravidade_condicao': gravidade,
                'risco_seguranca': tipo_os == 'corretiva' and random.random() < 0.08,
            }, eq)
            
            # A última OS tem maior probabilidade de estar em aberto ou em andamento
            if ordem_idx == num_os - 1:
                status_os = random.choices(['andamento', 'pendente', 'concluida'], weights=[0.4, 0.3, 0.3])[0]
            else:
                status_os = random.choices(['concluida', 'pendente', 'cancelada'], weights=[0.75, 0.15, 0.10])[0]

            if status_os == 'andamento':
                data_abertura = now - timedelta(hours=random.randint(1, 24))
            else:
                data_abertura = data_os

            if status_os in ['concluida', 'cancelada']:
                if status_os == 'cancelada':
                    horas_reparo = random.randint(1, 8)
                elif tipo_os == 'preventiva':
                    horas_reparo = random.randint(2, 10)
                elif tipo_os == 'preditiva':
                    horas_reparo = random.randint(3, 16)
                else:
                    horas_reparo = random.randint(4, 32)
                data_conclusao_os = data_abertura + timedelta(hours=horas_reparo)
                if data_conclusao_os > now:
                    data_conclusao_os = now - timedelta(minutes=random.randint(5, 60))
            else:
                data_conclusao_os = None

            if status_os == 'pendente' and random.random() < 0.7:
                responsavel_os = None
            else:
                responsavel_os = escolher_responsavel(
                    tecnicos_empresa, tecnicos, 
                    obrigatorio=status_os in ['concluida', 'cancelada', 'andamento']
                )

            os_obj = OrdemServico.objects.create(
                equipamento=eq, 
                responsavel=responsavel_os,
                titulo=f"{tipo_os.capitalize()} - {eq.nome}", 
                descricao=f"Atendimento de manutenção {tipo_os} para o equipamento {eq.nome} ({eq.tipo}).",
                status=status_os, 
                data_abertura=data_abertura,
                data_conclusao=data_conclusao_os,
                **dados_prioridade
            )
            
            # Histórico para OS Concluídas
            if status_os == 'concluida':
                HistoricoManutencao.objects.update_or_create(
                    ordem_servico=os_obj,
                    defaults={
                        'data_execucao': (data_conclusao_os.date() if data_conclusao_os else data_abertura.date()),
                        'descricao_servico': random.choice(ACOES_MANUTENCAO.get(tipo_os, ACOES_MANUTENCAO['preventiva'])),
                        'custo_pecas': Decimal(round(random.uniform(150.0, 3200.0), 2)),
                        'custo_mao_de_obra': Decimal(round(random.uniform(250.0, 1800.0), 2)),
                    },
                )

            # Avançar a data da próxima OS
            if status_os in ['concluida', 'cancelada']:
                gap_days = random.uniform(2.0, 15.0)
                data_os = data_conclusao_os + timedelta(days=gap_days, hours=random.randint(0, 4))
            elif status_os == 'pendente':
                data_os = data_abertura + timedelta(days=random.uniform(1.0, 8.0))
            else:
                data_os = data_abertura + timedelta(hours=random.uniform(4.0, 24.0))

            if data_os > now:
                data_os = now - timedelta(days=random.randint(1, 5), hours=random.randint(0, 12))

        # Alertas e OS para equipamentos em manutenção
        if eq.status == 'manutencao':
            Alerta.objects.create(
                equipamento=eq, 
                tipo_alerta="Parada Não Programada", 
                nivel='critico',
                descricao="Alerta disparado por interrupção brusca nos parâmetros operacionais.",
                status='ativo',
                origem='manual',
            )
        
        elif random.random() > 0.8: # Alertas esporádicos em equipamentos ativos
            nivel_alerta = random.choice(['baixo', 'medio', 'critico'])
            tipo_al = random.choice([
                "Anomalia de Vibração RMS", 
                "Sobretemperatura de Mancal", 
                "Sobrecorrente na Fase R", 
                "Queda de Pressão na Linha"
            ])
            Alerta.objects.create(
                equipamento=eq, 
                tipo_alerta=tipo_al, 
                nivel=nivel_alerta,
                descricao=f"Desvio detectado: {tipo_al} fora dos padrões nominais da ISO 10816 / FMEA.",
                status=random.choice(['ativo', 'resolvido']),
                origem='manual',
            )

        log_progresso("Manutenção & Alertas", idx + 1, total_equips)
    print(f"OK (Duração: {time.time() - t_start:.2f}s)")

    total_time = time.time() - start_total
    print(f"\n[DONE] Banco de dados populado com sucesso em {total_time:.2f}s!")
    print(f"Resumo Final:")
    print(f" - Empresas: {Empresa.objects.count()}")
    print(f" - Usuários: {Usuario.objects.count()} (Superuser admin + Gestores + Técnicos)")
    print(f" - Equipamentos: {Equipamento.objects.count()}")
    print(f" - Sensores: {Sensor.objects.count()}")
    print(f" - Telemetria: {Telemetria.objects.count()} registros")
    print(f" - Ordens de Serviço: {OrdemServico.objects.count()}")
    print(f" - Históricos de Manutenção: {HistoricoManutencao.objects.count()}")
    print(f" - Alertas: {Alerta.objects.count()}")
    print(f" - PromptConfigs Gemini: {PromptConfig.objects.count()}")
    print(f" - TrendConfigs: {TrendConfig.objects.count()}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed industrial completo e atualizado para o sistema BugHunter.')
    parser.add_argument('--empresas', type=int, default=2, help='Número de empresas a criar')
    parser.add_argument('--equipamentos', type=int, default=10, help='Número de equipamentos por empresa')
    parser.add_argument('--days', type=int, default=120, help='Dias de histórico de telemetria e manutenção')
    parser.add_argument('--clean-only', action='store_true', help='Apenas limpa o banco de dados sem popular')
    args = parser.parse_args()
    
    try:
        run_seed(args.empresas, args.equipamentos, args.days, args.clean_only)
    except Exception as e:
        print(f"\n[ERROR] Falha crítica no seed: {e}")
        import traceback
        traceback.print_exc()
