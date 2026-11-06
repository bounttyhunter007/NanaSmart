from django.contrib import admin
from .models import OrdemServico, HistoricoManutencao

@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    readonly_fields = ('prioridade', 'prioridade_automatica', 'prioridade_manual', 'prioridade_origem',
                       'prioridade_herdada_conhecida', 'justificativa_prioridade', 'criticidade_na_abertura',
                       'justificativa_criticidade_na_abertura', 'criterios_criticidade_na_abertura')

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('equipamento',) if obj else ())
    list_display = ('id', 'titulo', 'equipamento', 'tipo_os', 'status', 'prioridade', 'responsavel')
    list_filter = ('tipo_os', 'status', 'prioridade', 'equipamento')
    search_fields = ('titulo', 'equipamento__nome')

@admin.register(HistoricoManutencao)
class HistoricoManutencaoAdmin(admin.ModelAdmin):
    list_display = ('ordem_servico', 'data_execucao', 'custo_pecas', 'custo_mao_de_obra', 'custo_total')
    list_filter = ('data_execucao',)
    search_fields = ('ordem_servico__titulo', 'ordem_servico__equipamento__nome')
