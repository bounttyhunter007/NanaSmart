from django.contrib import admin
from .models import OrdemServico, HistoricoManutencao

@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'equipamento', 'status', 'prioridade', 'responsavel')
    list_filter = ('status', 'prioridade', 'equipamento')
    search_fields = ('titulo', 'equipamento__nome')

@admin.register(HistoricoManutencao)
class HistoricoManutencaoAdmin(admin.ModelAdmin):
    list_display = ('ordem_servico', 'data_execucao', 'custo_pecas', 'custo_maao_de_obra', 'custo_total')
    list_filter = ('data_execucao',)
    search_fields = ('ordem_servico__titulo', 'ordem_servico__equipamento__nome')
