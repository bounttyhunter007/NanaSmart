from django.db import models
from accounts.models import Empresa

class Equipamento(models.Model):
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipamentos')
    
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100, help_text="Ex: Motor elétrico, Bomba Hidráulica")
    fabricante = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(max_length=100, unique=True)
    data_instalacao = models.DateField(blank=True, null=True)
    horimetro = models.FloatField(default=0, help_text="Horas de operação do equipamento")

    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('manutencao','Em Manutencao'),
        ('inativo', 'Inativo'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    
    def __str__(self):
        return f"{self.nome} (SN: {self.numero_serie})"

class EquipamentoLocalizacao(models.Model):
    equipamento = models.OneToOneField(Equipamento, on_delete=models.CASCADE, related_name='localizacao')
    setor = models.CharField(max_length=100)

    def __str__(self):
        return f"Localização: {self.setor} ({self.equipamento.nome})"


class PlanoManutencao(models.Model):
    """
    Define uma tarefa de manutenção recorrente para um equipamento,
    baseada em intervalo de horímetro (horas de operação).
    Exemplo: "Troca de Óleo" a cada 100 horas.
    """
    PRIORIDADE_CHOICES = (
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('critico', 'Crítico'),
    )

    equipamento     = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='planos_manutencao')
    nome_servico    = models.CharField(max_length=200, help_text="Ex: Troca de Óleo, Revisão de Rolamentos")
    descricao       = models.TextField(help_text="Detalhes do serviço a ser realizado")
    intervalo_horas = models.FloatField(help_text="A cada quantas horas este serviço deve ser realizado")
    prioridade      = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='medio')
    ativo           = models.BooleanField(default=True)

    # Controle de execução
    horimetro_ultima_os = models.FloatField(
        default=0,
        help_text="Horímetro do equipamento no momento em que a última O.S. foi gerada"
    )

    def save(self, *args, **kwargs):
        # Na criação do plano, define horimetro_ultima_os com o horímetro atual do equipamento
        # para que o próximo disparo seja: horímetro_atual + intervalo
        if not self.pk:
            self.horimetro_ultima_os = self.equipamento.horimetro
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_servico} (a cada {self.intervalo_horas}h) — {self.equipamento.nome}"