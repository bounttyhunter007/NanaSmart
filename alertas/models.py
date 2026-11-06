from django.db import models
from ativos.models import Equipamento

class Alerta(models.Model):
    NIVEL_CHOICES = (
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('critico', 'Crítico'),
    )
    
    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('resolvido', 'Resolvido'),
        ('ignorado', 'Ignorado'),
    )

    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, related_name='alertas')
    sensor = models.ForeignKey(
        'telemetria.Sensor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas',
        help_text='Sensor que originou o alerta, quando aplicável.'
    )
    tipo_alerta = models.CharField(max_length=100)
    ORIGEM_CHOICES = (
        ('limite', 'Limite operacional'),
        ('tendencia', 'Tendência preditiva'),
        ('manual', 'Manual'),
    )
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='manual')
    ordem_servico = models.ForeignKey(
        'manutencao.OrdemServico', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='alertas_relacionados',
        help_text='Ordem que atende esta ocorrência; pode atender outras recorrências.',
    )
    evento_chave = models.CharField(
        max_length=160, blank=True, default='', db_index=True,
        help_text='Identificador estável do episódio para reprocessamento idempotente.'
    )
    dados_analise = models.JSONField(default=dict, blank=True)
    dados_deteccao = models.JSONField(default=dict, blank=True, editable=False)
    data_normalizacao = models.DateTimeField(null=True, blank=True, editable=False)
    analise_ia = models.TextField(blank=True, default='')
    data_ultima_analise = models.DateTimeField(null=True, blank=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='baixo')
    descricao = models.TextField()
    data_alerta = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('evento_chave',),
                condition=models.Q(status='ativo') & ~models.Q(evento_chave=''),
                name='alerta_evento_ativo_unico',
            ),
        ]

    def __str__(self):
        return f"[{self.nivel.upper()}] {self.tipo_alerta} - {self.equipamento.nome}"
