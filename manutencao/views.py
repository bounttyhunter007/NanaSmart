from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as df_filters
from .models import OrdemServico, HistoricoManutencao
from .serializers import OrdemServicoSerializer, HistoricoManutencaoSerializer
from .permissions import IsOwnerOrGestorOrUnassigned
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico
from rest_framework.permissions import IsAuthenticated
from django.db import transaction


class HistoricoManutencaoFilter(df_filters.FilterSet):
    # ... (rest of filter class)
    data_execucao_depois = df_filters.DateFilter(field_name='data_execucao', lookup_expr='gte')
    data_execucao_antes = df_filters.DateFilter(field_name='data_execucao', lookup_expr='lte')

    class Meta:
        model = HistoricoManutencao
        fields = [
            'ordem_servico', 'ordem_servico__equipamento__empresa',
            'data_execucao_depois', 'data_execucao_antes'
        ]


class OrdemServicoViewSet(viewsets.ModelViewSet):
    serializer_class = OrdemServicoSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrGestorOrUnassigned]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'prioridade', 'equipamento', 'equipamento__empresa', 'responsavel', 'tipo_os']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['data_abertura', 'prioridade', 'status']
    ordering = ['-data_abertura']

    @transaction.atomic
    def perform_create(self, serializer):
        validated = serializer.validated_data
        status = validated.get('status')
        responsavel = validated.get('responsavel')
        if status == 'concluida' and responsavel is None:
            serializer.save(responsavel=self.request.user)
        else:
            serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        validated = serializer.validated_data
        status = validated.get('status', serializer.instance.status)
        responsavel = validated.get('responsavel', serializer.instance.responsavel)
        if status == 'concluida' and responsavel is None:
            serializer.save(responsavel=self.request.user)
        else:
            serializer.save()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrdemServico.objects.none()
        user = self.request.user
        qs = OrdemServico.objects.select_related('equipamento', 'responsavel')
        
        if user.tipo_usuario == 'admin':
            return qs.all()
        
        if user.empresa:
            base_qs = qs.filter(equipamento__empresa=user.empresa)
            
            # Lógica de Visibilidade para Técnicos
            if user.tipo_usuario == 'tecnico':
                from django.db.models import Q
                # Técnico vê: O.S. sem dono OU O.S. que pertence a ele
                return base_qs.filter(Q(responsavel=user) | Q(responsavel__isnull=True))
            
            return base_qs
            
        return qs.none()


class HistoricoManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = HistoricoManutencaoSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HistoricoManutencaoFilter
    search_fields = ['descricao_servico']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return HistoricoManutencao.objects.none()
        user = self.request.user
        qs = HistoricoManutencao.objects.select_related('ordem_servico')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(ordem_servico__equipamento__empresa=user.empresa)
        return qs.none()
