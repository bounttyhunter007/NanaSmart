from django.db import models
from accounts.models import Empresa

CRITICIDADE_ABC = (('A', 'A — Alta criticidade'), ('B', 'B — Média criticidade'), ('C', 'C — Baixa criticidade'))


class CriteriosCriticidade(models.Model):
    """Revisões publicadas e imutáveis do guia validado de cada empresa."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='criterios_criticidade')
    revisao = models.PositiveIntegerField()
    criterio_a = models.TextField()
    criterio_b = models.TextField()
    criterio_c = models.TextField()
    representante_manutencao = models.CharField(max_length=200)
    data_validacao = models.DateField()
    criado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-revisao']
        constraints = [models.UniqueConstraint(fields=['empresa', 'revisao'], name='criterios_empresa_revisao_unica')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            from django.core.exceptions import ValidationError
            raise ValidationError('Publique uma nova revisão; critérios anteriores são imutáveis.')
        super().save(*args, **kwargs)


class TipoEquipamento(models.Model):
    """Catálogo por empresa usado apenas como sugestão, nunca como sobrescrita."""

    CRITICIDADE_CHOICES = CRITICIDADE_ABC
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='tipos_equipamento')
    nome = models.CharField(max_length=100)
    criticidade_padrao = models.CharField(max_length=1, choices=CRITICIDADE_CHOICES, blank=True, null=True)
    criticidade_padrao_legada = models.CharField(max_length=20, blank=True, null=True, editable=False)
    descricao_criterios = models.TextField(blank=True, help_text='Critérios locais que justificam a sugestão.')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['empresa', 'nome'], name='tipo_equipamento_por_empresa_unico')]
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Equipamento(models.Model):
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipamentos')
    
    nome = models.CharField(max_length=255)
    TIPO_EQUIPAMENTO_CHOICES = (
        ('motor_eletrico', 'Motor Elétrico'),
        ('bomba_hidraulica', 'Bomba Hidráulica'),
        ('compressor_ar', 'Compressor de Ar'),
        ('gerador', 'Gerador'),
        ('prensa', 'Prensa'),
        ('esteira', 'Esteira'),
        ('ventilador', 'Ventilador Industrial'),
        ('outro', 'Outro'),
    )
    
    tipo = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Ex: Motor elétrico, Bomba Hidráulica"
    )
    tipo_equipamento = models.ForeignKey(
        TipoEquipamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='equipamentos',
        help_text='Catálogo opcional; sua criticidade é apenas uma sugestão inicial.'
    )
    fabricante = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True, help_text="Descrição do equipamento")
    data_instalacao = models.DateField(blank=True, null=True)
    horimetro = models.FloatField(default=0, help_text="Horas de operação do equipamento")

    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('manutencao','Em Manutenção'),
        ('inativo', 'Inativo'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')

    CRITICIDADE_CHOICES = CRITICIDADE_ABC
    ORIGEM_CRITICIDADE_CHOICES = (
        ('nao_avaliada', 'Não avaliada'), ('tipo', 'Sugerida pelo tipo'),
        ('individual', 'Avaliação individual'), ('migracao', 'Convertida do legado'),
    )
    criticidade = models.CharField(max_length=1, choices=CRITICIDADE_CHOICES, blank=True, null=True,
                                   help_text='Classe A/B/C; nulo significa não avaliada.')
    criticidade_origem = models.CharField(max_length=20, choices=ORIGEM_CRITICIDADE_CHOICES, default='nao_avaliada')
    justificativa_criticidade = models.TextField(blank=True, help_text='Justificativa da avaliação individual ou da sugestão aceita.')
    criterios_criticidade = models.ForeignKey(CriteriosCriticidade, on_delete=models.PROTECT, null=True, blank=True)
    
    def __str__(self):
        return f"{self.nome} (SN: {self.numero_serie})"


class HistoricoCriticidadeEquipamento(models.Model):
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='historico_criticidade')
    criticidade_anterior = models.CharField(max_length=1, blank=True, null=True)
    criticidade_nova = models.CharField(max_length=1, choices=Equipamento.CRITICIDADE_CHOICES, blank=True, null=True)
    justificativa = models.TextField(blank=True)
    alterado_por = models.ForeignKey('accounts.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    criterios_criticidade = models.ForeignKey(CriteriosCriticidade, on_delete=models.PROTECT, null=True, blank=True)
    origem = models.CharField(max_length=20, default='individual')
    dados_anteriores = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-criado_em']

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
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    )

    equipamento     = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='planos_manutencao')
    nome_servico    = models.CharField(max_length=200, help_text="Ex: Troca de Óleo, Revisão de Rolamentos")
    descricao       = models.TextField(help_text="Detalhes do serviço a ser realizado")
    intervalo_horas = models.FloatField(help_text="A cada quantas horas este serviço deve ser realizado")
    prioridade      = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='media')
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
