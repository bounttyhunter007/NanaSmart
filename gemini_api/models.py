from django.db import models


class PromptAnaliseOS(models.Model):
    """Personalização da análise individual, isolada dos prompts globais."""

    empresa = models.OneToOneField(
        'accounts.Empresa', on_delete=models.CASCADE, related_name='prompt_analise_os',
    )
    custom_text = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)


class PromptConfig(models.Model):
    """
    Stores custom prompt configurations for the Gemini AI.
    Each 'key' represents a specific prompt type (e.g., system_instruction, chat, os_analysis, etc.).
    Only one active config per key is allowed at a time.
    """
    PROMPT_KEYS = [
        ('system_instruction_tecnico', 'Instrução de Sistema — Técnico'),
        ('system_instruction_gestor', 'Instrução de Sistema — Gestor'),
        ('system_instruction_admin', 'Instrução de Sistema — Administrador'),
        ('chat_context', 'Contextualização do Chat'),
        ('os_analysis', 'Análise de Ordens de Serviço'),
        ('unassigned_orders', 'Ordens Sem Atribuição'),
        ('finance', 'Gestão Financeira'),
        ('trend_analysis', 'Explicação de Tendência'),
    ]

    key = models.CharField(
        max_length=50,
        choices=PROMPT_KEYS,
        unique=True,
        help_text='Tipo de prompt a ser customizado.',
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        help_text='Nome amigável do prompt (exibido no frontend).',
    )
    custom_text = models.TextField(
        blank=True,
        default='',
        help_text='Texto customizado do prompt. Se vazio, usa o prompt original.',
    )
    original_text = models.TextField(
        blank=True,
        default='',
        help_text='Texto original do prompt (preenchido automaticamente na criação).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']
        verbose_name = 'Configuração de Prompt'
        verbose_name_plural = 'Configurações de Prompt'

    def __str__(self):
        return f'{self.get_key_display()} ({self.key})'

    @property
    def is_customized(self):
        return bool(self.custom_text.strip())

    @property
    def effective_text(self):
        """Returns custom_text if set, otherwise original_text."""
        return self.custom_text.strip() if self.custom_text.strip() else self.original_text
