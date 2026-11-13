"""Dados sintéticos de demonstração. A limpeza é destrutiva e a geração é atômica."""
import os
import sys
import django
import random
import math
import re
import argparse
import time
from datetime import timedelta
from decimal import Decimal
import unicodedata
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.models import F, Q
from django.utils import timezone

# Configuração do Ambiente Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from faker import Faker
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao, PlanoManutencao, TipoEquipamento, CriteriosCriticidade
from ativos.services import aplicar_criticidade, CRITERIOS_SUGERIDOS
from telemetria.models import Sensor, Telemetria, TrendConfig
from telemetria.predictive_service import sync_sensor_trend
from telemetria.limit_service import sync_limit_reading
from manutencao.models import OrdemServico, HistoricoManutencao
from manutencao.services import registros_alerta
from alertas.models import Alerta
from gemini_api.models import PromptConfig
from gemini_api.prompt_builder import DEFAULTS as GEMINI_DEFAULTS

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

FABRICANTES_POR_TIPO = {
    'Motor Elétrico Trifásico': 'WEG', 'Bomba Centrífuga': 'KSB',
    'Compressor de Parafuso': 'Atlas Copco', 'Painel de Comando (CCM)': 'Siemens',
    'Redutor de Velocidade': 'SEW-Eurodrive', 'Transformador de Potência': 'ABB',
    'Prensa Hidráulica': 'Schuler',
}
SERVICOS_POR_TIPO = {
    'Motor Elétrico Trifásico': 'Inspeção de conexões elétricas, ventilação e fixação do motor.',
    'Bomba Centrífuga': 'Inspeção de vedação, acoplamento e pressão da bomba.',
    'Compressor de Parafuso': 'Inspeção de filtros, lubrificação e pressão do compressor.',
    'Painel de Comando (CCM)': 'Inspeção termográfica e verificação de conexões do painel.',
    'Redutor de Velocidade': 'Inspeção de lubrificação, acoplamento e vibração do redutor.',
    'Transformador de Potência': 'Inspeção de ventilação, temperatura e conexões do transformador.',
    'Prensa Hidráulica': 'Inspeção de mangueiras, vedação e pressão do circuito hidráulico.',
}

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
    """Nomes ASCII e domínio reservado, sem sugerir um contato real."""
    def ascii_text(text):
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    partes = re.sub(r'[^a-z0-9\s]', '', ascii_text(nome)).split()
    username = f'{partes[0]}.{partes[-1]}' if len(partes) >= 2 else (partes or ['demo'])[0]
    base = username = username[:60]
    contador = 1
    while username in _usernames_usados or Usuario.objects.filter(username=username).exists():
        username = f'{base}{contador}'
        contador += 1
    _usernames_usados.add(username)
    dominio = re.sub(r'[^a-z0-9]', '', ascii_text(empresa_nome))[:40] or 'empresa'
    email = f'{username}@{dominio}.example.com'
    validate_email(email)
    return username, email


def log_progresso(etapa, atual, total):
    percentual = (atual / total) * 100 if total > 0 else 100.0
    sys.stdout.write(f"\r[{etapa}] Progresso: {percentual:.1f}% ({atual}/{total})")
    sys.stdout.flush()
    if atual == total: print()

def salvar_telemetria_bulk(leituras):
    timestamps = [leitura.timestamp for leitura in leituras]
    Telemetria.objects.bulk_create(leituras)
    for leitura, timestamp in zip(leituras, timestamps):
        leitura.timestamp = timestamp
    Telemetria.objects.bulk_update(leituras, ['timestamp'], batch_size=5000)


