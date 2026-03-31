from django.contrib import admin
from .models import Alerta

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo_alerta', 'equipamento', 'nivel', 'status', 'data_alerta')
    list_filter = ('nivel', 'status', 'equipamento')
    search_fields = ('tipo_alerta', 'equipamento__nome')
