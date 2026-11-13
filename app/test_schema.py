"""O contrato publicado deve ser válido e refletir os formatos usados pela API."""

import json
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class OpenApiSchemaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        output = StringIO()
        # Fail on generation warnings as well as invalid OpenAPI references/types.
        call_command('spectacular', format='openapi-json', validate=True, fail_on_warn=True, stdout=output)
        cls.schema = json.loads(output.getvalue())
        cls.components = cls.schema['components']['schemas']

    def test_operation_ids_are_unique_and_demo_has_distinct_requests_and_status_codes(self):
        operations = [
            operation for path in self.schema['paths'].values()
            for method, operation in path.items()
            if method in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options')
        ]
        ids = [operation['operationId'] for operation in operations]
        self.assertEqual(len(ids), len(set(ids)))
        collection = self.schema['paths']['/api/telemetria/tendencias/demo/']
        detail = self.schema['paths']['/api/telemetria/tendencias/demo/{demo_id}/']
        create = collection['post']
        update = detail['post']
        self.assertIn('201', create['responses'])
        self.assertNotIn('200', create['responses'])
        self.assertIn('200', update['responses'])
        self.assertIn('empresa', self.components['DemoCreateRequest']['required'])
        self.assertNotIn('empresa', self.components['DemoUpdateRequest']['properties'])
        self.assertNotEqual(
            create['requestBody']['content']['application/json']['schema'],
            update['requestBody']['content']['application/json']['schema'],
        )
        for operation in (collection['get'], create, detail['get'], update):
            response = operation['responses'].get('201') or operation['responses']['200']
            self.assertEqual(
                response['content']['application/json']['schema'],
                {'$ref': '#/components/schemas/TrendDemoSnapshot'},
            )

    def test_alert_computed_fields_have_correct_types_and_nullability(self):
        fields = self.components['Alerta']['properties']
        self.assertEqual(fields['ordem_servico_id']['type'], 'integer')
        self.assertTrue(fields['ordem_servico_id']['nullable'])
        self.assertEqual(fields['sensor_nome']['type'], 'string')
        self.assertEqual(fields['legado']['type'], 'boolean')
        demo_fields = self.components['DemoAlert']['properties']
        self.assertEqual(demo_fields['ordem_servico_id']['type'], 'integer')
        self.assertTrue(demo_fields['ordem_servico_id']['nullable'])
        analysis = self.components['TrendDemoSnapshot']['properties']['analysis']
        self.assertEqual(analysis['type'], 'object')
        self.assertTrue(analysis['nullable'])

    def test_priority_and_criticality_choices_keep_their_distinct_values_and_meanings(self):
        priority = self.components['PrioridadeOSEnum']
        criticality = self.components['CriticidadeEquipamentoEnum']
        plan = self.components['PrioridadePlanoManutencaoEnum']
        self.assertEqual(priority['enum'], ['A', 'B', 'C'])
        self.assertEqual(criticality['enum'], ['A', 'B', 'C'])
        self.assertNotEqual(priority['description'], criticality['description'])
        self.assertEqual(plan['enum'], ['baixa', 'media', 'alta', 'critica'])
