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
    planta = models.CharField(max_length=100)
    coordenada = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Lat/Long ou Grid ID")

    def __str__(self):
        return f"Localização: {self.setor} - {self.planta} ({self.equipamento.nome})"