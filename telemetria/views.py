from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sensor, Telemetria
from .serializers import SensorSerializer, TelemetriaSerializer

class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'tipo_sensor', 'ativo']
    search_fields = ['descricao']

class TelemetriaViewSet(viewsets.ModelViewSet):
    queryset = Telemetria.objects.all()
    serializer_class = TelemetriaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sensor', 'sensor__equipamento']
    
    # Ordenação padrão por data decrescente (mais recente primeiro)
    ordering = ['-data_hora']
