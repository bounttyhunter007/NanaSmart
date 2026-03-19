from django.core.management.base import BaseCommand
from accounts.models import Empresa
from faker import Faker

class Command(BaseCommand):
    help = 'Popula a base de dados com empresas aleatórias usando o Faker'

    def handle(self, *args, **kwargs):
        self.stdout.write("A iniciar a criação de empresas aleatórias...")

        # Instanciamos o Faker configurado para dados do Brasil
        fake = Faker('pt_BR')
        
        # Vamos criar 50 empresas de uma só vez!
        for _ in range(50):
            nome_empresa = fake.company()
            cnpj_aleatorio = fake.cnpj() # Gera um CNPJ com a formatação correta
            
            # O get_or_create tenta buscar; se não achar, ele cria.
            empresa, criada = Empresa.objects.get_or_create(
                cnpj=cnpj_aleatorio,
                defaults={
                    'nome': nome_empresa,
                    'email': fake.company_email(),
                    'telefone': fake.phone_number(),
                    'endereco': fake.address() # Gera uma morada completa aleatória
                }
            )

            if criada:
                self.stdout.write(self.style.SUCCESS(f'Empresa "{nome_empresa}" criada com sucesso!'))
            else:
                self.stdout.write(self.style.WARNING(f'Empresa "{nome_empresa}" já existia.'))

        self.stdout.write(self.style.SUCCESS("Base de dados populada com 50 novas empresas!"))