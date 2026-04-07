import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone
from faker import Faker

# Configuração do Ambiente Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

# Importação dos Models (Após o setup)
from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from telemetria.models import Sensor, Telemetria
from manutencao.models import OrdemServico, HistoricoManutencao
from alertas.models import Alerta

fake = Faker('pt_BR')

def clear_database():
    print("\n🧹 Limpando o banco de dados...")
    Alerta.objects.all().delete()
    HistoricoManutencao.objects.all().delete()
    OrdemServico.objects.all().delete()
    Telemetria.objects.all().delete()
    Sensor.objects.all().delete()
    EquipamentoLocalizacao.objects.all().delete()
    Equipamento.objects.all().delete()
    Usuario.objects.filter(is_superuser=False).delete()
    Empresa.objects.all().delete()
    print("✅ Banco limpo com sucesso!")

def seed_data(apps_to_seed=None):
    if apps_to_seed is None:
        apps_to_seed = ['accounts', 'ativos', 'telemetria', 'manutencao', 'alertas']

    # 1. Accounts
    empresas = []
    if 'accounts' in apps_to_seed:
        print("\n🏢 Populando Empresas e Usuários...")
        for _ in range(5):
            empresa = Empresa.objects.create(
                nome=fake.company(),
                cnpj=fake.cnpj(),
                email=fake.company_email(),
                telefone=fake.phone_number(),
                endereco=fake.address()
            )
            empresas.append(empresa)
            
            # Criar alguns usuários para cada empresa
            for _ in range(3):
                first_name = fake.first_name()
                last_name = fake.last_name()
                user_type = random.choice(['tecnico', 'gestor'])
                
                # Username e Email coerentes
                base_name = f"{first_name.lower()}.{last_name.lower()}".replace(' ', '')
                username = f"{base_name}{random.randint(10, 99)}"
                email = f"{base_name}@{fake.free_email_domain()}"
                
                # Cargos Profissionais
                if user_type == 'tecnico':
                    cargo = random.choice([
                        'Eletricista Industrial', 'Mecânico de Manutenção', 
                        'Técnico em Automação', 'Operador de Utilidades',
                        'Mecatrônico Sênior', 'Lubrificador Industrial'
                    ])
                else:
                    cargo = random.choice([
                        'Gerente de Manutenção', 'Supervisor de Produção', 
                        'Planejador de Manutenção (PCM)', 'Engenheiro de Confiabilidade',
                        'Coordenador de Facilities'
                    ])

                Usuario.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password='senha_padrao_123',
                    empresa=empresa,
                    tipo_usuario=user_type,
                    cargo=cargo
                )
    else:
        empresas = list(Empresa.objects.all())

    if not empresas:
        print("⚠️ Nenhuma empresa encontrada. Por favor, popule 'accounts' primeiro.")
        return

    # 2. Ativos
    equipamentos = []
    if 'ativos' in apps_to_seed:
        print("⚙️ Populando Equipamentos...")
        tipos_equipamento = [
            ('Motor Elétrico', ['temperatura', 'vibracao', 'corrente']),
            ('Bomba Hidráulica', ['pressao', 'vibracao', 'temperatura']),
            ('Compressor', ['pressao', 'temperatura', 'vibracao']),
            ('Painel Elétrico', ['corrente', 'temperatura']),
            ('Esteira Transportadora', ['vibracao', 'corrente']),
            ('Robô de Solda', ['vibracao', 'corrente', 'temperatura']),
            ('Tanque de Resfriamento', ['temperatura', 'umidade', 'pressao'])
        ]
        
        for emp in empresas:
            num_equip = random.randint(10, 40)
            for _ in range(num_equip):
                nome_tipo, sensores_alvo = random.choice(tipos_equipamento)
                equip = Equipamento.objects.create(
                    empresa=emp,
                    nome=f"{nome_tipo} {fake.word().capitalize()}",
                    tipo=nome_tipo,
                    fabricante=fake.company(),
                    modelo=f"MOD-{random.randint(100, 999)}",
                    numero_serie=fake.unique.bothify(text='??-########-##').upper(),
                    data_instalacao=fake.date_between(start_date='-5y', end_date='today'),
                    status='ativo'
                )
                EquipamentoLocalizacao.objects.create(
                    equipamento=equip,
                    setor=random.choice(['Produção', 'Logística', 'Manutenção', 'Utilidades'])
                )
                equipamentos.append((equip, sensores_alvo))
    else:
        # Tenta mapear equipamentos existentes (simplificado)
        for eq in Equipamento.objects.all():
            sensores_alvo = ['temperatura', 'vibracao'] # default
            equipamentos.append((eq, sensores_alvo))

    # 3. Telemetria
    if 'telemetria' in apps_to_seed:
        print("📡 Populando Sensores e Telemetria (isso pode demorar)...")
        config_sensores = { # (Unidade, Min Normal, Max Normal)
            'temperatura': ('°C', 40.0, 75.0),
            'vibracao': ('mm/s', 0.5, 4.5),
            'pressao': ('bar', 2.0, 8.0),
            'corrente': ('A', 10.0, 35.0),
            'umidade': ('%', 30.0, 60.0)
        }
        
        for eq, sensores_alvo in equipamentos:
            for s_tipo in sensores_alvo:
                unidade, min_val, max_val = config_sensores.get(s_tipo, ('un', 10.0, 50.0))
                sensor = Sensor.objects.create(
                    equipamento=eq, tipo_sensor=s_tipo, unidade_medida=unidade,
                    descricao=f"Sensor de {s_tipo} do {eq.nome}", ativo=True
                )
                
                start_date = timezone.now() - timedelta(days=7)
                leituras = []
                for i in range(24 * 7): # 1 leitura/hora
                    valor = random.uniform(min_val, max_val)
                    if random.random() > 0.97: # 3% chance de anomalia
                        valor *= random.uniform(1.2, 1.6)
                    
                    leituras.append(Telemetria(sensor=sensor, valor=round(valor, 2), data_hora=start_date + timedelta(hours=i)))
                Telemetria.objects.bulk_create(leituras)

    # 4. Manutenção
    if 'manutencao' in apps_to_seed:
        print("🔧 Populando Ordens de Serviço...")
        usuarios_tecnicos = list(Usuario.objects.filter(tipo_usuario='tecnico'))
        if usuarios_tecnicos:
            for eq, _ in random.sample(equipamentos, min(len(equipamentos), 30)):
                status = random.choice(['pendente', 'andamento', 'concluida'])
                os = OrdemServico.objects.create(
                    equipamento=eq, responsavel=random.choice(usuarios_tecnicos),
                    titulo=f"Manutenção Corretiva: {fake.catch_phrase()}",
                    descricao=f"Verificação de falha: {fake.text(max_nb_chars=100)}",
                    status=status, prioridade=random.choice(['baixa', 'media', 'alta', 'urgente']),
                    data_abertura=fake.date_time_between(start_date='-30d', end_date='-5d', tzinfo=timezone.get_current_timezone())
                )
                if status == 'concluida':
                    os.data_conclusao = os.data_abertura + timedelta(hours=random.randint(2, 72))
                    os.save()
                    HistoricoManutencao.objects.create(
                        ordem_servico=os, descricao_servico=f"Reparo realizado: {fake.sentence()}",
                        data_execucao=os.data_conclusao.date(),
                        custo_pecas=round(random.uniform(50, 1500), 2),
                        custo_maao_de_obra=round(random.uniform(200, 2000), 2)
                    )

    # 5. Alertas
    if 'alertas' in apps_to_seed:
        print("🚨 Populando Alertas Inteligentes...")
        for eq, sensores_alvo in random.sample(equipamentos, min(len(equipamentos), 20)):
            s_tipo = random.choice(sensores_alvo) if sensores_alvo else 'Geral'
            Alerta.objects.create(
                equipamento=eq,
                tipo_alerta=f"Anomalia: {s_tipo.capitalize()}",
                nivel=random.choice(['medio', 'critico']),
                descricao=f"Desvio nos padrões normais de {s_tipo}. Verifique os gráficos de telemetria.",
                status=random.choice(['ativo', 'resolvido', 'ignorado'])
            )

    print("\n✨ População concluída com sucesso!")

def main_menu():
    print("="*40)
    print("🚀 SCRIPT DE POPULAÇÃO INTELIGENTE")
    print("="*40)
    print("1. Limpar Banco de Dados")
    print("2. Popular TUDO (~200 ativos, 7 dias de telemetria)")
    print("3. Popular Somente Contas (Empresas/Usuários)")
    print("4. Popular Ativos (Requer Contas)")
    print("5. Popular Telemetria (Requer Ativos)")
    print("6. Sair")
    print("="*40)
    
    escolha = input("Escolha uma opção: ")
    
    if escolha == '1':
        clear_database()
    elif escolha == '2':
        seed_data()
    elif escolha == '3':
        seed_data(['accounts'])
    elif escolha == '4':
        seed_data(['ativos'])
    elif escolha == '5':
        seed_data(['telemetria'])
    elif escolha == '6':
        print("Até logo!")
        sys.exit()
    else:
        print("Opção inválida.")

if __name__ == "__main__":
    main_menu()
