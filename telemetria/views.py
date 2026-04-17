from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sensor, Telemetria
from .serializers import SensorSerializer, TelemetriaSerializer
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'tipo_sensor', 'ativo']
    search_fields = ['descricao']

    def get_queryset(self):
        user = self.request.user
        qs = Sensor.objects.select_related('equipamento')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()


class TelemetriaViewSet(viewsets.ModelViewSet):
    serializer_class = TelemetriaSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sensor', 'sensor__equipamento']

    def get_queryset(self):
        user = self.request.user
        qs = Telemetria.objects.select_related('sensor', 'sensor__equipamento').order_by('-data_hora')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(sensor__equipamento__empresa=user.empresa)
        return qs.none()