def gerar_historico_sensor(minimo, limite, inicio, fim, perfil='estavel', rng=None):
    """Histórico sintético suave, com horários irregulares e escala do sensor.

    A mudança de regime ocorre nas últimas 24 horas, sem acumular desgaste
    durante meses até todas as leituras ficarem presas no teto.
    """
    if perfil not in ('estavel', 'crescente', 'recuperacao'):
        raise ValueError('Perfil de telemetria desconhecido.')
    rng = rng or random
    if perfil == 'crescente':
        base = rng.uniform(.40, .48) * limite
        mudanca = rng.uniform(.54, .60) * limite
    elif perfil == 'recuperacao':
        base = rng.uniform(.68, .76) * limite
        mudanca = -rng.uniform(.25, .35) * limite
    else:
        base = rng.uniform(.48, .55) * limite
        mudanca = 0
    fase = rng.uniform(0, math.tau)
    periodo = rng.uniform(18, 30)
    horarios = []
    ponto = fim - timedelta(minutes=rng.uniform(2, 12))
    while ponto >= inicio:
        horarios.append(ponto)
        ponto -= timedelta(minutes=rng.uniform(40, 85))
    for ponto in reversed(horarios):
        horas = (ponto - inicio).total_seconds() / 3600
        progresso = max(0, min(1, 1 - (fim - ponto).total_seconds() / 86400))
        oscilacao = math.sin(math.tau * horas / periodo + fase) * limite * .012
        ruido = rng.uniform(-.003, .003) * limite
        valor = base + mudanca * progresso + oscilacao + ruido
        # O ruído é proporcional à grandeza: não domina sensores de escala pequena.
        yield ponto, round(max(minimo * .8, min(valor, limite * 1.1)), 4)

def gerar_historico_apresentacao(minimo, limite, inicio, fim, perfil, rng):
    """Cenários identificados, suaves e com evidências nas últimas 24 horas."""
    if perfil == 'estavel':
        yield from gerar_historico_sensor(minimo, limite, inicio, fim, rng=rng)
        return
    marcos = {
        'preditiva': [(-24, .40), (0, .98)],
        'ativo': [(-24, .50), (-6, .50), (0, 1.05)],
        'recuperado': [(-24, .50), (-20, .50), (-14, 1.05), (-13, 1.05), (-7, .50), (0, .50)],
        'recorrencia': [(-24, .50), (-23, .50), (-19, 1.05), (-15, .50),
                        (-13, .50), (-9, 1.05), (-5, .50), (0, .50)],
    }[perfil]
    recente = max(inicio, fim - timedelta(hours=24))
    for ponto, valor in gerar_historico_sensor(minimo, limite, inicio, recente, rng=rng):
        # Aproxima o histórico antigo do primeiro marco, evitando uma quebra de
        # regime instantânea na junção com o cenário das últimas 24 horas.
        base = marcos[0][1] + (valor / limite - .5) * .05
        yield ponto, round(max(minimo * .8, limite * base), 4)
    horarios = [fim - timedelta(minutes=5)]
    while horarios[-1] > recente:
        anterior = horarios[-1] - timedelta(minutes=rng.uniform(10, 20))
        horarios.append(max(recente, anterior))
    for ponto in reversed(horarios):
        hora = (ponto - fim).total_seconds() / 3600
        for (h0, v0), (h1, v1) in zip(marcos, marcos[1:]):
            if h0 <= hora <= h1:
                proporcao = v0 + (v1 - v0) * (hora - h0) / (h1 - h0)
                yield ponto, round(max(minimo * .8, limite * proporcao), 4)
                break


