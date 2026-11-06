from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from accounts.models import Empresa
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import Equipamento, EquipamentoLocalizacao, PlanoManutencao, TipoEquipamento, HistoricoCriticidadeEquipamento, CriteriosCriticidade
from .services import aplicar_criticidade
from accounts.validation import validate_equipment_resource

class CriteriosCriticidadeSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source='criado_por.username', read_only=True, default=None)

    class Meta:
        model = CriteriosCriticidade
        fields = '__all__'
        read_only_fields = ['revisao', 'criado_por', 'criado_em']
        validators = []  # A revisão é atribuída sob bloqueio da empresa.

    def validate_empresa(self, empresa):
        user = self.context['request'].user
        if user.tipo_usuario != 'admin' and empresa.pk != user.empresa_id:
            raise serializers.ValidationError('Os critérios devem pertencer à sua empresa.')
        return empresa

    def validate_data_validacao(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('A data de validação não pode estar no futuro.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        Empresa.objects.select_for_update().get(pk=validated_data['empresa'].pk)
        ultima = CriteriosCriticidade.objects.filter(empresa=validated_data['empresa']).first()
        return CriteriosCriticidade.objects.create(**validated_data,
            revisao=(ultima.revisao + 1 if ultima else 1), criado_por=self.context['request'].user)


class EquipamentoSerializer(serializers.ModelSerializer):
    criticidade_sugerida = serializers.SerializerMethodField(read_only=True)
    aceitar_sugestao = serializers.BooleanField(write_only=True, required=False, default=False)
    criterios_utilizados = CriteriosCriticidadeSerializer(source='criterios_criticidade', read_only=True)

    class Meta:
        model = Equipamento
        fields = '__all__'
        read_only_fields = ['criticidade_origem', 'criterios_criticidade']

    def get_criticidade_sugerida(self, obj) -> str | None:
        return obj.tipo_equipamento.criticidade_padrao if obj.tipo_equipamento else None

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        empresa = data.get('empresa', getattr(self.instance, 'empresa', None))
        if user and user.tipo_usuario != 'admin' and (empresa is None or empresa != user.empresa):
            raise serializers.ValidationError({'empresa': 'O equipamento deve pertencer à sua empresa.'})
        if self.instance and empresa.pk != self.instance.empresa_id:
            raise serializers.ValidationError({'empresa': 'A empresa do equipamento não pode ser alterada; preserve seu histórico.'})
        tipo = data.get('tipo_equipamento', getattr(self.instance, 'tipo_equipamento', None))
        if tipo and empresa and tipo.empresa_id != empresa.pk:
            raise serializers.ValidationError({'tipo_equipamento': 'O tipo deve pertencer à empresa do equipamento.'})
        if data.get('aceitar_sugestao'):
            if not tipo or not tipo.criticidade_padrao:
                raise serializers.ValidationError({'aceitar_sugestao': 'O tipo selecionado não possui classe sugerida.'})
            if data.get('criticidade') and data['criticidade'] != tipo.criticidade_padrao:
                raise serializers.ValidationError({'criticidade': 'A classe deve corresponder à sugestão aceita.'})
            data['criticidade'] = tipo.criticidade_padrao
        classe = data.get('criticidade', getattr(self.instance, 'criticidade', None))
        motivo = data.get('justificativa_criticidade', getattr(self.instance, 'justificativa_criticidade', ''))
        mudou = (classe != getattr(self.instance, 'criticidade', None) or
                 motivo != getattr(self.instance, 'justificativa_criticidade', '') or data.get('aceitar_sugestao'))
        if mudou and (self.instance or classe):
            if not motivo.strip():
                raise serializers.ValidationError({'justificativa_criticidade': 'Informe a justificativa da avaliação.'})
            if classe and not CriteriosCriticidade.objects.filter(empresa=empresa).exists():
                raise serializers.ValidationError({'criticidade': 'Cadastre os critérios validados da empresa antes de classificar.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        aceitar = validated_data.pop('aceitar_sugestao', False)
        classe = validated_data.pop('criticidade', None)
        motivo = validated_data.pop('justificativa_criticidade', '')
        equipamento = super().create(validated_data)
        if classe:
            aplicar_criticidade(equipamento, classe, motivo, self.context['request'].user, 'tipo' if aceitar else 'individual')
        return equipamento

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Equipamento.objects.select_for_update().get(pk=instance.pk)
        aceitar = validated_data.pop('aceitar_sugestao', False)
        classe = validated_data.pop('criticidade', instance.criticidade)
        motivo = validated_data.pop('justificativa_criticidade', instance.justificativa_criticidade)
        mudou = classe != instance.criticidade or motivo != instance.justificativa_criticidade or aceitar
        equipamento = super().update(instance, validated_data)
        if mudou:
            aplicar_criticidade(equipamento, classe, motivo, self.context['request'].user, 'tipo' if aceitar else 'individual')
        return equipamento


class TipoEquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoEquipamento
        fields = '__all__'
        read_only_fields = ['criticidade_padrao_legada']

    def validate_empresa(self, empresa):
        request = self.context.get('request')
        if request and request.user.tipo_usuario != 'admin' and empresa != request.user.empresa:
            raise serializers.ValidationError('O tipo deve pertencer à sua empresa.')
        return empresa


class HistoricoCriticidadeEquipamentoSerializer(serializers.ModelSerializer):
    alterado_por_nome = serializers.CharField(source='alterado_por.username', read_only=True, default=None)
    criterios_utilizados = CriteriosCriticidadeSerializer(source='criterios_criticidade', read_only=True)
    class Meta:
        model = HistoricoCriticidadeEquipamento
        fields = '__all__'
        read_only_fields = [
            'equipamento', 'criticidade_anterior', 'criticidade_nova',
            'justificativa', 'alterado_por', 'criado_em',
        ]

class EquipamentoLocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipamentoLocalizacao
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        validate_equipment_resource(
            request.user if request else None,
            equipamento,
        )
        return data


class PlanoManutencaoSerializer(serializers.ModelSerializer):
    proximo_disparo_horas = serializers.SerializerMethodField()

    class Meta:
        model = PlanoManutencao
        fields = '__all__'
        read_only_fields = ['horimetro_ultima_os', 'prioridade']

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_proximo_disparo_horas(self, obj):
        """Calcula e exibe quando a próxima O.S. será gerada."""
        return obj.horimetro_ultima_os + obj.intervalo_horas


    def validate(self, data):
        request = self.context.get('request')
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        validate_equipment_resource(
            request.user if request else None,
            equipamento,
        )
        return data
