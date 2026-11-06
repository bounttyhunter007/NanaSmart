from rest_framework import viewsets, filters, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CriteriosCriticidade
from .serializers import CriteriosCriticidadeSerializer
from .services import CRITERIOS_SUGERIDOS
from django_filters.rest_framework import DjangoFilterBackend
from .models import Equipamento, EquipamentoLocalizacao, PlanoManutencao, TipoEquipamento, HistoricoCriticidadeEquipamento
from .serializers import (EquipamentoSerializer, EquipamentoLocalizacaoSerializer, PlanoManutencaoSerializer,
                          TipoEquipamentoSerializer, HistoricoCriticidadeEquipamentoSerializer)
from accounts.permissions import IsGestorOrReadOnly
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError


class EquipamentoViewSet(viewsets.ModelViewSet):
    serializer_class = EquipamentoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['empresa', 'status', 'tipo', 'tipo_equipamento', 'criticidade', 'localizacao__setor']
    search_fields = ['nome', 'fabricante', 'modelo', 'numero_serie']

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'detail': 'Este equipamento possui histórico de alertas. Desative o equipamento para preservar os registros.'})

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipamento.objects.none()
        user = self.request.user
        if user.tipo_usuario == 'admin':
            return Equipamento.objects.select_related('tipo_equipamento', 'criterios_criticidade').all()
        if user.empresa:
            return Equipamento.objects.select_related('tipo_equipamento', 'criterios_criticidade').filter(empresa=user.empresa)
        return Equipamento.objects.none()


class TipoEquipamentoViewSet(viewsets.ModelViewSet):
    queryset = TipoEquipamento.objects.none()
    serializer_class = TipoEquipamentoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset
        user = self.request.user
        if user.tipo_usuario == 'admin':
            return TipoEquipamento.objects.all()
        return TipoEquipamento.objects.filter(empresa=user.empresa) if user.empresa else TipoEquipamento.objects.none()


class HistoricoCriticidadeEquipamentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistoricoCriticidadeEquipamento.objects.none()
    serializer_class = HistoricoCriticidadeEquipamentoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['equipamento']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset
        user = self.request.user
        qs = HistoricoCriticidadeEquipamento.objects.select_related('equipamento', 'alterado_por')
        if user.tipo_usuario == 'admin':
            return qs
        return qs.filter(equipamento__empresa=user.empresa) if user.empresa else qs.none()


class CriteriosCriticidadeViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CriteriosCriticidadeSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CriteriosCriticidade.objects.none()
        qs = CriteriosCriticidade.objects.select_related('criado_por')
        user = self.request.user
        return qs if user.tipo_usuario == 'admin' else qs.filter(empresa_id=user.empresa_id)

    @action(detail=False, methods=['get'])
    def atual(self, request):
        from accounts.models import Empresa
        from rest_framework.exceptions import NotFound
        try:
            empresa_id = int(request.query_params.get('empresa') or request.user.empresa_id)
        except (TypeError, ValueError):
            raise ValidationError({'empresa': 'Selecione uma empresa.'})
        if (request.user.tipo_usuario != 'admin' and empresa_id != request.user.empresa_id
                or not Empresa.objects.filter(pk=empresa_id).exists()):
            raise NotFound('Empresa não encontrada.')
        obj = self.get_queryset().filter(empresa_id=empresa_id).first()
        return Response(self.get_serializer(obj).data if obj else {
            **CRITERIOS_SUGERIDOS, 'empresa': empresa_id, 'revisao': None,
            'representante_manutencao': '', 'data_validacao': None,
        })


class EquipamentoLocalizacaoViewSet(viewsets.ModelViewSet):
    serializer_class = EquipamentoLocalizacaoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'setor']
    search_fields = ['setor']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return EquipamentoLocalizacao.objects.none()
        user = self.request.user
        qs = EquipamentoLocalizacao.objects.select_related('equipamento')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()


class PlanoManutencaoViewSet(viewsets.ModelViewSet):
    """
    Gerencia os planos de manutenção preditiva por horímetro.
    Apenas Gestores e Admins podem criar/editar planos.
    Técnicos podem visualizar.
    """
    serializer_class = PlanoManutencaoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'ativo', 'prioridade']
    search_fields = ['nome_servico', 'descricao']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PlanoManutencao.objects.none()
        user = self.request.user
        qs = PlanoManutencao.objects.select_related('equipamento')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()