def reprocessar_limites_historicos(sensor, inicio):
    """Importa ocorrências sintéticas pelos serviços reais, em ordem temporal.

    auto_now_add representa a importação, por isso ajustamos somente as datas
    sintéticas de abertura após a criação. O relógio do processo não é alterado.
    A evidência, a gravidade, a recuperação e os vínculos são decisões do serviço.
    """
    vistos = set()
    for leitura in Telemetria.objects.filter(sensor=sensor, timestamp__gte=inicio).order_by('timestamp', 'pk').iterator():
        alerta = sync_limit_reading(leitura)
        if alerta is not None and alerta.pk not in vistos:
            vistos.add(alerta.pk)
            abertura_id = (alerta.dados_deteccao.get('analise') or {}).get('ultima_leitura_id')
            if abertura_id != leitura.pk:
                continue  # reprocessamento: não redatar um episódio já importado
            Alerta.objects.filter(pk=alerta.pk).update(data_alerta=leitura.timestamp)
            ordem = alerta.ordem_servico
            if ordem is not None and ordem.data_abertura > leitura.timestamp:
                OrdemServico.objects.filter(pk=ordem.pk).update(data_abertura=leitura.timestamp)
    # Reconstrói os cabeçalhos legíveis com as datas importadas, inclusive recorrências.
    for ordem in OrdemServico.objects.filter(sensor_origem=sensor, tipo_os='corretiva'):
        alertas = Alerta.objects.filter(ordem_servico=ordem).order_by('data_alerta', 'pk')
        ordem.descricao = '[DEMO] Ocorrências importadas do histórico sintético.\n\n' + '\n\n'.join(
            registro for alerta in alertas for registro in registros_alerta(alerta))
        ordem.save(update_fields=['descricao'])


def validar_parametros(num_empresas, equip_por_empresa, dias_historico, funcionarios_por_empresa):
    for nome, valor in [('empresas', num_empresas), ('equipamentos', equip_por_empresa), ('days', dias_historico)]:
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
            raise ValueError(f'{nome} deve ser um inteiro maior ou igual a 1.')
    if funcionarios_por_empresa is not None and (
        isinstance(funcionarios_por_empresa, bool) or not isinstance(funcionarios_por_empresa, int)
        or funcionarios_por_empresa < 2
    ):
        raise ValueError('Use pelo menos 2 funcionários por empresa: 1 gestor e 1 técnico.')


def verificar_banco():
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise RuntimeError('Há migrações pendentes. Execute python manage.py migrate antes do seed.')
    print(f'[BANCO] {connection.vendor} | {connection.settings_dict["NAME"]} | '
          f'host={connection.settings_dict.get("HOST") or "local"}')


def criar_usuario_demo(empresa, papel, indice, fake, rng):
    nome = fake.name()
    # A parte numérica é estável e o resolvedor protege nomes de admins preservados.
    login_base = f'{papel}.demo.{indice}'
    login = login_base
    sufixo = 1
    while Usuario.objects.filter(username=login).exists():
        login = f'{login_base}.{sufixo}'
        sufixo += 1
    email = f'{login}@empresa{indice.split(".")[0]}.example.com'
    validate_email(email)
    usuario = Usuario.objects.create_user(
        username=login, email=email, password='123', empresa=empresa, tipo_usuario=papel,
        first_name=nome.split()[0], last_name=' '.join(nome.split()[1:]),
        cargo=rng.choice(CARGOS_GESTOR if papel == 'gestor' else CARGOS_TECNICO),
        telefone=fake.phone_number(),
    )
    return usuario


def criar_ordens_historicas(eq, tecnicos, inicio, fim, rng):
    dias = (fim - inicio).total_seconds() / 86400
    # Duas conclusões recentes, inclusive para dias=1; outras cobrem a janela inteira.
    idades = [dias * .85, dias * .50, min(3, dias * .25), min(1, dias * .10)]
    for indice, idade in enumerate(idades):
        abertura = fim - timedelta(days=idade)
        conclusao = abertura + timedelta(hours=rng.uniform(.5, 1.5))
        tipo = ['corretiva', 'preventiva', 'corretiva', 'preditiva'][indice]
        texto = f'[DEMO] {SERVICOS_POR_TIPO[eq.tipo]}'
        ordem = OrdemServico.objects.create(
            equipamento=eq, responsavel=tecnicos[indice % len(tecnicos)],
            titulo=f'[DEMO] {tipo.capitalize()} - {eq.nome}', descricao=texto,
            tipo_os=tipo, gravidade_condicao='baixa' if tipo == 'corretiva' else 'ausente',
            status='concluida', data_abertura=abertura, data_conclusao=conclusao,
        )
        HistoricoManutencao.objects.update_or_create(ordem_servico=ordem, defaults={
            'data_execucao': timezone.localdate(conclusao), 'descricao_servico': texto,
            'custo_pecas': Decimal(rng.randrange(15000, 320001)) / 100,
            'custo_mao_de_obra': Decimal(rng.randrange(25000, 180001)) / 100,
        })
    OrdemServico.objects.create(
        equipamento=eq, responsavel=tecnicos[0], titulo=f'[DEMO] Inspeção cancelada - {eq.nome}',
        descricao='[DEMO] Solicitação duplicada, cancelada antes da execução; sem custos.',
        status='cancelada', data_abertura=fim - timedelta(days=dias * .4),
        data_conclusao=fim - timedelta(days=dias * .35),
    )
    if eq.status == 'ativo':
        OrdemServico.objects.create(
            equipamento=eq, titulo=f'[DEMO] Inspeção disponível - {eq.nome}',
            descricao=f'[DEMO] Aguardando atribuição. {SERVICOS_POR_TIPO[eq.tipo]}',
            status='pendente', data_abertura=fim - timedelta(hours=1),
        )


