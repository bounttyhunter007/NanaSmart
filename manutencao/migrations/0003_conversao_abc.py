from django.db import migrations


def converter(apps, schema_editor):
    Ordem = apps.get_model('manutencao', 'OrdemServico')
    Historico = apps.get_model('manutencao', 'HistoricoPrioridadeOS')
    db = schema_editor.connection.alias
    classes = {'critica': 'A', 'alta': 'A', 'media': 'B', 'baixa': 'C', 'A': 'A', 'B': 'B', 'C': 'C'}
    for ordem in Ordem.objects.using(db).all().iterator():
        nova = classes.get(ordem.prioridade)
        Historico.objects.using(db).create(
            ordem_servico_id=ordem.pk, prioridade_anterior=ordem.prioridade, prioridade_nova=nova,
            origem='migracao', justificativa='Conversão dos níveis legados para ABC, sem recalcular a OS.',
            dados_anteriores={
                'prioridade': ordem.prioridade, 'prioridade_automatica': ordem.prioridade_automatica,
                'prioridade_manual': ordem.prioridade_manual, 'justificativa': ordem.justificativa_prioridade,
                'criticidade_na_abertura': ordem.criticidade_na_abertura,
                'justificativa_criticidade_na_abertura': ordem.justificativa_criticidade_na_abertura,
            },
        )
        # A matriz antiga não comprovava herança da classe. Não inventar esse vínculo.
        Ordem.objects.using(db).filter(pk=ordem.pk).update(
            prioridade=nova, prioridade_automatica=classes.get(ordem.prioridade_automatica),
            prioridade_origem='convertida', prioridade_herdada_conhecida=False,
        )


def restaurar(apps, schema_editor):
    Ordem = apps.get_model('manutencao', 'OrdemServico')
    Historico = apps.get_model('manutencao', 'HistoricoPrioridadeOS')
    db = schema_editor.connection.alias
    for registro in Historico.objects.using(db).filter(origem='migracao').iterator():
        dados = registro.dados_anteriores
        Ordem.objects.using(db).filter(pk=registro.ordem_servico_id).update(
            prioridade=dados['prioridade'], prioridade_automatica=dados['prioridade_automatica'])
    Historico.objects.using(db).filter(origem='migracao').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('ativos', '0003_conversao_abc'),
        ('manutencao', '0002_ordemservico_criterios_criticidade_na_abertura_and_more'),
    ]
    operations = [migrations.RunPython(converter, restaurar)]
