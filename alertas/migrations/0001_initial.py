import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ativos', '0001_initial'),
        ('telemetria', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alerta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_alerta', models.CharField(max_length=100)),
                ('origem', models.CharField(choices=[('limite', 'Limite operacional'), ('tendencia', 'Tendência preditiva'), ('manual', 'Manual')], default='limite', max_length=20)),
                ('evento_chave', models.CharField(blank=True, db_index=True, default='', help_text='Identificador estável do episódio para reprocessamento idempotente.', max_length=160)),
                ('dados_analise', models.JSONField(blank=True, default=dict)),
                ('analise_ia', models.TextField(blank=True, default='')),
                ('data_ultima_analise', models.DateTimeField(blank=True, null=True)),
                ('nivel', models.CharField(choices=[('baixo', 'Baixo'), ('medio', 'Médio'), ('critico', 'Crítico')], default='baixo', max_length=20)),
                ('descricao', models.TextField()),
                ('data_alerta', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('resolvido', 'Resolvido'), ('ignorado', 'Ignorado')], default='ativo', max_length=20)),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to='ativos.equipamento')),
                ('sensor', models.ForeignKey(blank=True, help_text='Sensor que originou o alerta, quando aplicável.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas', to='telemetria.sensor')),
            ],
            options={
                'constraints': [models.UniqueConstraint(condition=models.Q(('status', 'ativo'), models.Q(('evento_chave', ''), _negated=True)), fields=('evento_chave',), name='alerta_evento_ativo_unico')],
            },
        ),
    ]
