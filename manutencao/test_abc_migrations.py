from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ConversaoABCMigrationTests(TransactionTestCase):
    def test_converte_preservando_valores_lacunas_e_historicos(self):
        executor = MigrationExecutor(connection)
        anteriores = [('ativos', '0001_initial'), ('manutencao', '0001_initial')]
        executor.migrate(anteriores)
        try:
            apps = executor.loader.project_state(anteriores).apps
            Empresa = apps.get_model('accounts', 'Empresa')
            Equipamento = apps.get_model('ativos', 'Equipamento')
            Tipo = apps.get_model('ativos', 'TipoEquipamento')
            Historico = apps.get_model('ativos', 'HistoricoCriticidadeEquipamento')
            Ordem = apps.get_model('manutencao', 'OrdemServico')
            empresa = Empresa.objects.create(nome='Legado ABC', cnpj='MIG-ABC', email='mig@example.com')
            equipamento = Equipamento.objects.create(empresa=empresa, nome='Motor legado', numero_serie='MIG-ABC',
                criticidade='D', criticidade_origem='individual', justificativa_criticidade='Avaliação anterior válida.')
            tipo = Tipo.objects.create(empresa=empresa, nome='Tipo legado', criticidade_padrao='D')
            historico = Historico.objects.create(equipamento=equipamento, criticidade_anterior='C', criticidade_nova='D', justificativa='Registro original.')
            ids = []
            for prioridade in ('critica', 'alta', 'media', 'baixa'):
                ordem = Ordem.objects.create(equipamento=equipamento,
                    titulo='OS legada', descricao='Preservar texto', prioridade=prioridade,
                    prioridade_automatica=prioridade, prioridade_manual=True, justificativa_prioridade='Motivo original.',
                    criticidade_na_abertura='D', justificativa_criticidade_na_abertura='Retrato original.')
                ids.append(ordem.pk)
            lacuna = Ordem.objects.create(equipamento=equipamento, titulo='Sem retrato', descricao='Sem inferência',
                                         prioridade='media', prioridade_automatica='', criticidade_na_abertura=None)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            apps = executor.loader.project_state(executor.loader.graph.leaf_nodes()).apps
            Equipamento = apps.get_model('ativos', 'Equipamento')
            Tipo = apps.get_model('ativos', 'TipoEquipamento')
            Historico = apps.get_model('ativos', 'HistoricoCriticidadeEquipamento')
            Ordem = apps.get_model('manutencao', 'OrdemServico')
            Prioridades = apps.get_model('manutencao', 'HistoricoPrioridadeOS')
            equipamento = Equipamento.objects.get(pk=equipamento.pk)
            self.assertEqual(equipamento.criticidade, 'C')
            self.assertIsNone(equipamento.criterios_criticidade_id)
            self.assertEqual(Tipo.objects.get(pk=tipo.pk).criticidade_padrao, 'C')
            self.assertEqual(Tipo.objects.get(pk=tipo.pk).criticidade_padrao_legada, 'D')
            original = Historico.objects.get(pk=historico.pk)
            self.assertEqual(original.criticidade_nova, 'D')
            self.assertEqual(original.justificativa, 'Registro original.')
            self.assertEqual(Historico.objects.filter(equipamento=equipamento, origem='migracao').get().dados_anteriores['criticidade'], 'D')
            for pk, original, esperado in zip(ids, ('critica', 'alta', 'media', 'baixa'), ('A', 'A', 'B', 'C')):
                ordem = Ordem.objects.get(pk=pk)
                self.assertEqual(ordem.prioridade, esperado)
                self.assertEqual(ordem.prioridade_automatica, esperado)
                self.assertEqual(ordem.criticidade_na_abertura, 'D')
                self.assertEqual(ordem.justificativa_criticidade_na_abertura, 'Retrato original.')
                self.assertEqual(ordem.justificativa_prioridade, 'Motivo original.')
                self.assertTrue(ordem.prioridade_manual)
                self.assertFalse(ordem.prioridade_herdada_conhecida)
                self.assertEqual(Prioridades.objects.get(ordem_servico_id=pk).dados_anteriores['prioridade'], original)
            lacuna = Ordem.objects.get(pk=lacuna.pk)
            self.assertIsNone(lacuna.criticidade_na_abertura)
            self.assertIsNone(lacuna.prioridade_automatica)
            self.assertFalse(lacuna.prioridade_herdada_conhecida)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