def validar_populacao(empresas, now, equip_por_empresa):
    """Invariantes da demonstração: falhas impedem o commit de uma base incompleta."""
    ordens = OrdemServico.objects.filter(equipamento__empresa__in=empresas)
    if ordens.filter(data_conclusao__lt=F('data_abertura')).exists() or ordens.filter(data_abertura__gt=timezone.now()).exists():
        raise RuntimeError('Cronologia inválida nas ordens geradas.')
    if ordens.filter(data_conclusao__gt=timezone.now()).exists():
        raise RuntimeError('Há manutenção concluída com data futura.')
    if ordens.filter(data_abertura__date__lt=F('equipamento__data_instalacao')).exists():
        raise RuntimeError('Há ordem anterior à instalação do equipamento.')
    if ordens.filter(responsavel__isnull=False).exclude(responsavel__empresa_id=F('equipamento__empresa_id')).exists():
        raise RuntimeError('Responsável de outra empresa na demonstração.')
    if Telemetria.objects.filter(timestamp__date__lt=F('sensor__equipamento__data_instalacao')).exists():
        raise RuntimeError('Há telemetria anterior à instalação do equipamento.')
    for empresa in empresas:
        for usuario in empresa.usuarios.all():
            validate_email(usuario.email)
            if usuario.tipo_usuario == 'tecnico' and not ordens.filter(responsavel=usuario, status='andamento').exists():
                raise RuntimeError(f'Técnico {usuario.username} sem trabalho em andamento.')
        for eq in empresa.equipamentos.all():
            recentes = ordens.filter(equipamento=eq, status='concluida', data_abertura__gte=now - timedelta(days=7))
            if recentes.count() < 2:
                raise RuntimeError(f'Equipamento {eq.nome} sem histórico recente suficiente para KPIs.')
        if equip_por_empresa >= 3:
            classes = set(empresa.equipamentos.values_list('criticidade', flat=True))
            if not {'A', 'B', 'C'} <= classes:
                raise RuntimeError('Cobertura ABC incompleta.')
            alertas = Alerta.objects.filter(equipamento__empresa=empresa)
            if not alertas.filter(origem='limite', status='ativo').exists() or not alertas.filter(origem='limite', status='resolvido').exists():
                raise RuntimeError('Cobertura de alerta ativo e normalizado incompleta.')
            if not ordens.filter(equipamento__empresa=empresa, alerta_origem__origem='tendencia', tipo_os='preditiva').exists():
                raise RuntimeError('Nenhuma ordem originada da previsão de tendência.')


