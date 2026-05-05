from django.db import models
from django.utils import timezone
from ativos.models import Equipamento
from accounts.models import Usuario

class OrdemServico(models.Model):
    # Relacionamentos Mágicos
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='ordens_servico')
    responsavel = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='minhas_os')
    
    # Dados da OS
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(help_text="Descreva o problema ou o serviço a ser realizado")
    
    # Status e Prioridade
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    
    PRIORIDADE_CHOICES = (
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('critico', 'Crítico'),
    )
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='baixo')
    
    # Datas
    data_abertura = models.DateTimeField(default=timezone.now) # Preenche com a hora atual, mas aceita valores manuais
    data_conclusao = models.DateTimeField(null=True, blank=True) # Só preenche quando o técnico terminar

    def save(self, *args, **kwargs):
        # Se o status for concluída e a data de conclusão ainda estiver vazia...
        if self.status == 'concluida' and not self.data_conclusao:
            self.data_conclusao = timezone.now() # O servidor carimba a data e hora exatas!
            
        super().save(*args, **kwargs) # Continua o processo normal de salvar no banco

    def __str__(self):
        return f"OS #{self.id} - {self.titulo} ({self.equipamento.nome})"

class HistoricoManutencao(models.Model):
    ordem_servico = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='historico')
    descricao_servico = models.TextField()
    data_execucao = models.DateField()
    custo_pecas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    custo_mao_de_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_de_obra

    def __str__(self):
        return f"Histórico OS #{self.ordem_servico.id} - {self.data_execucao}"