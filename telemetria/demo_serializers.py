"""Contratos da demonstração: validação existente e documentação das respostas."""

from rest_framework import serializers

from alertas.models import Alerta
from manutencao.models import OrdemServico
from .demo_service import VALUES
from .models import TrendDemo


class DemoRequest(serializers.Serializer):
    empresa = serializers.IntegerField(min_value=1, required=False)
    acao = serializers.ChoiceField(choices=['avancar', 'parar', 'fase'], default='avancar')
    cenario = serializers.ChoiceField(choices=list(VALUES), required=False)


class DemoCreateRequest(serializers.Serializer):
    empresa = serializers.IntegerField(min_value=1)
    cenario = serializers.ChoiceField(choices=TrendDemo._meta.get_field('cenario').choices, default='aumento')


class DemoUpdateRequest(serializers.Serializer):
    acao = serializers.ChoiceField(choices=['avancar', 'parar', 'fase'], default='avancar')
    cenario = serializers.ChoiceField(
        choices=TrendDemo._meta.get_field('cenario').choices, required=False,
        help_text='Obrigatório quando a ação for fase.',
    )


class DemoAlertSerializer(serializers.ModelSerializer):
    ordem_servico_id = serializers.IntegerField(allow_null=True)

    class Meta:
        model = Alerta
        fields = ('id', 'origem', 'nivel', 'status', 'descricao', 'ordem_servico_id', 'data_normalizacao')


class DemoOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServico
        fields = ('id', 'tipo_os', 'status', 'prioridade', 'titulo')


class TrendDemoSnapshotSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    cenario = serializers.ChoiceField(choices=TrendDemo._meta.get_field('cenario').choices)
    status = serializers.ChoiceField(choices=TrendDemo._meta.get_field('status').choices)
    passo = serializers.IntegerField(min_value=1, max_value=7)
    total_passos = serializers.IntegerField()
    intervalo_segundos = serializers.IntegerField()
    proxima_leitura_em = serializers.DateTimeField()
    sensor_id = serializers.IntegerField()
    equipamento_id = serializers.IntegerField()
    empresa_id = serializers.IntegerField()
    analysis = serializers.DictField(
        allow_null=True,
        help_text='Análise operacional do sensor, incluindo critérios, qualidade e amostra. Nulo se o sensor estiver inativo.',
    )
    alertas = DemoAlertSerializer(many=True)
    ordens = DemoOrderSerializer(many=True)
