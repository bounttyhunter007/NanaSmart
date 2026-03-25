from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alerta
from .serializers import AlertaSerializer

class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'nivel', 'status']
    search_fields = ['tipo_alerta', 'descricao']
