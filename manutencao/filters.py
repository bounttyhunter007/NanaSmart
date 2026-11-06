from django_filters import rest_framework as df_filters
from .models import OrdemServico


class OrdemServicoFilter(df_filters.FilterSet):
    empresa = df_filters.NumberFilter(field_name='equipamento__empresa')
    prioridade = df_filters.ChoiceFilter(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('a_definir', 'A definir')], method='filter_priority')
    abertas = df_filters.BooleanFilter(method='filter_open')
    responsavel_escopo = df_filters.ChoiceFilter(choices=[('minhas', 'Minhas'), ('livres', 'Livres')], method='filter_owner')
    setor = df_filters.CharFilter(field_name='equipamento__localizacao__setor')

    class Meta:
        model = OrdemServico
        fields = ['status', 'prioridade', 'equipamento', 'equipamento__empresa', 'responsavel', 'tipo_os', 'abertas', 'responsavel_escopo', 'setor', 'empresa']

    def filter_priority(self, qs, name, value):
        return qs.filter(prioridade__isnull=True) if value == 'a_definir' else qs.filter(prioridade=value)

    def filter_open(self, qs, name, value):
        return qs.filter(status__in=['pendente', 'andamento']) if value else qs

    def filter_owner(self, qs, name, value):
        return qs.filter(responsavel=self.request.user) if value == 'minhas' else qs.filter(responsavel__isnull=True)

