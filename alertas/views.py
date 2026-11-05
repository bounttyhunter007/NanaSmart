from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alerta
from .serializers import AlertaSerializer
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico


class AlertaViewSet(viewsets.ModelViewSet):
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'equipamento__empresa', 'nivel', 'status']
    search_fields = ['tipo_alerta', 'descricao']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Alerta.objects.none()
        user = self.request.user
        qs = Alerta.objects.select_related('equipamento', 'ordem_servico', 'ordem_servico_preditiva').order_by('-data_alerta')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()
