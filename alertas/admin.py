from django.contrib import admin
from .models import Alerta

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo_alerta', 'equipamento', 'sensor', 'origem', 'nivel', 'status', 'data_alerta')
    list_filter = ('origem', 'nivel', 'status', 'equipamento')
    search_fields = ('tipo_alerta', 'equipamento__nome', 'evento_chave')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]
