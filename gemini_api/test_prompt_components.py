from django.test import SimpleTestCase

from .prompt import Prompt
from .prompt_builder_pattern import PromptBuilderConcreto
from .prompt_components import GrupoPrompt, TrechoPrompt
from .prompt_director import PromptDirector


class PromptCompositeTests(SimpleTestCase):
    def test_group_does_not_retain_a_mutable_children_list(self):
        children = [TrechoPrompt('Primeiro')]
        group = GrupoPrompt(children)
        children.append(TrechoPrompt('Segundo'))
        self.assertEqual(group.renderizar(), 'Primeiro')

    def test_leaf_and_nested_groups_have_uniform_rendering_including_empty_sections(self):
        leaf = TrechoPrompt('Contexto')
        nested = GrupoPrompt((leaf, GrupoPrompt((TrechoPrompt('A'), TrechoPrompt('B')))))
        self.assertEqual(leaf.renderizar(), 'Contexto')
        self.assertEqual(nested.renderizar(), 'Contexto\nA\nB')
        self.assertEqual(GrupoPrompt(()).renderizar(), '')
        self.assertEqual(GrupoPrompt((TrechoPrompt(''), nested)).renderizar(), '\nContexto\nA\nB')

    def test_chat_director_preserves_exact_prompt_text(self):
        builder = PromptBuilderConcreto()
        context = {
            'alert_summary': ['Alerta A', '- Alerta B'],
            'open_order_summary': ['OS 1'], 'equipment_kpis': ['KPI 1'],
            'telemetry': ['- 90 C'],
        }
        product = PromptDirector.montar_chat(builder, context, 'Empresa Exemplo', 'O que fazer?')
        self.assertIsInstance(product, Prompt)
        self.assertEqual(product.obter_texto(), (
            'Empresa Exemplo\n\nALERTAS RELEVANTES:\n- Alerta A\n- Alerta B'
            '\n\nORDENS EM ABERTO:\n- OS 1\n\nKPIs DE EQUIPAMENTOS:\n- KPI 1'
            '\n\nTELEMETRIA RECENTE:\n- 90 C\n\nPERGUNTA DO USUÁRIO:\nO que fazer?'
        ))

    def test_reset_does_not_change_the_previous_product_or_reuse_its_context(self):
        builder = PromptBuilderConcreto()
        previous = PromptDirector.montar_chat(builder, {}, 'Empresa A', 'Pergunta A')
        current = PromptDirector.montar_chat(builder, {}, 'Empresa B', 'Pergunta B')
        self.assertEqual(str(previous), 'Empresa A\n\nPERGUNTA DO USUÁRIO:\nPergunta A')
        self.assertEqual(str(current), 'Empresa B\n\nPERGUNTA DO USUÁRIO:\nPergunta B')

    def test_truncation_and_optional_blocks_keep_existing_format(self):
        builder = PromptBuilderConcreto()
        builder.com_alertas([f'Alerta {i}' for i in range(7)])
        builder.com_financeiro(['Total: 10', 'Média: 5'])
        builder.com_instrucoes('Instrução')
        text = str(builder.build())
        self.assertIn('- Alerta 4\n... (2 itens adicionais omitidos)', text)
        self.assertNotIn('Alerta 5', text)
        self.assertTrue(text.endswith('\nTotal: 10\nMédia: 5\n\nInstrução'))

    def test_other_directors_preserve_their_text(self):
        cases = [
            (PromptDirector.montar_analise_os,
             {'assigned_order_summary': ['OS A'], 'unassigned_order_summary': ['OS B']},
             'Cabeçalho\n\nORDENS ATRIBUÍDAS:\n- OS A\n\nORDENS SEM ATRIBUIÇÃO:\n- OS B\n\nInstrução\n\nPERGUNTA DO USUÁRIO:\nPergunta'),
            (PromptDirector.montar_ordens_nao_atribuidas,
             {'unassigned_order_summary': ['OS B']},
             'Cabeçalho\n\nORDENS SEM ATRIBUIÇÃO (EXEMPLOS):\n- OS B\n\nInstrução\n\nPERGUNTA DO USUÁRIO:\nPergunta'),
            (PromptDirector.montar_financeiro,
             {'financial_summary': {'top_equipment_costs': ['Motor: 10']}},
             'Cabeçalho\n\nEQUIPAMENTOS COM MAIOR CUSTO:\n- Motor: 10\n\nInstrução\n\nPERGUNTA DO USUÁRIO:\nPergunta'),
        ]
        for director, context, expected in cases:
            with self.subTest(director=director.__name__):
                self.assertEqual(str(director(PromptBuilderConcreto(), context, 'Cabeçalho', 'Instrução', 'Pergunta')), expected)
