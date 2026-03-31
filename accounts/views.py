from rest_framework import viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Empresa, Usuario
from .serializers import EmpresaSerializer, UsuarioSerializer, MeSerializer

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['nome', 'cnpj']

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['empresa', 'tipo_usuario', 'cargo']
    search_fields = ['first_name', 'last_name', 'email', 'username']

class MeView(APIView):
    """
    GET /api/auth/me/
    Retorna o perfil completo do usuário autenticado via JWT.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)