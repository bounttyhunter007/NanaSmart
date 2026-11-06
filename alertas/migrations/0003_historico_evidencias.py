from django.db import migrations, models
import django.db.models.deletion
from django.utils.dateparse import parse_datetime


def preserve_legacy(apps, schema_editor):
    Alerta = apps.get_model('alertas', 'Alerta')
    for alerta in Alerta.objects.using(schema_editor.connection.alias).all().iterator():
        # O acompanhamento antigo não prova quais eram os dados na abertura.
        alerta.dados_deteccao = {'legado': True}
        recovered = (alerta.dados_analise or {}).get('recuperado_em')
        if isinstance(recovered, str):
            try:
                alerta.data_normalizacao = parse_datetime(recovered)
            except ValueError:
                pass
        alerta.save(update_fields=['dados_deteccao', 'data_normalizacao'])


class Migration(migrations.Migration):
    dependencies = [('alertas', '0002_alerta_ordem_servico_alter_alerta_origem')]
    operations = [
        migrations.AddField(model_name='alerta', name='dados_deteccao',
                            field=models.JSONField(default=dict, blank=True, editable=False)),
        migrations.AddField(model_name='alerta', name='data_normalizacao',
                            field=models.DateTimeField(null=True, blank=True, editable=False)),
        migrations.AlterField(model_name='alerta', name='equipamento',
                              field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                      related_name='alertas', to='ativos.equipamento')),
        migrations.RunPython(preserve_legacy, migrations.RunPython.noop),
    ]
