from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Alerta
from .serializers import AlertaSerializer
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico


class AlertaViewSet(viewsets.ModelViewSet):
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'nivel', 'status']
    search_fields = ['tipo_alerta', 'descricao']

    def get_queryset(self):
        user = self.request.user
        qs = Alerta.objects.select_related('equipamento')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(equipamento__empresa=user.empresa)
        return qs.none()