def _popular(num_empresas, equip_por_empresa, dias_historico, funcionarios_por_empresa, rng_seed):
    rng = random.Random(rng_seed)
    fake = Faker('pt_BR')
    fake.seed_instance(rng_seed)
    now = timezone.now()
    inicio = now - timedelta(days=dias_historico)
    for key, texto in GEMINI_DEFAULTS.items():
        PromptConfig.objects.create(key=key, label=PROMPT_LABELS.get(key, key), original_text=texto, custom_text='')
    TrendConfig.objects.create(sensor=None, periodo_horas=24, num_leituras=50, sensibilidade='media', ativo=True)
    admin, criado = Usuario.objects.get_or_create(username='admin', defaults={
        'email': 'admin@example.com', 'tipo_usuario': 'admin', 'is_staff': True, 'is_superuser': True,
        'cargo': 'Administrador do Sistema',
    })
    if criado:
        admin.set_password('admin')
        admin.save()
    empresas, roteiro = [], []
    for numero in range(1, num_empresas + 1):
        cidade, estado = rng.choice(CIDADES_ESTADOS)
        empresa = Empresa.objects.create(
            nome=f'[DEMO {numero:02d}] {fake.company()}', cnpj=fake.unique.cnpj(),
            email=f'contato@empresa{numero}.example.com', telefone=fake.phone_number(),
            cidade=cidade, estado=estado, endereco=f'{fake.street_address()} - {cidade}/{estado} (endereço fictício)',
        )
        empresas.append(empresa)
        CriteriosCriticidade.objects.create(
            empresa=empresa, revisao=1, **CRITERIOS_SUGERIDOS,
            representante_manutencao='Validação fictícia — dados de demonstração',
            data_validacao=timezone.localdate(inicio) - timedelta(days=1),
        )
        tipos = {nome: TipoEquipamento.objects.create(
            empresa=empresa, nome=nome, criticidade_padrao=classe, descricao_criterios=justificativa,
        ) for nome, (classe, justificativa) in CRITICIDADE_TIPOS.items()}
        gestor = criar_usuario_demo(empresa, 'gestor', str(numero), fake, rng)
        total_tecnicos = funcionarios_por_empresa - 1 if funcionarios_por_empresa is not None else 3
        tecnicos = [criar_usuario_demo(empresa, 'tecnico', f'{numero}.{i}', fake, rng)
                    for i in range(1, total_tecnicos + 1)]
        itens, ativos = [], []
        for indice in range(equip_por_empresa):
            tipo, sensores_tipo, modelo, descricao = TIPOS_EQUIP[indice % len(TIPOS_EQUIP)]
            status = ['ativo', 'ativo', 'ativo', 'manutencao', 'inativo'][indice % 5]
            # A instalação precede o histórico inteiro, sem strings relativas ambíguas do Faker.
            instalacao = timezone.localdate(inicio) - timedelta(days=rng.randint(180, 720))
            eq = Equipamento.objects.create(
                empresa=empresa, nome=f'[DEMO] {tipo} E{numero:02d}-{indice + 1:02d}', tipo=tipo,
                tipo_equipamento=tipos[tipo], fabricante=FABRICANTES_POR_TIPO[tipo], modelo=modelo,
                numero_serie=f'DEMO-E{numero:03d}-{indice + 1:04d}', descricao=f'[DEMO] {descricao}',
                data_instalacao=instalacao, status=status, horimetro=1000 + indice * 250,
            )
            classe, justificativa = CRITICIDADE_TIPOS[tipo]
            if indice % 3 == 2:
                classe, justificativa = 'C', 'Unidade fictícia de reserva com redundância disponível e baixo impacto de parada.'
            aplicar_criticidade(eq, classe, justificativa, usuario=gestor, origem='individual' if classe == 'C' else 'tipo')
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=SETORES[indice % len(SETORES)])
            plano = PlanoManutencao.objects.create(
                equipamento=eq, nome_servico='[DEMO] Inspeção periódica', descricao=SERVICOS_POR_TIPO[tipo],
                intervalo_horas=250, prioridade='media', ativo=True,
            )
            if status == 'ativo':
                ativos.append(eq)
            sensores_roteiro = []
            for s_tipo in sensores_tipo:
                unidade, minimo, limite, baixo, medio, critico = CONFIG_SENSORES[s_tipo]
                perfil = 'estavel'
                if indice == 1 and s_tipo == 'temperatura':
                    perfil = 'preditiva'
                elif indice == 2:
                    perfil = {'pressao': 'ativo', 'vibracao': 'recuperado', 'temperatura': 'recorrencia'}[s_tipo]
                sensor = Sensor.objects.create(
                    equipamento=eq, nome=f'Sensor de {s_tipo.capitalize()}', tipo=s_tipo, unidade_medida=unidade,
                    limite_alerta=limite, limite_alerta_baixo_pct=baixo, limite_alerta_medio_pct=medio,
                    limite_alerta_critico_pct=critico, ativo=status != 'inativo',
                    descricao=f'[DEMO] Perfil histórico: {perfil}. Dados sintéticos.',
                )
                fim = now - timedelta(hours=min(24, dias_historico * 12)) if status == 'inativo' else now
                buffer = []
                for ponto, valor in gerar_historico_apresentacao(minimo, limite, inicio, fim, perfil, rng):
                    buffer.append(Telemetria(sensor=sensor, timestamp=ponto, valor=valor))
                    if len(buffer) >= 5000:
                        salvar_telemetria_bulk(buffer)
                        buffer = []
                if buffer:
                    salvar_telemetria_bulk(buffer)
                if sensor.ativo:
                    reprocessar_limites_historicos(sensor, now - timedelta(hours=24))
                    sync_sensor_trend(sensor.pk)
                sensores_roteiro.append({'id': sensor.pk, 'tipo': s_tipo, 'perfil': perfil})
            criar_ordens_historicas(eq, tecnicos, inicio, now, rng)
            if status == 'manutencao':
                OrdemServico.objects.create(
                    equipamento=eq, responsavel=tecnicos[0], status='andamento',
                    titulo=f'[DEMO] Manutenção em execução - {eq.nome}',
                    descricao=f'[DEMO] Equipamento parado para serviço. {SERVICOS_POR_TIPO[tipo]}',
                    data_abertura=now - timedelta(hours=2),
                )
            itens.append({'id': eq.pk, 'nome': eq.nome, 'status': status, 'sensores': sensores_roteiro,
                         'plano_id': plano.pk, 'horimetro': eq.horimetro,
                         'proximo_disparo': plano.horimetro_ultima_os + plano.intervalo_horas})
            log_progresso(f'Empresa {numero}: ativos e histórico', indice + 1, equip_por_empresa)
        for indice, tecnico in enumerate(tecnicos):
            eq = ativos[indice % len(ativos)]
            for status in ['pendente', 'andamento']:
                OrdemServico.objects.create(
                    equipamento=eq, responsavel=tecnico, status=status,
                    titulo=f'[DEMO] Inspeção {status} - {eq.nome}',
                    descricao=f'[DEMO] Trabalho atribuído a {tecnico.get_full_name()}. {SERVICOS_POR_TIPO[eq.tipo]}',
                    data_abertura=now - timedelta(minutes=30 if status == 'pendente' else 60),
                )
        roteiro.append({'id': empresa.pk, 'nome': empresa.nome, 'gestor': gestor.username,
                        'tecnicos': [t.username for t in tecnicos], 'equipamentos': itens})
    validar_populacao(empresas, now, equip_por_empresa)
    return {'admin': admin.username, 'admin_criado': criado, 'empresas': roteiro, 'seed': rng_seed}


