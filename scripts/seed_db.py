"""
Script de seed — popula o banco com dados realistas para desenvolvimento e testes.

Uso:
    python scripts/seed_db.py

O que faz:
    1. Limpa o banco (preserva o superusuário admin)
    2. Aplica migrações pendentes
    3. Garante o superusuário admin/admin123
    4. Cria 3 empresas, cada uma com 1 gestor e 4 técnicos
    5. Cria 15-25 equipamentos por empresa com sensores e 90 dias de histórico de telemetria
    6. Cria OS históricas e registros de histórico de manutenção
    7. Injeta alertas variados (baixo/medio/critico) por equipamento
"""
import os
import sys
import django
import random
import re
from datetime import timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from faker import Faker
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico, HistoricoManutencao
from alertas.models import Alerta

fake = Faker('pt_BR')

# ---------------------------------------------------------------------------
# Dados predefinidos
# ---------------------------------------------------------------------------
FABRICANTES = [
    'WEG', 'Siemens', 'ABB', 'Schneider Electric',
    'Caterpillar', 'Bosch Rexroth', 'Atlas Copco',
    'SEW-Eurodrive', 'Danfoss'
]

# Chave do tipo DEVE bater com config_alertas.LIMITES_ALERTA
TIPOS_EQUIP = [
    ('Motor Elétrico',     ['temperatura', 'vibracao', 'corrente']),
    ('Bomba Hidráulica',   ['pressao', 'vibracao', 'temperatura']),
    ('Compressor',         ['pressao', 'temperatura', 'vibracao']),   # era "Compressor de Ar" — corrigido
    ('Painel Elétrico',    ['corrente', 'temperatura']),
    ('Prensa Hidráulica',  ['vibracao', 'pressao']),
    ('Inversor de Frequência', ['corrente', 'temperatura']),
    ('Redutor de Velocidade',  ['vibracao', 'temperatura']),
]

TIPOS_MANUTENCAO = [
    ('Corretiva Crítica',   'Intervenção imediata para correção de quebra funcional. Substituição de componentes danificados.'),
    ('Preventiva Mensal',   'Manutenção programada conforme plano diretor. Limpeza, lubrificação e reapertos.'),
    ('Calibração',          'Ajuste fino de sensores de campo e verificação de loops de controle.'),
    ('Análise Preditiva',   'Coleta de dados de vibração e análise termográfica para detecção precoce de falhas.'),
    ('Inspeção de Segurança', 'Validação de dispositivos de segurança (NR-12) e integridade mecânica.'),
]

SETORES = [
    'Linha de Montagem A', 'Utilidades', 'Usinagem Sênior',
    'Logística Automação', 'Célula de Solda', 'Estação de Pintura',
]

# Faixas de valores normais para cada tipo de sensor (unidade, min_normal, max_normal)
CONFIG_SENSORES = {
    'temperatura': ('°C',   35.0, 70.0),
    'vibracao':    ('mm/s',  0.2,  5.0),
    'pressao':     ('bar',   1.5,  9.0),
    'corrente':    ('A',     5.0, 45.0),
    'umidade':     ('%',    30.0, 75.0),
}

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
_usernames_usados = set()

def gerar_username_unico(nome):
    """Gera um username único no formato joao.silva, com sufixo numérico se necessário."""
    nome = nome.lower()
    nome = re.sub(r'[^\w\s]', '', nome)
    partes = nome.split()
    base = f"{partes[0]}.{partes[1]}" if len(partes) >= 2 else partes[0]
    username = base
    contador = 1
    while username in _usernames_usados or Usuario.objects.filter(username=username).exists():
        username = f"{base}{contador}"
        contador += 1
    _usernames_usados.add(username)
    return username


def clear_database():
    print('\n--- Limpando banco de dados ---')
    Alerta.objects.all().delete()
    HistoricoManutencao.objects.all().delete()
    OrdemServico.objects.all().delete()
    Telemetria.objects.all().delete()
    Sensor.objects.all().delete()
    EquipamentoLocalizacao.objects.all().delete()
    Equipamento.objects.all().delete()
    Usuario.objects.filter(is_superuser=False).delete()
    Empresa.objects.all().delete()
    _usernames_usados.clear()
    print('Banco limpo.')


def garantir_admin():
    print('\n--- Criando/resetando superusuário admin ---')
    call_command('migrate', verbosity=0)
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(
            username='admin', email='admin@admin.com', password='admin123',
            tipo_usuario='admin'
        )
        print("Superusuário 'admin' criado.")
    else:
        u = Usuario.objects.get(username='admin')
        u.set_password('admin123')
        u.is_superuser = True
        u.is_staff = True
        u.tipo_usuario = 'admin'
        u.save()
        print("Superusuário 'admin' resetado.")


