from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import MeSerializer, ChangePasswordSerializer

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
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = request.user
        if not user.check_password(serializer.validated_data['senha_atual']):
            return Response({'senha_atual': 'Senha atual incorreta.'}, status=400)

        user.set_password(serializer.validated_data['nova_senha'])
        user.save()
        return Response({'detail': 'Senha alterada com sucesso.'}, status=200)
