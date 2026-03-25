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

    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='alertas')
    tipo_alerta = models.CharField(max_length=100)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='baixo')
    descricao = models.TextField()
    data_alerta = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')

    def __str__(self):
        return f"[{self.nivel.upper()}] {self.tipo_alerta} - {self.equipamento.nome}"
