from rest_framework import viewsets
from .models import Equipamento, EquipamentoLocalizacao
from .serializers import EquipamentoSerializer, EquipamentoLocalizacaoSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class EquipamentoViewSet(viewsets.ModelViewSet):
    queryset = Equipamento.objects.all()
    serializer_class = EquipamentoSerializer
    
    # Já vamos deixar os filtros Sênior prontos!
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['empresa', 'status', 'tipo'] # Filtros exatos
    search_fields = ['nome', 'fabricante', 'modelo', 'numero_serie'] # Busca por texto

class EquipamentoLocalizacaoViewSet(viewsets.ModelViewSet):
    queryset = EquipamentoLocalizacao.objects.all()
    serializer_class = EquipamentoLocalizacaoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['equipamento', 'setor', 'planta']