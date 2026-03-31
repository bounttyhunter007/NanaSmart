from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empresa, Usuario

# 1. Registramos a tabela Empresa de forma simples
admin.site.register(Empresa)

# 2. Configuração Sênior para o nosso Usuário Customizado
class CustomUserAdmin(UserAdmin):
    model = Usuario
    # Pegamos o layout padrão do Django e adicionamos uma nova seção 
    # com os nossos campos customizados para aparecerem na tela.
    fieldsets = UserAdmin.fieldsets + (
        ('Informações da Empresa e Cargo', {'fields': ('empresa', 'tipo_usuario', 'cargo', 'telefone')}),
    )

admin.site.register(Usuario, CustomUserAdmin)