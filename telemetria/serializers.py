import math

from rest_framework import serializers
from .models import Sensor, Telemetria, TrendConfig
from accounts.validation import validate_equipment_resource, validate_sensor_resource

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        validate_equipment_resource(
            request.user if request else None,
            equipamento,
        )

        low = data.get('limite_alerta_baixo_pct', getattr(self.instance, 'limite_alerta_baixo_pct', None))
        medium = data.get('limite_alerta_medio_pct', getattr(self.instance, 'limite_alerta_medio_pct', None))
        critical = data.get('limite_alerta_critico_pct', getattr(self.instance, 'limite_alerta_critico_pct', None))

        low = 70.0 if low is None else low
        medium = 85.0 if medium is None else medium
        critical = 100.0 if critical is None else critical

        for name, value in [
            ('limite_alerta_baixo_pct', low),
            ('limite_alerta_medio_pct', medium),
            ('limite_alerta_critico_pct', critical),
        ]:
            if value is not None and not (0 <= value <= 100):
                raise serializers.ValidationError({name: 'Deve ser um percentual entre 0 e 100.'})

        if not (0 <= low < medium < critical <= 100):
            raise serializers.ValidationError(
                'Os valores de alerta devem obedecer: baixo < médio < crítico e estar entre 0 e 100.'
            )

        return data

class TelemetriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetria
        fields = '__all__'

    def validate_valor(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError('Informe uma leitura numérica finita.')
        return value

    def validate(self, data):
        request = self.context.get('request')
        sensor = data.get('sensor', getattr(self.instance, 'sensor', None))
        validate_sensor_resource(request.user if request else None, sensor)
        return data


class TrendConfigSerializer(serializers.ModelSerializer):
    sensor_nome = serializers.CharField(source='sensor.nome', read_only=True, default=None)
    equipamento_nome = serializers.CharField(source='sensor.equipamento.nome', read_only=True, default=None)

    class Meta:
        model = TrendConfig
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        sensor = data.get('sensor', getattr(self.instance, 'sensor', None))
        if user and user.tipo_usuario != 'admin' and sensor is None:
            raise serializers.ValidationError({
                'sensor': 'Somente administradores podem alterar a configuração global.'
            })
        validate_sensor_resource(user, sensor)
        periodo = data.get('periodo_horas', getattr(self.instance, 'periodo_horas', 24))
        leituras = data.get('num_leituras', getattr(self.instance, 'num_leituras', 50))
        if periodo < 1:
            raise serializers.ValidationError({'periodo_horas': 'Informe um período positivo.'})
        if not 3 <= leituras <= 500:
            raise serializers.ValidationError({'num_leituras': 'Use entre 3 e 500 leituras.'})
        return data
