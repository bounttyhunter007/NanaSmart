from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empresa, Usuario

# 1. Registramos a tabela Empresa de forma simples
admin.site.register(Empresa)
class CustomUserAdmin(UserAdmin):
    model = Usuario
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informações da Empresa e Cargo', {'fields': ('empresa', 'tipo_usuario', 'cargo', 'telefone')}),
    )

admin.site.register(Usuario, CustomUserAdmin)