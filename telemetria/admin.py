from django.contrib import admin
from .models import Sensor, Telemetria

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('tipo_sensor', 'equipamento', 'unidade_medida', 'ativo')
    list_filter = ('tipo_sensor', 'ativo', 'equipamento')
    search_fields = ('equipamento__nome', 'tipo_sensor')

@admin.register(Telemetria)
class TelemetriaAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor', 'data_hora', 'get_equipamento')
    list_filter = ('sensor__tipo_sensor', 'data_hora')
    search_fields = ('sensor__equipamento__nome',)

    def get_equipamento(self, obj):
        return obj.sensor.equipamento.nome
    get_equipamento.short_description = 'Equipamento'
