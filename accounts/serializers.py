from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
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


class ChangePasswordSerializer(serializers.Serializer):
  
    senha_atual = serializers.CharField(required=True, write_only=True)
    nova_senha = serializers.CharField(required=True, write_only=True, min_length=6)
    confirmar_nova_senha = serializers.CharField(required=True, write_only=True)

    def validate_nova_senha(self, value):
        # Roda as validações de senha do Django (tamanho mínimo, senha numérica etc.)
        validate_password(value)
        return value

    def validate(self, data):
        if data['nova_senha'] != data['confirmar_nova_senha']:
            raise serializers.ValidationError({'confirmar_nova_senha': 'As senhas não coincidem.'})
        return data