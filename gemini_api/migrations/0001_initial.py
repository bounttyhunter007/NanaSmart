from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PromptConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(choices=[('system_instruction_tecnico', 'Instrução de Sistema — Técnico'), ('system_instruction_gestor', 'Instrução de Sistema — Gestor'), ('system_instruction_admin', 'Instrução de Sistema — Administrador'), ('chat_context', 'Contextualização do Chat'), ('os_analysis', 'Análise de Ordens de Serviço'), ('unassigned_orders', 'Ordens Sem Atribuição'), ('finance', 'Gestão Financeira'), ('trend_analysis', 'Explicação de Tendência')], help_text='Tipo de prompt a ser customizado.', max_length=50, unique=True)),
                ('label', models.CharField(blank=True, help_text='Nome amigável do prompt (exibido no frontend).', max_length=120)),
                ('custom_text', models.TextField(blank=True, default='', help_text='Texto customizado do prompt. Se vazio, usa o prompt original.')),
                ('original_text', models.TextField(blank=True, default='', help_text='Texto original do prompt (preenchido automaticamente na criação).')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuração de Prompt',
                'verbose_name_plural': 'Configurações de Prompt',
                'ordering': ['key'],
            },
        ),
    ]
