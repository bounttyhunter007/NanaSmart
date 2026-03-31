from django.contrib import admin
from .models import Equipamento, EquipamentoLocalizacao

@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'numero_serie', 'status', 'empresa')
    list_filter = ('status', 'tipo', 'empresa')
    search_fields = ('nome', 'numero_serie')

@admin.register(EquipamentoLocalizacao)
class EquipamentoLocalizacaoAdmin(admin.ModelAdmin):
    list_display = ('equipamento', 'setor')
    list_filter = ('setor',)
    search_fields = ('equipamento__nome', 'setor')
