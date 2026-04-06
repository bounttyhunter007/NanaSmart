from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Equipamento, EquipamentoLocalizacao
from .serializers import EquipamentoSerializer, EquipamentoLocalizacaoSerializer
from accounts.permissions import IsGestorOrReadOnly


class EquipamentoViewSet(viewsets.ModelViewSet):
    serializer_class = EquipamentoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['empresa', 'status', 'tipo']
    search_fields = ['nome', 'fabricante', 'modelo', 'numero_serie']

    def get_queryset(self):
        user = self.request.user
        if user.tipo_usuario == 'admin':
            return Equipamento.objects.all()
        if user.empresa:
            return Equipamento.objects.filter(empresa=user.empresa)
        return Equipamento.objects.none()


class EquipamentoLocalizacaoViewSet(viewsets.ModelViewSet):
    serializer_class = EquipamentoLocalizacaoSerializer
    permission_classes = [IsGestorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'setor']
    search_fields = ['setor']

    def get_queryset(self):
        user = self.request.user
        qs = EquipamentoLocalizacao.objects.select_related('equipamento')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()