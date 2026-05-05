from django.db import models
from ativos.models import Equipamento

class Sensor(models.Model):
    TIPO_SENSOR_CHOICES = (
        ('temperatura', 'Temperatura'),
        ('vibracao', 'Vibração'),
        ('pressao', 'Pressão'),
        ('corrente', 'Corrente Elétrica'),
        ('umidade', 'Umidade'),
    )

    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='sensores')
    tipo_sensor = models.CharField(max_length=50, choices=TIPO_SENSOR_CHOICES)
    unidade_medida = models.CharField(max_length=20, help_text="Ex: °C, mm/s, bar, A")
    limite_alerta = models.FloatField(null=True, blank=True, help_text="Limite máximo para gerar alerta crítico")
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Se o limite não for fornecido, busca o padrão do sistema
        if self.limite_alerta is None:
            from .config_alertas import obter_limite
            self.limite_alerta = obter_limite(self.equipamento.tipo, self.tipo_sensor)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_sensor_display()} - {self.equipamento.nome}"

class Telemetria(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='leituras')
    valor = models.FloatField()
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Telemetrias"
        ordering = ['-data_hora']

    def __str__(self):
        return f"{self.sensor.tipo_sensor}: {self.valor} {self.sensor.unidade_medida} em {self.data_hora}"
