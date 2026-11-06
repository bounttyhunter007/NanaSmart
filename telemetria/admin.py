from django.contrib import admin
from .models import Sensor, Telemetria, TrendConfig

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'equipamento', 'unidade_medida', 'ativo')
    list_filter = ('tipo', 'ativo', 'equipamento')
    search_fields = ('equipamento__nome', 'tipo')

@admin.register(Telemetria)
class TelemetriaAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor', 'timestamp', 'get_equipamento')
    list_filter = ('sensor__tipo', 'timestamp')
    search_fields = ('sensor__equipamento__nome',)

    def get_equipamento(self, obj):
        return obj.sensor.equipamento.nome
    get_equipamento.short_description = 'Equipamento'

@admin.register(TrendConfig)
class TrendConfigAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'periodo_horas', 'minimo_leituras', 'num_leituras', 'direcao_alerta', 'sensibilidade', 'ativo')
    list_filter = ('direcao_alerta', 'sensibilidade', 'ativo')
