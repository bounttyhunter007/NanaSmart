from rest_framework import serializers
from .models import Empresa, Usuario

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__' 

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        # Trocamos 'nome' por 'first_name' e 'last_name'
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'empresa', 'tipo_usuario', 'cargo', 'especialidade', 'telefone']