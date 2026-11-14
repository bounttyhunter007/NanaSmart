from django_filters import rest_framework as filters
from .models import Alerta
from django.db.models import Case, When, IntegerField


def ordenar_historico(queryset):
    """Gravidade antes da paginação; aberturas recentes desempatarão cada nível."""
    return queryset.alias(gravidade_historico=Case(
        When(nivel='critico', then=0), When(nivel='medio', then=1),
        When(nivel='baixo', then=2), default=3, output_field=IntegerField(),
    )).order_by('gravidade_historico', '-data_alerta', '-pk')


class AlertaFilter(filters.FilterSet):
    data_de = filters.IsoDateTimeFilter(field_name='data_alerta', lookup_expr='gte')
    data_ate = filters.IsoDateTimeFilter(field_name='data_alerta', lookup_expr='lte')
    empresa = filters.NumberFilter(field_name='equipamento__empresa')
    search = filters.CharFilter(method='search_text')
    setor = filters.CharFilter(field_name='equipamento__localizacao__setor')
    ordenacao = filters.ChoiceFilter(
        choices=[('gravidade', 'Gravidade'), ('recentes', 'Mais recentes')],
        method='filter_order',
    )

    def filter_order(self, queryset, name, value):
        return queryset.order_by('-data_alerta', '-pk') if value == 'recentes' else ordenar_historico(queryset)

    class Meta:
        model = Alerta
        fields = ['equipamento', 'equipamento__empresa', 'empresa', 'sensor', 'origem',
                  'nivel', 'status', 'data_de', 'data_ate', 'search']

    def search_text(self, queryset, name, value):
        from django.db.models import Q
        for term in value.split():
            queryset = queryset.filter(Q(tipo_alerta__icontains=term) | Q(descricao__icontains=term))
        return queryset
