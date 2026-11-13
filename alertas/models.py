from copy import deepcopy

from django.db import models, transaction
from django.utils import timezone
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
    historico_niveis = models.JSONField(default=list, blank=True, editable=False)
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

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is not None and not kwargs['update_fields']:
            return
        # O registro acompanha o pico do episódio, nunca a prioridade da O.S.
        # O bloqueio e a mesma transação protegem também os serviços dos sinais.
        with transaction.atomic():
            if self.sensor_id and self.origem in ('limite', 'tendencia'):
                from telemetria.models import Sensor
                Sensor.objects.select_for_update().get(pk=self.sensor_id)
            anterior = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            self.historico_niveis = deepcopy(anterior.historico_niveis) if anterior else []
            campos = kwargs.get('update_fields')
            if anterior and (campos is None or 'nivel' in campos):
                pesos = {'baixo': 1, 'medio': 2, 'critico': 3}
                if pesos.get(self.nivel, 0) > pesos.get(anterior.nivel, 0):
                    registrado = timezone.now()
                    observado = self.data_ultima_analise if campos is None or 'data_ultima_analise' in campos else None
                    if observado == anterior.data_ultima_analise:
                        observado = None
                    self.historico_niveis.append({
                        'nivel_anterior': anterior.nivel, 'nivel': self.nivel,
                        'ocorrido_em': (observado or registrado).isoformat(),
                        'registrado_em': registrado.isoformat(),
                        'descricao': self.descricao,
                    })
            if campos is not None:
                kwargs['update_fields'] = set(campos) | {'historico_niveis'}
            super().save(*args, **kwargs)
