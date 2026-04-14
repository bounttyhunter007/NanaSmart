import os
import sys
import django
import random
import re
from datetime import timedelta
from django.utils import timezone
from faker import Faker

# Configuração do Ambiente Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

# Importação dos Models
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico, HistoricoManutencao
from alertas.models import Alerta

fake = Faker('pt_BR')

# Dados Predefinidos Reais
FABRICANTES = ['WEG', 'Siemens', 'ABB', 'Schneider Electric', 'Caterpillar', 'Bosch Rexroth', 'Atlas Copco', 'SEW-Eurodrive', 'Danfoss']
TIPOS_EQUIP = [
    ('Motor Elétrico', ['temperatura', 'vibracao', 'corrente']),
    ('Bomba Hidráulica', ['pressao', 'vibracao', 'temperatura']),
    ('Compressor de Ar', ['pressao', 'temperatura', 'vibracao']),
    ('Painel de Controle', ['corrente', 'temperatura']),
    ('Prensa Hidráulica', ['vibracao', 'pressao']),
    ('Inversor de Frequência', ['corrente', 'temperatura']),
    ('Redutor de Velocidade', ['vibracao', 'temperatura'])
]
TIPOS_MANUTENCAO = [
    ('Corretiva Crítica', 'Intervenção imediata para correção de quebra funcional. Substituição de componentes danificados.'),
    ('Preventiva Mensal', 'Manutenção programada conforme plano diretor. Limpeza, lubrificação e reapertos.'),
    ('Calibração de Sensores', 'Ajuste fino de sensores de campo e verificação de loops de controle.'),
    ('Análise Preditiva', 'Coleta de dados de vibração e análise termográfica para detecção precoce de falhas.'),
    ('Inspeção de Segurança', 'Validar dispositivos de segurança (NR-12) e integridade mecânica.')
]
SETORES = ['Linha de Montagem A', 'Utilidades', 'Usinagem Sênior', 'Logística Automação', 'Célula de Solda', 'Estação de Pintura']

def normalize_username(name):
    # Transforma "João Silva" em "joao.silva"
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return parts[0]

def clear_database():
    print("\n🧹 Limpando o banco de dados para população premium...")
    Alerta.objects.all().delete()
    HistoricoManutencao.objects.all().delete()
    OrdemServico.objects.all().delete()
    Telemetria.objects.all().delete()
    Sensor.objects.all().delete()
    EquipamentoLocalizacao.objects.all().delete()
    Equipamento.objects.all().delete()
    Usuario.objects.filter(is_superuser=False).delete()
    Empresa.objects.all().delete()
    print("✅ Banco limpo!")