def run_seed(num_empresas=2, equip_por_empresa=10, dias_historico=120, clean_only=False,
             funcionarios_por_empresa=None, rng_seed=42, check_only=False):
    # Nenhuma escrita pode acontecer antes destas verificações.
    validar_parametros(num_empresas, equip_por_empresa, dias_historico, funcionarios_por_empresa)
    verificar_banco()
    if equip_por_empresa < 3 and not clean_only:
        print('[AVISO] Menos de 3 equipamentos/empresa: cobertura parcial; use 3 ou mais para todos os cenários.')
    if check_only:
        print('[CHECK] Parâmetros e migrações válidos. Nenhum dado foi alterado.')
        return
    inicio = time.monotonic()
    with transaction.atomic():
        # Desvincular antes da cascata também preserva o hash de senha e o perfil.
        preservados = Q(is_superuser=True) | Q(tipo_usuario='admin')
        Usuario.objects.filter(preservados).update(empresa=None)
        # As permissões da aplicação usam tipo_usuario, além do flag do Django.
        Usuario.objects.filter(is_superuser=True).update(tipo_usuario='admin')
        print('[CLEAN] Substituindo dados de demonstração...')
        for model in [Alerta, HistoricoManutencao, OrdemServico, Telemetria, TrendConfig, Sensor,
                      PlanoManutencao, EquipamentoLocalizacao, Equipamento, TipoEquipamento, PromptConfig, Empresa]:
            model.objects.all().delete()
        Usuario.objects.exclude(preservados).delete()
        _usernames_usados.clear()
        resultado = None if clean_only else _popular(
            num_empresas, equip_por_empresa, dias_historico, funcionarios_por_empresa, rng_seed)
    # Sucesso só é anunciado após o commit.
    if clean_only:
        print('[DONE] Limpeza concluída. Contas administrativas preservadas, sem empresa vinculada.')
        return
    print(f'\n[DONE] Base validada e salva em {time.monotonic() - inicio:.2f}s. Seed={rng_seed}')
    print(f'Administrador: {resultado["admin"]} | senha: {"admin" if resultado["admin_criado"] else "preservada (não redefinida)"}')
    for empresa in resultado['empresas']:
        print(f'\nEmpresa {empresa["id"]}: {empresa["nome"]}')
        print(f'  Gestor: {empresa["gestor"]} | Técnicos: {", ".join(empresa["tecnicos"])} | senha: 123')
        for eq in empresa['equipamentos']:
            print(f'  Equipamento {eq["id"]}: {eq["nome"]} | {eq["status"]}')
            for sensor in eq['sensores']:
                print(f'    Sensor {sensor["id"]}: {sensor["tipo"]} | {sensor["perfil"]}')
        eq = empresa['equipamentos'][0]
        print(f'  Horímetro: equipamento {eq["id"]}, plano {eq["plano_id"]}: '
              f'{eq["horimetro"]:g} h -> disparo em {eq["proximo_disparo"]:g} h')
        print(f'  Ao vivo: python scripts/simulador_realtime.py --equipamento {eq["id"]} --cenario oscilacao --seed {rng_seed}')
    print(f'\nTelemetria: {Telemetria.objects.count()} | OS: {OrdemServico.objects.count()} | Alertas: {Alerta.objects.count()}')
    return resultado


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresas', type=int, default=2)
    parser.add_argument('--equipamentos', type=int, default=10, help='Por empresa; mínimo 3 para cobertura completa')
    parser.add_argument('--funcionarios', type=int, default=None, help='Total por empresa; padrão 4 (1 gestor e 3 técnicos)')
    parser.add_argument('--days', type=int, default=120, help='Dias de histórico')
    parser.add_argument('--seed', type=int, default=42, help='Semente reproduzível de dados sintéticos')
    parser.add_argument('--clean-only', action='store_true', help='Apaga dados e preserva contas administrativas')
    parser.add_argument('--check', action='store_true', help='Valida parâmetros e migrações sem alterar dados')
    args = parser.parse_args(argv)
    try:
        validar_parametros(args.empresas, args.equipamentos, args.days, args.funcionarios)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        run_seed(args.empresas, args.equipamentos, args.days, args.clean_only,
                 args.funcionarios, args.seed, args.check)
    except KeyboardInterrupt:
        print('\n[ERROR] Interrompido. A limpeza/geração é revertida se o commit ainda não ocorreu; '
              'o marcador [DONE] indica que a base já foi salva.', file=sys.stderr)
        return 130
    except Exception:
        import traceback
        print('\n[ERROR] Falha no seed. Erros durante a limpeza/geração revertem a transação. '
              'Confira o diagnóstico abaixo.', file=sys.stderr)
        traceback.print_exc()
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
