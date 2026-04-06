from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as df_filters
from .models import OrdemServico, HistoricoManutencao
from .serializers import OrdemServicoSerializer, HistoricoManutencaoSerializer


class HistoricoManutencaoFilter(df_filters.FilterSet):
    """
    Filtro de data por intervalo — use:
      ?data_execucao_depois=2024-01-01&data_execucao_antes=2024-12-31
    """
    data_execucao_depois = df_filters.DateFilter(field_name='data_execucao', lookup_expr='gte')
    data_execucao_antes = df_filters.DateFilter(field_name='data_execucao', lookup_expr='lte')

    class Meta:
        model = HistoricoManutencao
        fields = ['ordem_servico', 'data_execucao_depois', 'data_execucao_antes']


class OrdemServicoViewSet(viewsets.ModelViewSet):
    serializer_class = OrdemServicoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'prioridade', 'equipamento', 'responsavel']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['data_abertura', 'prioridade', 'status']
    ordering = ['-data_abertura']

    def get_queryset(self):
        user = self.request.user
        qs = OrdemServico.objects.select_related('equipamento', 'responsavel')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()


class HistoricoManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = HistoricoManutencaoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HistoricoManutencaoFilter
    search_fields = ['descricao_servico']

    def get_queryset(self):
        user = self.request.user
        qs = HistoricoManutencao.objects.select_related('ordem_servico')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(ordem_servico__equipamento__empresa=user.empresa)
        return qs.none()