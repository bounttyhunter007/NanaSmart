from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AlertLinkMigrationTests(TransactionTestCase):
    def test_evidencias_legadas_nao_inventam_dados_da_abertura(self):
        executor = MigrationExecutor(connection)
        anterior = [('alertas', '0002_alerta_ordem_servico_alter_alerta_origem'), ('manutencao', '0001_initial'), ('ativos', '0001_initial')]
        atual = [('alertas', '0003_historico_evidencias')]
        executor.migrate(anterior)
        try:
            apps = executor.loader.project_state(anterior).apps
            Empresa = apps.get_model('accounts', 'Empresa')
            Equipamento = apps.get_model('ativos', 'Equipamento')
            Alerta = apps.get_model('alertas', 'Alerta')
            Ordem = apps.get_model('manutencao', 'OrdemServico')
            empresa = Empresa.objects.create(nome='Legado', cnpj='LEGADO', email='l@example.com')
            equipamento = Equipamento.objects.create(empresa=empresa, nome='Motor', numero_serie='LEGADO')
            conhecido = Alerta.objects.create(
                equipamento=equipamento, tipo_alerta='Limite', origem='limite', descricao='Texto antigo',
                status='ignorado', dados_analise={'recuperado_em': '2026-11-05T12:00:00+00:00', 'ultimo_valor': 10},
            )
            manual = Alerta.objects.create(equipamento=equipamento, tipo_alerta='Manual', origem='manual',
                                          descricao='Sem dados iniciais', status='resolvido')
            ordem = Ordem.objects.create(equipamento=equipamento, alerta_origem=conhecido,
                                         titulo='Atendimento anterior', descricao='Preservar')
            Alerta.objects.filter(pk=conhecido.pk).update(ordem_servico=ordem)
            executor = MigrationExecutor(connection)
            executor.migrate(atual)
            Alerta = executor.loader.project_state(atual).apps.get_model('alertas', 'Alerta')
            conhecido = Alerta.objects.get(pk=conhecido.pk)
            manual = Alerta.objects.get(pk=manual.pk)
            self.assertEqual(conhecido.dados_deteccao, {'legado': True})
            self.assertEqual(conhecido.data_normalizacao.isoformat(), '2026-11-05T12:00:00+00:00')
            self.assertEqual(conhecido.status, 'ignorado')
            self.assertEqual(conhecido.ordem_servico_id, ordem.pk)
            self.assertEqual(conhecido.descricao, 'Texto antigo')
            self.assertEqual(manual.dados_deteccao, {'legado': True})
            self.assertIsNone(manual.data_normalizacao)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_preserva_historico_e_vincula_somente_origem_conhecida(self):
        executor = MigrationExecutor(connection)
        anterior = [('alertas', '0001_initial'), ('manutencao', '0001_initial')]
        atual = [('alertas', '0002_alerta_ordem_servico_alter_alerta_origem')]
        executor.migrate(anterior)
        try:
            apps = executor.loader.project_state(anterior).apps
            Empresa = apps.get_model('accounts', 'Empresa')
            Equipamento = apps.get_model('ativos', 'Equipamento')
            Alerta = apps.get_model('alertas', 'Alerta')
            Ordem = apps.get_model('manutencao', 'OrdemServico')
            empresa = Empresa.objects.create(nome='Migração', cnpj='MIGRA', email='m@example.com')
            equipamento = Equipamento.objects.create(empresa=empresa, nome='Motor', numero_serie='MIGRA')
            conhecido = Alerta.objects.create(
                equipamento=equipamento, tipo_alerta='Tendência', origem='tendencia',
                descricao='Histórico conhecido', status='resolvido',
            )
            legado = Alerta.objects.create(
                equipamento=equipamento, tipo_alerta='Limite', origem='limite',
                descricao='Sem sensor identificável', status='ativo',
            )
            ordem = Ordem.objects.create(
                equipamento=equipamento, alerta_origem=conhecido,
                titulo='Preditiva', descricao='Histórico preservado', status='concluida',
            )
            Ordem.objects.create(equipamento=equipamento, titulo='MANUTENÇÃO: Limite', descricao='Sem origem')
            executor = MigrationExecutor(connection)
            executor.migrate(atual)
            apps = executor.loader.project_state(atual).apps
            Alerta = apps.get_model('alertas', 'Alerta')
            self.assertEqual(Alerta.objects.get(pk=conhecido.pk).ordem_servico_id, ordem.pk)
            self.assertEqual(Alerta.objects.get(pk=conhecido.pk).status, 'resolvido')
            self.assertIsNone(Alerta.objects.get(pk=legado.pk).ordem_servico_id)
            self.assertEqual(Alerta.objects.get(pk=legado.pk).origem, 'limite')
            self.assertEqual(Alerta.objects.get(pk=legado.pk).descricao, 'Sem sensor identificável')
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