def seed_premium():
    now = timezone.now()
    start_history = now - timedelta(days=90)
    
    print("\n🏢 Criando Entorno Corporativo...")
    empresas = []
    nomes_empresas = ["Indústria Mecânica Brasileira", "TecnoLogística S.A.", "AutoPeças Global", "Alimentos Estrela", "Energia Pura Ltda"]
    
    for nome_emp in nomes_empresas[:3]:
        emp = Empresa.objects.create(
            nome=nome_emp,
            cnpj=fake.cnpj(),
            email=f"contato@{nome_emp.lower().replace(' ', '')}.com.br",
            telefone=fake.phone_number(),
            endereco=fake.address()
        )
        empresas.append(emp)
        
        # Gestor
        gestor_name = fake.name()
        Usuario.objects.create_user(
            username=normalize_username(gestor_name), email=fake.email(), password="123",
            empresa=emp, tipo_usuario='gestor', first_name=gestor_name.split()[0], last_name=" ".join(gestor_name.split()[1:]),
            cargo="Gerente de Manutenção Industrial"
        )
        
        # Técnicos
        for _ in range(4):
            tec_name = fake.name()
            Usuario.objects.create_user(
                username=normalize_username(tec_name), email=fake.email(), password="123",
                empresa=emp, tipo_usuario='tecnico', first_name=tec_name.split()[0], last_name=" ".join(tec_name.split()[1:]),
                cargo=random.choice(["Técnico Mecânico Sênior", "Eletricista de Manutenção", "Especialista em Automação", "Lubrificador Industrial"])
            )

    print("⚙️ Gerando Ativos com Status Variados...")
    todos_equipamentos = []
    for emp in empresas:
        num_equip = random.randint(15, 25)
        for _ in range(num_equip):
            nome_tipo, sensores = random.choice(TIPOS_EQUIP)
            status_prob = random.random()
            if status_prob > 0.92: status = 'inativo'
            elif status_prob > 0.85: status = 'manutencao'
            else: status = 'ativo'
            
            eq = Equipamento.objects.create(
                empresa=emp,
                nome=f"{nome_tipo} {random.randint(100, 999)}",
                tipo=nome_tipo,
                fabricante=random.choice(FABRICANTES),
                modelo=f"SERIE-{random.choice(['X', 'Z', 'W'])}{random.randint(10, 99)}",
                numero_serie=fake.unique.bothify(text='??-########-##').upper(),
                data_instalacao=fake.date_between(start_date='-3y', end_date='-1y'),
                status=status
            )
            EquipamentoLocalizacao.objects.create(equipamento=eq, setor=random.choice(SETORES))
            todos_equipamentos.append((eq, sensores))

    print("📡 Gerando Telemetria (90 dias)...")
    config_sensores = {
        'temperatura': ('°C', 35, 80), 'vibracao': ('mm/s', 0.2, 5.0),
        'pressao': ('bar', 1.5, 9.0), 'corrente': ('A', 5, 45)
    }
    
    for eq, sensores_list in todos_equipamentos:
        for s_tipo in sensores_list:
            unidade, min_v, max_v = config_sensores.get(s_tipo, ('un', 0, 100))
            sensor = Sensor.objects.create(equipamento=eq, tipo_sensor=s_tipo, unidade_medida=unidade, ativo=True)
            
            leituras = []
            for i in range(90 * 2): # Amostra a cada 12 horas para manter o banco leve mas com histórico longo
                data_ponto = start_history + timedelta(hours=i*12)
                if data_ponto > now: break
                valor = random.uniform(min_v, max_v)
                if random.random() > 0.98: valor *= 1.3
                leituras.append(Telemetria(sensor=sensor, valor=round(valor, 2), data_hora=data_ponto))
            Telemetria.objects.bulk_create(leituras)

    print("🔧 Construindo Histórico Humano (MTBF/MTTR Logic)...")
    tecnicos_all = list(Usuario.objects.filter(tipo_usuario='tecnico'))
    
    for eq, _ in random.sample(todos_equipamentos, int(len(todos_equipamentos)*0.6)):
        num_ev = random.randint(1, 4)
        last_date = start_history
        tecnicos_empresa = [t for t in tecnicos_all if t.empresa == eq.empresa]
        if not tecnicos_empresa: tecnicos_empresa = tecnicos_all
        
        for _ in range(num_ev):
            abertura = last_date + timedelta(days=random.randint(12, 28))
            if abertura > now - timedelta(days=1): break
            
            tipo_nome, tipo_desc = random.choice(TIPOS_MANUTENCAO)
            status_os = random.choices(['concluida', 'cancelada'], weights=[0.9, 0.1])[0]
            
            os = OrdemServico.objects.create(
                equipamento=eq, responsavel=random.choice(tecnicos_empresa),
                titulo=f"{tipo_nome}: {eq.nome}", 
                descricao=tipo_desc,
                status=status_os, 
                prioridade=random.choice(['media', 'alta', 'urgente']),
                data_abertura=abertura
            )
            
            if status_os == 'concluida':
                duration_h = random.randint(1, 12)
                conclusao = abertura + timedelta(hours=duration_h)
                os.data_conclusao = conclusao
                os.save()
                
                HistoricoManutencao.objects.create(
                    ordem_servico=os, 
                    descricao_servico=f"Procedimento de {tipo_nome} executado sem intercorrências. Verificado conforme padrões ISO 9001.",
                    data_execucao=conclusao.date(), 
                    custo_pecas=random.uniform(20, 800), 
                    custo_mao_de_obra=duration_h * 120
                )
                last_date = conclusao
            else:
                last_date = abertura + timedelta(days=2)

    print("\n✨ População Humanizada Concluída!")
    print(f"Total de Usuários: {Usuario.objects.count()}")
    print(f"Total de O.S Históricas: {OrdemServico.objects.filter(status='concluida').count()}")

if __name__ == "__main__":
    clear_database()
    seed_premium()
