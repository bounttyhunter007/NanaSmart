from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Empresa, Usuario
from .serializers import EmpresaSerializer, UsuarioSerializer
from .permissions import IsGestor


class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    permission_classes = [IsGestor]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome', 'cnpj']

    def get_queryset(self):
        user = self.request.user
        # Se for admin geral, vê todas as empresas
        if user.tipo_usuario == 'admin':
            return Empresa.objects.all()
        # Se for usuário comum/gestor, vê apenas a própria empresa
        if user.empresa:
            return Empresa.objects.filter(pk=user.empresa.pk)
        return Empresa.objects.none()


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsGestor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['empresa', 'tipo_usuario', 'cargo']
    search_fields = ['first_name', 'last_name', 'email', 'username']

    def get_queryset(self):
        user = self.request.user
        # Se for admin geral, vê todos os usuários de todas as empresas
        if user.tipo_usuario == 'admin':
            return Usuario.objects.select_related('empresa').all()
        # Se for usuário comum/gestor, vê apenas os usuários da sua empresa
        if user.empresa:
            return Usuario.objects.select_related('empresa').filter(empresa=user.empresa)
        return Usuario.objects.none()