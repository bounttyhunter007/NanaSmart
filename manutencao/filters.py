from django_filters import rest_framework as df_filters
from django.db.models import Case, IntegerField, Q, When
from .models import OrdemServico


class OrdemServicoFilter(df_filters.FilterSet):
    empresa = df_filters.NumberFilter(field_name='equipamento__empresa')
    prioridade = df_filters.ChoiceFilter(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('a_definir', 'A definir')], method='filter_priority')
    abertas = df_filters.BooleanFilter(method='filter_open')
    responsavel_escopo = df_filters.ChoiceFilter(choices=[('minhas', 'Minhas'), ('livres', 'Livres')], method='filter_owner')
    setor = df_filters.CharFilter(field_name='equipamento__localizacao__setor')
    sensor_origem = df_filters.NumberFilter(method='filter_sensor')
    historico_preditivo = df_filters.BooleanFilter(method='filter_predictive_history')

    class Meta:
        model = OrdemServico
        fields = ['status', 'prioridade', 'equipamento', 'equipamento__empresa', 'responsavel', 'tipo_os', 'abertas', 'responsavel_escopo', 'setor', 'empresa', 'sensor_origem', 'historico_preditivo']

    def filter_sensor(self, qs, name, value):
        return qs.filter(Q(sensor_origem_id=value) | Q(sensor_origem__isnull=True, alerta_origem__sensor_id=value))

    def filter_predictive_history(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(tipo_os='preditiva').annotate(
            attendance_rank=Case(When(status__in=['pendente', 'andamento'], then=0), default=1, output_field=IntegerField()),
        ).order_by('attendance_rank', '-data_abertura', '-pk')

    def filter_priority(self, qs, name, value):
        return qs.filter(prioridade__isnull=True) if value == 'a_definir' else qs.filter(prioridade=value)

    def filter_open(self, qs, name, value):
        return qs.filter(status__in=['pendente', 'andamento']) if value else qs

    def filter_owner(self, qs, name, value):
        return qs.filter(responsavel=self.request.user) if value == 'minhas' else qs.filter(responsavel__isnull=True)

