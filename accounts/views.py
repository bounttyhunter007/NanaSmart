from rest_framework import viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Empresa, Usuario
from .serializers import EmpresaSerializer, UsuarioSerializer, MeSerializer
from .permissions import IsGestor


class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    permission_classes = [IsGestor]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome', 'cnpj']

    def get_queryset(self):
        user = self.request.user
        if user.tipo_usuario == 'admin':
            return Empresa.objects.all()
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
        if user.tipo_usuario == 'admin':
            return Usuario.objects.select_related('empresa').all()
        if user.empresa:
            return Usuario.objects.select_related('empresa').filter(empresa=user.empresa)
        return Usuario.objects.none()


class MeView(APIView):
    """
    GET /api/auth/me/
    Retorna o perfil completo do usuário autenticado via JWT.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)