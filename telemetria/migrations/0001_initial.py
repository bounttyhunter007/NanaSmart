import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ativos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sensor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[('temperatura', 'Temperatura'), ('vibracao', 'Vibração'), ('pressao', 'Pressão'), ('corrente', 'Corrente Elétrica'), ('umidade', 'Umidade')], max_length=50)),
                ('unidade_medida', models.CharField(help_text='Ex: °C, mm/s, bar, A', max_length=20)),
                ('limite_alerta', models.FloatField(help_text='Limite máximo para gerar alerta crítico')),
                ('limite_alerta_baixo_pct', models.FloatField(blank=True, help_text='Percentual do limite crítico que dispara alerta baixo (0-100).', null=True, verbose_name='Alerta Baixo (%)')),
                ('limite_alerta_medio_pct', models.FloatField(blank=True, help_text='Percentual do limite crítico que dispara alerta médio (0-100).', null=True, verbose_name='Alerta Médio (%)')),
                ('limite_alerta_critico_pct', models.FloatField(blank=True, help_text='Percentual do limite crítico que dispara alerta crítico (0-100).', null=True, verbose_name='Alerta Crítico (%)')),
                ('descricao', models.TextField(blank=True, null=True)),
                ('ativo', models.BooleanField(default=True)),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sensores', to='ativos.equipamento')),
            ],
        ),
        migrations.CreateModel(
            name='Telemetria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', models.FloatField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leituras', to='telemetria.sensor')),
            ],
            options={
                'verbose_name_plural': 'Telemetrias',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='TrendConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo_horas', models.IntegerField(default=24, help_text='Período de análise em horas')),
                ('num_leituras', models.IntegerField(default=50, help_text='Número máximo de leituras para análise')),
                ('sensibilidade', models.CharField(choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta')], default='media', max_length=20)),
                ('ativo', models.BooleanField(default=True)),
                ('sensor', models.OneToOneField(blank=True, help_text='Se null, é a configuração global padrão', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trend_config', to='telemetria.sensor')),
            ],
            options={
                'verbose_name': 'Configuração de Tendência',
                'verbose_name_plural': 'Configurações de Tendência',
            },
        ),
    ]
