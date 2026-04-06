from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Tabela EMPRESA
class Empresa(models.Model):
    nome = models.CharField(max_length=255) 
    cnpj = models.CharField(max_length=18, unique=True) 
    email = models.EmailField() 
    telefone = models.CharField(max_length=20, blank=True, null=True) 
    endereco = models.TextField(blank=True, null=True) 
    data_cadastro = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.nome

# 2. Tabela USUARIO (Unificada com TECNICO)
class Usuario(AbstractUser):
    # Opções baseadas no seu DER (admin, técnico, gestor) 
    TIPO_USUARIO_CHOICES = (
        ('admin', 'Administrador'),
        ('gestor', 'Gestor'),
        ('tecnico', 'Técnico'),
    )
    
  
    # Chave Estrangeira (FK) ligando o Usuário à Empresa 
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='usuarios',
        null=True, 
        blank=True
    )
    
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES, default='tecnico') 
    cargo = models.CharField(max_length=100, blank=True, null=True) # Ex: Eletricista Sênior, Mecânico 
        
    telefone = models.CharField(max_length=20, blank=True, null=True) # [cite: 163]

    def __str__(self):
        # Vai mostrar no painel: "joao.silva (Técnico) - Indústria XPTO"
        return f"{self.username} ({self.get_tipo_usuario_display()}) - {self.empresa}"