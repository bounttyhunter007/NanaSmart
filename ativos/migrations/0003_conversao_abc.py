from django.db import migrations, models


def converter(apps, schema_editor):
    Equipamento = apps.get_model('ativos', 'Equipamento')
    Historico = apps.get_model('ativos', 'HistoricoCriticidadeEquipamento')
    Tipo = apps.get_model('ativos', 'TipoEquipamento')
    db = schema_editor.connection.alias
    Historico.objects.using(db).all().update(origem='legado')
    for equipamento in Equipamento.objects.using(db).exclude(criticidade__isnull=True).iterator():
        antiga = equipamento.criticidade
        nova = {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'C'}.get(antiga)
        Historico.objects.using(db).create(
            equipamento_id=equipamento.pk, criticidade_anterior=antiga, criticidade_nova=nova,
            justificativa='Conversão para ABC; critérios locais anteriores não foram presumidos como validados.',
            origem='migracao', dados_anteriores={
                'criticidade': antiga, 'justificativa': equipamento.justificativa_criticidade,
                'origem': equipamento.criticidade_origem, 'criterios_criticidade': None,
                'rotulos': {'A': 'Crítica', 'B': 'Alta', 'C': 'Moderada', 'D': 'Baixa'},
            },
        )
        Equipamento.objects.using(db).filter(pk=equipamento.pk).update(criticidade=nova, criticidade_origem='migracao')
    for tipo in Tipo.objects.using(db).all().iterator():
        Tipo.objects.using(db).filter(pk=tipo.pk).update(
            criticidade_padrao_legada=tipo.criticidade_padrao,
            criticidade_padrao={'A': 'A', 'B': 'B', 'C': 'C', 'D': 'C'}.get(tipo.criticidade_padrao),
        )


def restaurar(apps, schema_editor):
    Equipamento = apps.get_model('ativos', 'Equipamento')
    Historico = apps.get_model('ativos', 'HistoricoCriticidadeEquipamento')
    Tipo = apps.get_model('ativos', 'TipoEquipamento')
    db = schema_editor.connection.alias
    for registro in Historico.objects.using(db).filter(origem='migracao').iterator():
        dados = registro.dados_anteriores
        Equipamento.objects.using(db).filter(pk=registro.equipamento_id).update(
            criticidade=dados.get('criticidade'), criticidade_origem=dados.get('origem', 'nao_avaliada'))
    Historico.objects.using(db).filter(origem='migracao').delete()
    for tipo in Tipo.objects.using(db).all().iterator():
        if tipo.criticidade_padrao_legada is not None:
            Tipo.objects.using(db).filter(pk=tipo.pk).update(criticidade_padrao=tipo.criticidade_padrao_legada)


class Migration(migrations.Migration):
    dependencies = [('ativos', '0002_historicocriticidadeequipamento_dados_anteriores_and_more')]
    operations = [
        migrations.AddField(model_name='tipoequipamento', name='criticidade_padrao_legada',
                            field=models.CharField(max_length=20, null=True, blank=True, editable=False)),
        migrations.RunPython(converter, restaurar),
    ]
