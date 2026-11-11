from rest_framework import serializers
from .models import OrdemServico, HistoricoManutencao, HistoricoPrioridadeOS
from accounts.validation import validate_company_resource
from ativos.serializers import CriteriosCriticidadeSerializer
from drf_spectacular.utils import extend_schema_field


class OcorrenciaAlertaOSSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    tipo_alerta = serializers.CharField()
    origem = serializers.CharField()
    sensor_nome = serializers.CharField()
    data_alerta = serializers.DateTimeField()
    nivel_inicial = serializers.CharField(allow_null=True)
    nivel_maximo = serializers.CharField()
    descricao_inicial = serializers.CharField()
    historico_niveis = serializers.ListField(child=serializers.DictField())
    historico_incompleto = serializers.BooleanField()
    data_normalizacao = serializers.DateTimeField(allow_null=True)

class OrdemServicoSerializer(serializers.ModelSerializer):
    equipamento_nome = serializers.CharField(source='equipamento.nome', read_only=True)
    criticidade_atual = serializers.CharField(source='equipamento.criticidade', read_only=True, allow_null=True)
    responsavel_nome = serializers.SerializerMethodField()
    criterios_abertura = CriteriosCriticidadeSerializer(source='criterios_criticidade_na_abertura', read_only=True)
    historico_alertas = serializers.SerializerMethodField()

    @extend_schema_field(OcorrenciaAlertaOSSerializer(many=True))
    def get_historico_alertas(self, obj):
        # A primeira relação é mantida também para vínculos antigos sem a FK.
        alertas = {alerta.pk: alerta for alerta in obj.alertas_relacionados.all()}
        if obj.alerta_origem_id:
            alertas.setdefault(obj.alerta_origem_id, obj.alerta_origem)
        resultado = []
        for alerta in sorted(alertas.values(), key=lambda a: (a.data_alerta, a.pk)):
            evidencia = alerta.dados_deteccao or {}
            niveis = alerta.historico_niveis or []
            inicial = evidencia.get('nivel')
            esperado = inicial
            completo = bool(inicial)
            for evento in niveis:
                completo = completo and evento['nivel_anterior'] == esperado
                esperado = evento['nivel']
            resultado.append({
                'id': alerta.pk, 'tipo_alerta': alerta.tipo_alerta, 'origem': alerta.origem,
                'sensor_nome': evidencia.get('sensor_nome') or (alerta.sensor.nome if alerta.sensor_id else ''),
                'data_alerta': alerta.data_alerta, 'nivel_inicial': inicial,
                'nivel_maximo': alerta.nivel, 'descricao_inicial': evidencia.get('descricao', ''),
                'historico_niveis': niveis,
                'historico_incompleto': not completo or esperado != alerta.nivel,
                'data_normalizacao': alerta.data_normalizacao,
            })
        return OcorrenciaAlertaOSSerializer(resultado, many=True).data

    def get_responsavel_nome(self, obj) -> str | None:
        return (obj.responsavel.get_full_name() or obj.responsavel.username) if obj.responsavel else None

    class Meta:
        model = OrdemServico
        fields = '__all__'
        
        # A magia da segurança Sênior acontece aqui:
        read_only_fields = [
            'data_abertura', 'data_conclusao', 'prioridade', 'prioridade_automatica',
            'prioridade_origem', 'prioridade_herdada_conhecida', 'criterios_criticidade_na_abertura',
            'justificativa_prioridade', 'criticidade_na_abertura',
            'justificativa_criticidade_na_abertura', 'prioridade_manual',
            'alerta_origem', 'sensor_origem',
        ]

    def validate(self, data):
        if 'prioridade' in self.initial_data:
            raise serializers.ValidationError({'prioridade': 'Utilize a ação de ajuste de prioridade, informando a justificativa.'})
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        responsavel = data.get('responsavel', getattr(self.instance, 'responsavel', None))

        if user and user.tipo_usuario != 'admin' and equipamento and equipamento.empresa_id != user.empresa_id:
            raise serializers.ValidationError({'equipamento': 'O equipamento deve pertencer à sua empresa.'})

        if responsavel and equipamento and responsavel.empresa_id != equipamento.empresa_id:
            if responsavel.tipo_usuario != 'admin':
                raise serializers.ValidationError({'responsavel': 'O responsável deve pertencer à empresa do equipamento.'})

        if user and user.tipo_usuario == 'tecnico':
            if responsavel and responsavel != user:
                raise serializers.ValidationError({
                    'responsavel': 'Técnicos só podem assumir ordens para si mesmos.'
                })

            if self.instance and self.instance.responsavel and self.instance.responsavel != user:
                raise serializers.ValidationError('Técnicos não podem editar ordens atribuídas a outro técnico.')

        if self.instance and self.instance.status in ('concluida', 'cancelada'):
            if data.get('status', self.instance.status) != self.instance.status:
                raise serializers.ValidationError({'status': 'Uma ordem concluída ou cancelada não pode mudar de status.'})

        if self.instance and equipamento.pk != self.instance.equipamento_id:
            raise serializers.ValidationError({'equipamento': 'O equipamento é fixo após abertura. Cancele a OS e abra outra para corrigir o vínculo.'})

        sensor = getattr(self.instance, 'sensor_origem', None)
        alerta = getattr(self.instance, 'alerta_origem', None)
        if equipamento and ((sensor and sensor.equipamento_id != equipamento.pk)
                            or (alerta and alerta.equipamento_id != equipamento.pk)):
            raise serializers.ValidationError({'equipamento': 'O equipamento deve corresponder à origem da ordem.'})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.tipo_usuario == 'tecnico':
            responsavel = validated_data.get('responsavel')
            if responsavel is None and validated_data.get('status') in ['andamento', 'concluida']:
                validated_data['responsavel'] = request.user
        ordem = super().create(validated_data)
        if request and request.user.is_authenticated:
            ordem.historico_prioridade.filter(origem='herdada').update(alterado_por=request.user)
        return ordem

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.tipo_usuario == 'tecnico':
            responsavel = validated_data.get('responsavel', instance.responsavel)
            if instance.responsavel is None and responsavel is None:
                validated_data['responsavel'] = request.user
            if validated_data.get('status') == 'concluida' and validated_data.get('responsavel') is None:
                validated_data['responsavel'] = request.user
        return super().update(instance, validated_data)

class AjustePrioridadeSerializer(serializers.Serializer):
    prioridade = serializers.ChoiceField(choices=OrdemServico.PRIORIDADE_CHOICES)
    justificativa = serializers.CharField(allow_blank=False)


class RestaurarPrioridadeSerializer(serializers.Serializer):
    justificativa = serializers.CharField(allow_blank=False)


class HistoricoPrioridadeOSSerializer(serializers.ModelSerializer):
    alterado_por_nome = serializers.CharField(source='alterado_por.username', read_only=True, default=None)

    class Meta:
        model = HistoricoPrioridadeOS
        fields = '__all__'


class HistoricoManutencaoSerializer(serializers.ModelSerializer):
    custo_total = serializers.ReadOnlyField()

    class Meta:
        model = HistoricoManutencao
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        ordem = data.get(
            'ordem_servico',
            getattr(self.instance, 'ordem_servico', None),
        )
        if ordem:
            validate_company_resource(
                request.user if request else None,
                ordem.equipamento,
                'ordem_servico',
            )
        return data
