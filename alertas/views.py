from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alerta
from .serializers import AlertaSerializer
from rest_framework.permissions import IsAuthenticated
from .filters import AlertaFilter, ordenar_historico


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertaFilter

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Alerta.objects.none()
        user = self.request.user
        qs = ordenar_historico(Alerta.objects.select_related(
            'equipamento', 'sensor', 'ordem_servico', 'ordem_servico_preditiva',
        ))
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()
