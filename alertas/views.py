from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alerta
from .serializers import AlertaSerializer, AlertaOperadorSerializer
from accounts.permissions import IsOperationalUser, IsOperationalOrOperatorReadOnly
from .filters import AlertaFilter, ordenar_historico
from django.db.models import Exists, OuterRef
from django.db.models.functions import Coalesce
from manutencao.visibility import visible_work_orders


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertaSerializer
    permission_classes = [IsOperationalUser | IsOperationalOrOperatorReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertaFilter

    def get_serializer_class(self):
        if getattr(getattr(self.request, 'user', None), 'tipo_usuario', None) == 'operador':
            return AlertaOperadorSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Alerta.objects.none()
        user = self.request.user
        qs = ordenar_historico(Alerta.objects.select_related(
            'equipamento', 'sensor', 'ordem_servico', 'ordem_servico_preditiva',
        )).annotate(ordem_servico_acessivel=Exists(
            visible_work_orders(user).filter(pk=Coalesce(
                OuterRef('ordem_servico_id'), OuterRef('ordem_servico_preditiva__pk'),
            )),
        ))
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()
