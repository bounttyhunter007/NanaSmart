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


class MeView(APIView):
    """
    GET /api/auth/me/
    Retorna o perfil completo do usuário autenticado via JWT.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Permite que qualquer usuário autenticado troque sua própria senha.
    Não requer e-mail, SMS ou link externo — a senha atual serve como confirmação de identidade.

    Payload:
        {
            "senha_atual": "senha_de_hoje",
            "nova_senha": "nova_senha_segura",
            "confirmar_nova_senha": "nova_senha_segura"
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import ChangePasswordSerializer
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = request.user
        if not user.check_password(serializer.validated_data['senha_atual']):
            return Response({'senha_atual': 'Senha atual incorreta.'}, status=400)

        user.set_password(serializer.validated_data['nova_senha'])
        user.save()
        return Response({'detail': 'Senha alterada com sucesso.'}, status=200)