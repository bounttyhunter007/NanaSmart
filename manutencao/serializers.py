from rest_framework import serializers
from .models import OrdemServico, HistoricoManutencao

class OrdemServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServico
        fields = '__all__'
        
        # A magia da segurança Sênior acontece aqui:
        read_only_fields = ['data_abertura', 'data_conclusao']

class HistoricoManutencaoSerializer(serializers.ModelSerializer):
    custo_total = serializers.ReadOnlyField()

    class Meta:
        model = HistoricoManutencao
        fields = '__all__'