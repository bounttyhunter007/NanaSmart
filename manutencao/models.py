from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from ativos.models import Equipamento
from accounts.models import Usuario
from alertas.models import Alerta

class OrdemServico(models.Model):
    # Relacionamentos Mágicos
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='ordens_servico')
    responsavel = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='minhas_os')
    alerta_origem = models.OneToOneField(
        Alerta, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordem_servico_preditiva',
        help_text='Alerta que originou a ordem automática, quando aplicável.'
    )
    sensor_origem = models.ForeignKey(
        'telemetria.Sensor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordens_servico_origem',
    )
    
    # Tipo da OS
    TIPO_OS_CHOICES = (
        ('corretiva',  'Corretiva'),   # Gerada por alerta de sensor
        ('preditiva',  'Preditiva'),   # Gerada por horímetro (plano de manutenção)
        ('preventiva', 'Preventiva'),  # Criada manualmente pelo gestor
    )
    tipo_os = models.CharField(max_length=20, choices=TIPO_OS_CHOICES, default='preventiva')

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
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    )
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='baixa')
    GRAVIDADE_CHOICES = (
        ('ausente', 'Não informada'), ('baixa', 'Baixa'), ('moderada', 'Moderada'),
        ('alta', 'Alta'), ('critica', 'Crítica'),
    )
    gravidade_condicao = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES, default='ausente')
    risco_seguranca = models.BooleanField(default=False)
    prioridade_manual = models.BooleanField(default=False)
    prioridade_automatica = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, blank=True)
    justificativa_prioridade = models.TextField(blank=True)
    criticidade_na_abertura = models.CharField(max_length=1, blank=True, null=True)
    justificativa_criticidade_na_abertura = models.TextField(blank=True)
    
    # Datas
    data_abertura = models.DateTimeField(default=timezone.now) # Preenche com a hora atual, mas aceita valores manuais
    data_conclusao = models.DateTimeField(null=True, blank=True) # Só preenche quando o técnico terminar

    def save(self, *args, **kwargs):
        with transaction.atomic():
            anterior = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if anterior and anterior.status in ('concluida', 'cancelada') and self.status != anterior.status:
                raise ValidationError({'status': 'Uma ordem concluída ou cancelada não pode mudar de status.'})
            if self.status == 'concluida' and not self.data_conclusao:
                self.data_conclusao = timezone.now()
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'data_conclusao'}
            super().save(*args, **kwargs)
            if self.status == 'concluida':
                HistoricoManutencao.objects.get_or_create(
                    ordem_servico=self,
                    defaults={
                        'descricao_servico': self.descricao or self.titulo,
                        'data_execucao': timezone.localdate(self.data_conclusao),
                    },
                )

    def __str__(self):
        return f"OS #{self.id} - {self.titulo} ({self.equipamento.nome})"

class HistoricoManutencao(models.Model):
    ordem_servico = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='historico')
    descricao_servico = models.TextField()
    data_execucao = models.DateField()
    custo_pecas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    custo_mao_de_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    @property
    def custo_total(self) -> Decimal:
        return self.custo_pecas + self.custo_mao_de_obra

    def __str__(self):
        return f"Histórico OS #{self.ordem_servico.id} - {self.data_execucao}"
