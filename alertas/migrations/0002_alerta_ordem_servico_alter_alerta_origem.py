import django.db.models.deletion
from django.db import migrations, models


def vincular_origens_conhecidas(apps, schema_editor):
    Alerta = apps.get_model('alertas', 'Alerta')
    OrdemServico = apps.get_model('manutencao', 'OrdemServico')
    alias = schema_editor.connection.alias
    for ordem in OrdemServico.objects.using(alias).exclude(alerta_origem_id=None).iterator():
        Alerta.objects.using(alias).filter(
            pk=ordem.alerta_origem_id, equipamento_id=ordem.equipamento_id,
            ordem_servico_id=None,
        ).update(ordem_servico_id=ordem.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('alertas', '0001_initial'),
        ('manutencao', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='alerta',
            name='ordem_servico',
            field=models.ForeignKey(blank=True, help_text='Ordem que atende esta ocorrência; pode atender outras recorrências.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas_relacionados', to='manutencao.ordemservico'),
        ),
        migrations.AlterField(
            model_name='alerta',
            name='origem',
            field=models.CharField(choices=[('limite', 'Limite operacional'), ('tendencia', 'Tendência preditiva'), ('manual', 'Manual')], default='manual', max_length=20),
        ),
        migrations.RunPython(vincular_origens_conhecidas, migrations.RunPython.noop),
    ]