def seed():
    now = timezone.now()
    inicio_historico = now - timedelta(days=90)

    # ------------------------------------------------------------------
    # Empresas e Usuários
    # ------------------------------------------------------------------
    print('\n--- Criando empresas e usuários ---')
    nomes_empresas = ['Indústria Mecânica Brasileira', 'TecnoLogística S.A.', 'AutoPeças Global']
    empresas = []

    for nome_emp in nomes_empresas:
        emp = Empresa.objects.create(
            nome=nome_emp,
            cnpj=fake.cnpj(),
            email=f"contato@{re.sub(r'[^a-z]', '', nome_emp.lower())}.com.br",
            telefone=fake.phone_number(),
            endereco=fake.address(),
        )
        empresas.append(emp)

        gestor_nome = fake.name()
        Usuario.objects.create_user(
            username=gerar_username_unico(gestor_nome),
            email=fake.email(), password='123',
            empresa=emp, tipo_usuario='gestor',
            first_name=gestor_nome.split()[0],
            last_name=' '.join(gestor_nome.split()[1:]),
            cargo='Gerente de Manutenção Industrial',
        )

        cargos_tecnicos = [
            'Técnico Mecânico Sênior', 'Eletricista de Manutenção',
            'Especialista em Automação', 'Lubrificador Industrial',
        ]
        for cargo in cargos_tecnicos:
            tec_nome = fake.name()
            Usuario.objects.create_user(
                username=gerar_username_unico(tec_nome),
                email=fake.email(), password='123',
                empresa=emp, tipo_usuario='tecnico',
                first_name=tec_nome.split()[0],
                last_name=' '.join(tec_nome.split()[1:]),
                cargo=cargo,
            )

    print(f'  {Usuario.objects.filter(is_superuser=False).count()} usuários criados.')

    # ------------------------------------------------------------------
    # Equipamentos e Localização
    # ------------------------------------------------------------------
    print('\n--- Criando equipamentos ---')
    todos_equipamentos = []

    status_prob_map = [
        ('ativo',      0.83),
        ('manutencao', 0.10),
        ('inativo',    0.07),
    ]
    estados, pesos = zip(*status_prob_map)

    for emp in empresas:
        for _ in range(random.randint(15, 20)):
            tipo_nome, sensores_list = random.choice(TIPOS_EQUIP)
            status = random.choices(estados, weights=pesos)[0]

            eq = Equipamento.objects.create(
                empresa=emp,
                nome=f'{tipo_nome} {random.randint(100, 999)}',
                tipo=tipo_nome,
                fabricante=random.choice(FABRICANTES),
                modelo=f'SERIE-{random.choice(["X", "Z", "W"])}{random.randint(10, 99)}',
                numero_serie=fake.unique.bothify(text='??-########-##').upper(),
                data_instalacao=fake.date_between(start_date='-3y', end_date='-1y'),
                status=status,
            )
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=random.choice(SETORES))
            todos_equipamentos.append((eq, sensores_list))

    print(f'  {Equipamento.objects.count()} equipamentos criados.')

    # ------------------------------------------------------------------
    # Sensores e Telemetria (bulk_create não dispara signal — intencional aqui)
    # ------------------------------------------------------------------
    print('\n--- Gerando sensores e telemetria (90 dias) ---')
    todos_sensores = []

    for eq, sensores_list in todos_equipamentos:
        for s_tipo in sensores_list:
            unidade, min_v, max_v = CONFIG_SENSORES.get(s_tipo, ('un', 0, 100))
            sensor = Sensor.objects.create(
                equipamento=eq, tipo_sensor=s_tipo,
                unidade_medida=unidade, ativo=True,
            )
            todos_sensores.append((sensor, min_v, max_v))

            # Leituras a cada 12h durante 90 dias
            leituras = []
            for i in range(90 * 2):
                ponto = inicio_historico + timedelta(hours=i * 12)
                if ponto > now:
                    break
                valor = random.uniform(min_v, max_v)
                # 2% de chance de spike (valor elevado, mas não necessariamente alerta)
                if random.random() > 0.98:
                    valor *= random.uniform(1.1, 1.4)
                leituras.append(Telemetria(sensor=sensor, valor=round(valor, 2), data_hora=ponto))

            Telemetria.objects.bulk_create(leituras)

    print(f'  {Telemetria.objects.count()} leituras criadas.')

    # ------------------------------------------------------------------
    # Ordens de Serviço e Histórico de Manutenção
    # ------------------------------------------------------------------
    print('\n--- Criando OS e históricos ---')
    tecnicos_all = list(Usuario.objects.filter(tipo_usuario='tecnico'))
    amostra_equip = random.sample(todos_equipamentos, int(len(todos_equipamentos) * 0.65))

    for eq, _ in amostra_equip:
        tecnicos_empresa = [t for t in tecnicos_all if t.empresa == eq.empresa] or tecnicos_all
        num_os = random.randint(1, 4)
        ultimo_evento = inicio_historico

        for _ in range(num_os):
            abertura = ultimo_evento + timedelta(days=random.randint(12, 28))
            if abertura > now - timedelta(days=1):
                break

            tipo_nome, tipo_desc = random.choice(TIPOS_MANUTENCAO)
            status_os = random.choices(['concluida', 'cancelada'], weights=[0.9, 0.1])[0]

            os_obj = OrdemServico.objects.create(
                equipamento=eq,
                responsavel=random.choice(tecnicos_empresa),
                titulo=f'{tipo_nome}: {eq.nome}',
                descricao=tipo_desc,
                status=status_os,
                prioridade=random.choice(['media', 'alta', 'urgente']),
                data_abertura=abertura,
            )

            if status_os == 'concluida':
                duracao_h = random.randint(1, 16)
                conclusao = abertura + timedelta(hours=duracao_h)
                os_obj.data_conclusao = conclusao
                os_obj.save()

                HistoricoManutencao.objects.create(
                    ordem_servico=os_obj,
                    descricao_servico=(
                        f'Procedimento de {tipo_nome} executado. '
                        f'Verificado conforme padrões ISO 9001.'
                    ),
                    data_execucao=conclusao.date(),
                    custo_pecas=Decimal(str(round(random.uniform(20, 800), 2))),
                    custo_mao_de_obra=Decimal(str(round(duracao_h * random.uniform(100, 150), 2))),
                )
                ultimo_evento = conclusao
            else:
                ultimo_evento = abertura + timedelta(days=2)

    print(f'  {OrdemServico.objects.filter(status="concluida").count()} OS concluídas.')

    # ------------------------------------------------------------------
    # Alertas variados (baixo / medio / critico) por equipamento
    # Injetados diretamente (sem signal) para popular o banco historicamente
    # ------------------------------------------------------------------
    print('\n--- Injetando alertas históricos variados ---')
    niveis = ['baixo', 'medio', 'critico']
    pesos_nivel = [0.40, 0.35, 0.25]

    # ~40% dos equipamentos têm alertas históricos
    for eq, sensores_list in random.sample(todos_equipamentos, int(len(todos_equipamentos) * 0.40)):
        num_alertas = random.randint(1, 3)
        for _ in range(num_alertas):
            tipo_sensor = random.choice(sensores_list)
            nivel = random.choices(niveis, weights=pesos_nivel)[0]
            status_alerta = random.choices(
                ['ativo', 'resolvido', 'ignorado'],
                weights=[0.30, 0.55, 0.15]
            )[0]
            Alerta.objects.create(
                equipamento=eq,
                tipo_alerta=f'Alerta de {tipo_sensor.capitalize()}',
                nivel=nivel,
                descricao=(
                    f'Leitura anômala detectada no sensor de {tipo_sensor} '
                    f'do equipamento {eq.nome}. Nível: {nivel}.'
                ),
                status=status_alerta,
            )

    print(f'  {Alerta.objects.count()} alertas criados.')

    # ------------------------------------------------------------------
    # Resumo final
    # ------------------------------------------------------------------
    print('\n=== Seed concluído com sucesso! ===')
    print(f'  Empresas     : {Empresa.objects.count()}')
    print(f'  Usuários     : {Usuario.objects.filter(is_superuser=False).count()}')
    print(f'  Equipamentos : {Equipamento.objects.count()}')
    print(f'  Sensores     : {Sensor.objects.count()}')
    print(f'  Leituras     : {Telemetria.objects.count()}')
    print(f'  OS totais    : {OrdemServico.objects.count()}')
    print(f'  Alertas      : {Alerta.objects.count()}')
    print()
    print('  Credenciais:')
    print('    Admin  : admin / admin123')
    print('    Outros : <username> / 123')


if __name__ == '__main__':
    clear_database()
    garantir_admin()
    seed()
