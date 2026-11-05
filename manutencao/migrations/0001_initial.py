import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('alertas', '0001_initial'),
        ('ativos', '0001_initial'),
        ('telemetria', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrdemServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_os', models.CharField(choices=[('corretiva', 'Corretiva'), ('preditiva', 'Preditiva'), ('preventiva', 'Preventiva')], default='preventiva', max_length=20)),
                ('titulo', models.CharField(max_length=200)),
                ('descricao', models.TextField(help_text='Descreva o problema ou o serviço a ser realizado')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('andamento', 'Em Andamento'), ('concluida', 'Concluída'), ('cancelada', 'Cancelada')], default='pendente', max_length=20)),
                ('prioridade', models.CharField(choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta'), ('critica', 'Crítica')], default='baixa', max_length=20)),
                ('gravidade_condicao', models.CharField(choices=[('ausente', 'Não informada'), ('baixa', 'Baixa'), ('moderada', 'Moderada'), ('alta', 'Alta'), ('critica', 'Crítica')], default='ausente', max_length=20)),
                ('risco_seguranca', models.BooleanField(default=False)),
                ('prioridade_manual', models.BooleanField(default=False)),
                ('prioridade_automatica', models.CharField(blank=True, choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta'), ('critica', 'Crítica')], max_length=20)),
                ('justificativa_prioridade', models.TextField(blank=True)),
                ('criticidade_na_abertura', models.CharField(blank=True, max_length=1, null=True)),
                ('justificativa_criticidade_na_abertura', models.TextField(blank=True)),
                ('data_abertura', models.DateTimeField(default=django.utils.timezone.now)),
                ('data_conclusao', models.DateTimeField(blank=True, null=True)),
                ('alerta_origem', models.OneToOneField(blank=True, help_text='Alerta que originou a ordem automática, quando aplicável.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordem_servico_preditiva', to='alertas.alerta')),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordens_servico', to='ativos.equipamento')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='minhas_os', to=settings.AUTH_USER_MODEL)),
                ('sensor_origem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordens_servico_origem', to='telemetria.sensor')),
            ],
        ),
        migrations.CreateModel(
            name='HistoricoManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao_servico', models.TextField()),
                ('data_execucao', models.DateField()),
                ('custo_pecas', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('custo_mao_de_obra', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('ordem_servico', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='manutencao.ordemservico')),
            ],
        ),
    ]
