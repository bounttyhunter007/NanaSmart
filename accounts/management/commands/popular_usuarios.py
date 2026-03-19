from django.core.management.base import BaseCommand
from accounts.models import Empresa, Usuario
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Popula o banco de dados com usuários aleatórios usando o Faker'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando a criação de usuários aleatórios...")

        fake = Faker('pt_BR')
        
        # 1. Buscamos todas as empresas cadastradas no banco
        empresas = list(Empresa.objects.all())
        
        # Se não houver empresas, avisamos o desenvolvedor para rodar o outro script primeiro
        if not empresas:
            self.stdout.write(self.style.ERROR("Nenhuma empresa encontrada! Rode 'python manage.py popular_banco' primeiro."))
            return

        tipos_usuario = ['admin', 'gestor', 'tecnico']
        cargos = ['Engenheiro Mecânico', 'Eletricista Sênior', 'Técnico de Manutenção', 'Gerente de Planta', 'Analista de Vibração']

        # Vamos criar 50 usuários
        for _ in range(50):
            nome = fake.first_name()
            sobrenome = fake.last_name()
            
            # Cria um username único no formato: nome.sobrenome.numero
            username = f"{nome.lower()}.{sobrenome.lower()}.{random.randint(100, 999)}"
            email = fake.email()
            telefone = fake.cellphone_number()
            
            # Sorteia uma empresa, um tipo e um cargo
            empresa_escolhida = random.choice(empresas)
            tipo_escolhido = random.choice(tipos_usuario)
            cargo_escolhido = random.choice(cargos)

            # Verifica se o username já existe por garantia
            if not Usuario.objects.filter(username=username).exists():
                
                # ATENÇÃO SÊNIOR: Usamos create_user (e não objects.create) 
                # para que o Django criptografe a senha automaticamente!
                Usuario.objects.create_user(
                    username=username,
                    email=email,
                    password='senhapadrao123', # Senha padrão para você conseguir logar com qualquer um depois
                    first_name=nome,
                    last_name=sobrenome,
                    empresa=empresa_escolhida,
                    tipo_usuario=tipo_escolhido,
                    cargo=cargo_escolhido,
                    telefone=telefone
                )
                self.stdout.write(self.style.SUCCESS(f'Usuário "{username}" criado com sucesso!'))
            else:
                self.stdout.write(self.style.WARNING(f'Usuário "{username}" já existia.'))

        self.stdout.write(self.style.SUCCESS("Banco de dados populado com 50 novos usuários!"))