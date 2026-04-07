import os
import sys
import django

# Django setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import Usuario as User
from scripts.seed_db import seed_data, clear_database
from django.core.management import call_command

def automate():
    print("🚀 Iniciando automação de população...")
    
    print("📦 Aplicando migrações (se houver)...")
    call_command('migrate', verbosity=0)

    # 1. Limpar banco
    clear_database()
    
    # 2. Popular Tudo
    seed_data()
    
    # 3. Garantir Superusuário admin/admin123
    print("\n👑 Garantindo superusuário admin...")
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✅ Superusuário 'admin' criado com sucesso!")
    else:
        u = User.objects.get(username='admin')
        u.set_password('admin123')
        u.is_superuser = True
        u.is_staff = True
        u.save()
        print("✅ Superusuário 'admin' já existia, senha resetada para 'admin123'!")

    print("\n✨ Automação concluída!")

if __name__ == "__main__":
    automate()
