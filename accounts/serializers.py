from rest_framework import serializers
from .models import Empresa, Usuario

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'empresa', 'tipo_usuario', 'cargo', 'telefone']

class MeSerializer(serializers.ModelSerializer):
    """Serializer para o endpoint /auth/me/ — retorna o perfil completo do usuário logado."""
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'tipo_usuario', 'cargo', 'telefone',
            'empresa', 'empresa_nome',
            'is_staff', 'is_superuser',
        ]
        read_only_fields = fields