import uuid

from django.db import models, transaction
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
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPO_SENSOR_CHOICES)
    unidade_medida = models.CharField(max_length=20, help_text="Ex: °C, mm/s, bar, A")
    limite_alerta = models.FloatField(help_text="Limite máximo para gerar alerta crítico")
    limite_alerta_baixo_pct = models.FloatField(
        blank=True,
        null=True,
        help_text="Percentual do limite crítico que dispara alerta baixo (0-100).",
        verbose_name="Alerta Baixo (%)"
    )
    limite_alerta_medio_pct = models.FloatField(
        blank=True,
        null=True,
        help_text="Percentual do limite crítico que dispara alerta médio (0-100).",
        verbose_name="Alerta Médio (%)"
    )
    limite_alerta_critico_pct = models.FloatField(
        blank=True,
        null=True,
        help_text="Percentual do limite crítico que dispara alerta crítico (0-100).",
        verbose_name="Alerta Crítico (%)"
    )
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        low = self.limite_alerta_baixo_pct if self.limite_alerta_baixo_pct is not None else 70.0
        medium = self.limite_alerta_medio_pct if self.limite_alerta_medio_pct is not None else 85.0
        critical = self.limite_alerta_critico_pct if self.limite_alerta_critico_pct is not None else 100.0

        for name, value in [
            ('limite_alerta_baixo_pct', low),
            ('limite_alerta_medio_pct', medium),
            ('limite_alerta_critico_pct', critical),
        ]:
            if value is not None and not (0 <= value <= 100):
                raise ValidationError({name: 'Deve ser um percentual entre 0 e 100.'})

        if not (0 <= low < medium < critical <= 100):
            raise ValidationError(
                'Os valores de alerta devem obedecer: baixo < médio < crítico e estar entre 0 e 100.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome} ({self.equipamento.nome})"

class Telemetria(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='leituras')
    valor = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Serializa ingestão e sinais por sensor; a leitura e seus efeitos são atômicos.
        with transaction.atomic():
            Sensor.objects.select_for_update().get(pk=self.sensor_id)
            super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Telemetrias"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.sensor.tipo}: {self.valor} {self.sensor.unidade_medida} em {self.timestamp}"


class TrendConfig(models.Model):
    """
    Configuração de análise de tendência por sensor.
    Se sensor=null, é a configuração global padrão.
    """
    SENSIBILIDADE_CHOICES = (
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
    )

    sensor = models.OneToOneField(
        Sensor, on_delete=models.CASCADE,
        related_name='trend_config',
        null=True, blank=True,
        help_text="Se null, é a configuração global padrão"
    )
    periodo_horas = models.IntegerField(
        default=24,
        help_text="Período de análise em horas"
    )
    num_leituras = models.IntegerField(
        default=50,
        help_text="Número máximo de leituras para análise"
    )
    minimo_leituras = models.IntegerField(default=3, help_text='Mínimo de leituras válidas com horários distintos.')
    duracao_minima_minutos = models.IntegerField(default=30, help_text='Duração mínima coberta pela amostra.')
    persistencia_minima = models.FloatField(default=0.7, help_text='Fração mínima de intervalos no sentido da tendência (0 a 1).')
    r2_minimo = models.FloatField(default=0.8, help_text='Qualidade mínima do ajuste linear (0 a 1).')
    direcao_alerta = models.CharField(
        max_length=20, default='crescente',
        choices=(('crescente', 'Aumento'), ('decrescente', 'Redução'), ('ambas', 'Ambas')),
        help_text='Sentidos considerados anormais para este sensor.',
    )
    sensibilidade = models.CharField(
        max_length=20,
        choices=SENSIBILIDADE_CHOICES,
        default='media'
    )
    ativo = models.BooleanField(default=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.periodo_horas < 1:
            raise ValidationError({'periodo_horas': 'A janela deve ser de pelo menos uma hora.'})
        if self.num_leituras < 3:
            raise ValidationError({'num_leituras': 'São necessárias pelo menos três leituras.'})
        if self.num_leituras > 500:
            raise ValidationError({'num_leituras': 'O limite configurável é de 500 leituras.'})
        if not 3 <= self.minimo_leituras <= self.num_leituras:
            raise ValidationError({'minimo_leituras': 'Use de 3 até o máximo de leituras configurado.'})
        if not 1 <= self.duracao_minima_minutos <= self.periodo_horas * 60:
            raise ValidationError({'duracao_minima_minutos': 'Use de 1 minuto até a duração da janela.'})
        for field in ('persistencia_minima', 'r2_minimo'):
            if not 0.5 <= getattr(self, field) <= 1:
                raise ValidationError({field: 'Use um valor entre 0,5 e 1.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Configuração de Tendência"
        verbose_name_plural = "Configurações de Tendência"

    def __str__(self):
        if self.sensor:
            return f"TrendConfig: {self.sensor.nome} ({self.sensor.equipamento.nome})"
        return "TrendConfig: Global (padrão)"

class TrendDemo(models.Model):
    """Demonstração identificada, com relógio real e amostras limitadas pelo servidor."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey('accounts.Usuario', on_delete=models.CASCADE, related_name='trend_demos')
    sensor = models.OneToOneField(Sensor, on_delete=models.CASCADE, related_name='demonstracao')
    cenario = models.CharField(max_length=20, default='aumento', choices=(
        ('aumento', 'Aumento gradual'), ('limite', 'Ultrapassar limite'),
        ('recuperacao', 'Recuperação'), ('estavel', 'Valores estáveis'), ('pico', 'Pico isolado'),
    ))
    status = models.CharField(max_length=20, default='executando', choices=(
        ('executando', 'Executando'), ('concluido', 'Concluído'), ('parado', 'Parado'),
    ))
    passo = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultima_leitura_em = models.DateTimeField()
