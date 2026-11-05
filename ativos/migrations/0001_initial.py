import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('tipo', models.CharField(blank=True, help_text='Ex: Motor elétrico, Bomba Hidráulica', max_length=100, null=True)),
                ('fabricante', models.CharField(blank=True, max_length=100, null=True)),
                ('modelo', models.CharField(blank=True, max_length=100, null=True)),
                ('numero_serie', models.CharField(max_length=100, unique=True)),
                ('descricao', models.TextField(blank=True, help_text='Descrição do equipamento', null=True)),
                ('data_instalacao', models.DateField(blank=True, null=True)),
                ('horimetro', models.FloatField(default=0, help_text='Horas de operação do equipamento')),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('manutencao', 'Em Manutenção'), ('inativo', 'Inativo')], default='ativo', max_length=20)),
                ('criticidade', models.CharField(blank=True, choices=[('A', 'A — Crítica'), ('B', 'B — Alta'), ('C', 'C — Moderada'), ('D', 'D — Baixa')], help_text='Classe A/B/C/D; nulo significa que a avaliação ainda não foi feita.', max_length=1, null=True)),
                ('criticidade_origem', models.CharField(choices=[('nao_avaliada', 'Não avaliada'), ('tipo', 'Sugerida pelo tipo'), ('individual', 'Avaliação individual')], default='nao_avaliada', max_length=20)),
                ('justificativa_criticidade', models.TextField(blank=True, help_text='Justificativa da avaliação individual ou da sugestão aceita.')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipamentos', to='accounts.empresa')),
            ],
        ),
        migrations.CreateModel(
            name='EquipamentoLocalizacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('setor', models.CharField(max_length=100)),
                ('equipamento', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='localizacao', to='ativos.equipamento')),
            ],
        ),
        migrations.CreateModel(
            name='HistoricoCriticidadeEquipamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criticidade_anterior', models.CharField(blank=True, max_length=1, null=True)),
                ('criticidade_nova', models.CharField(blank=True, choices=[('A', 'A — Crítica'), ('B', 'B — Alta'), ('C', 'C — Moderada'), ('D', 'D — Baixa')], max_length=1, null=True)),
                ('justificativa', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('alterado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico_criticidade', to='ativos.equipamento')),
            ],
            options={
                'ordering': ['-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='PlanoManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_servico', models.CharField(help_text='Ex: Troca de Óleo, Revisão de Rolamentos', max_length=200)),
                ('descricao', models.TextField(help_text='Detalhes do serviço a ser realizado')),
                ('intervalo_horas', models.FloatField(help_text='A cada quantas horas este serviço deve ser realizado')),
                ('prioridade', models.CharField(choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta'), ('critica', 'Crítica')], default='media', max_length=20)),
                ('ativo', models.BooleanField(default=True)),
                ('horimetro_ultima_os', models.FloatField(default=0, help_text='Horímetro do equipamento no momento em que a última O.S. foi gerada')),
                ('equipamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='planos_manutencao', to='ativos.equipamento')),
            ],
        ),
        migrations.CreateModel(
            name='TipoEquipamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('criticidade_padrao', models.CharField(blank=True, choices=[('A', 'A — Crítica'), ('B', 'B — Alta'), ('C', 'C — Moderada'), ('D', 'D — Baixa')], max_length=1, null=True)),
                ('descricao_criterios', models.TextField(blank=True, help_text='Critérios locais que justificam a sugestão.')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tipos_equipamento', to='accounts.empresa')),
            ],
            options={
                'ordering': ['nome'],
            },
        ),
        migrations.AddField(
            model_name='equipamento',
            name='tipo_equipamento',
            field=models.ForeignKey(blank=True, help_text='Catálogo opcional; sua criticidade é apenas uma sugestão inicial.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipamentos', to='ativos.tipoequipamento'),
        ),
        migrations.AddConstraint(
            model_name='tipoequipamento',
            constraint=models.UniqueConstraint(fields=('empresa', 'nome'), name='tipo_equipamento_por_empresa_unico'),
        ),
    ]
