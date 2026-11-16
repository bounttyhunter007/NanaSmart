from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import SimpleTestCase
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento
from .utils import ExportadorFactory
from .utils.base_exporter import Exportador
from .utils.catalog import CatalogoExportadores
from .utils.creators import CriadorExportador, CriadorExportadorCSV
from .utils.decorators import ExportadorComLog
from .utils.download_metadata import MetadadosCSV
from .utils.families import FamiliaCSV, FamiliaExcel, FamiliaPDF


class ExportacaoPatternsTests(SimpleTestCase):
    def test_singleton_has_one_identity_even_between_threads_and_keeps_registration(self):
        catalog = CatalogoExportadores()
        with patch.dict(catalog._registro):
            catalog.registrar('teste_catalogo', CriadorExportadorCSV)
            with ThreadPoolExecutor(max_workers=8) as executor:
                instances = list(executor.map(lambda _: CatalogoExportadores(), range(64)))
            self.assertTrue(all(instance is catalog for instance in instances))
            self.assertEqual(CatalogoExportadores().resolver('teste_catalogo'), (CriadorExportadorCSV, None))

    def test_families_generate_matching_content_type_extension_and_file(self):
        cases = [
            (FamiliaCSV, 'csv', 'text/csv; charset=utf-8', b'\xef\xbb\xbf'),
            (FamiliaExcel, 'xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', b'PK'),
            (FamiliaPDF, 'pdf', 'application/pdf', b'%PDF'),
        ]
        for family_type, extension, mime, magic in cases:
            with self.subTest(family=family_type.__name__):
                family = family_type()
                response = family.criar_exportador().exportar('relatorio', 'Relatório', ['Nome'], [['Motor á']])
                self.assertEqual(response['Content-Type'], mime)
                self.assertEqual(response['Content-Disposition'], f'attachment; filename="relatorio.{extension}"')
                self.assertTrue(response.content.startswith(magic))
                if extension == 'csv':
                    self.assertEqual(response.content.decode('utf-8-sig'), 'Nome\r\nMotor á\r\n')
                if extension == 'xlsx':
                    sheet = load_workbook(BytesIO(response.content)).active
                    self.assertEqual(list(sheet.values), [('Nome',), ('Motor á',)])

    def test_family_injects_its_metadata_product_into_the_exporter(self):
        metadata = Mock(wraps=MetadadosCSV())
        with patch.object(FamiliaCSV, 'criar_metadados', return_value=metadata):
            response = FamiliaCSV().criar_exportador().exportar('arquivo', 'Título', ['A'], [[1]])
        metadata.aplicar.assert_called_once_with(response, 'arquivo')
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

    def test_factory_keeps_legacy_creator_registration_and_shared_catalog(self):
        result = HttpResponse(b'conteudo original', content_type='application/octet-stream')

        class ExportadorTeste(Exportador):
            def exportar(self, nome, titulo, colunas, linhas):
                return result

        class CriadorTeste(CriadorExportador):
            def criar_exportador(self):
                return ExportadorTeste()

        with patch.dict(CatalogoExportadores()._registro):
            ExportadorFactory.registrar('teste_legado', CriadorTeste)
            response = ExportadorFactory.criar('teste_legado').exportar('n', 't', [], [])
            self.assertIs(response, result)
            self.assertEqual(CatalogoExportadores().resolver('teste_legado'), (CriadorTeste, None))

    def test_factory_rejects_unknown_format_and_invalid_registrations(self):
        with self.assertRaises(ValueError):
            ExportadorFactory.criar('inexistente')
        with self.assertRaises(TypeError):
            ExportadorFactory.registrar('invalido', object)
        with self.assertRaises(TypeError):
            ExportadorFactory.registrar('invalido', CriadorExportadorCSV, familia_cls=object)

    def test_decorators_can_be_nested_without_changing_response_or_logging_cells(self):
        result = HttpResponse(b'valor privado', content_type='text/csv')
        wrapped = Mock(spec=Exportador)
        wrapped.exportar.return_value = result
        decorator = ExportadorComLog(ExportadorComLog(wrapped))
        with self.assertLogs('exportacao.utils.decorators', level='INFO') as logs:
            response = decorator.exportar('n', 't', ['coluna privada'], [['valor privado']])
        self.assertIs(response, result)
        wrapped.exportar.assert_called_once_with('n', 't', ['coluna privada'], [['valor privado']])
        self.assertEqual(len(logs.output), 2)
        self.assertNotIn('valor privado', ' '.join(logs.output))
        self.assertNotIn('coluna privada', ' '.join(logs.output))

    def test_decorator_propagates_generation_failure_without_logging_success(self):
        wrapped = Mock(spec=Exportador)
        wrapped.exportar.side_effect = RuntimeError('falha de geração')
        with patch('exportacao.utils.decorators.logger.info') as log:
            with self.assertRaisesRegex(RuntimeError, 'falha de geração'):
                ExportadorComLog(wrapped).exportar('n', 't', [], [])
        log.assert_not_called()


class ExportacaoPatternsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Empresa.objects.create(nome='Empresa permitida', cnpj='PADROES-A', email='a@example.com')
        other = Empresa.objects.create(nome='Outra empresa', cnpj='PADROES-B', email='b@example.com')
        cls.manager = Usuario.objects.create_user(username='gestor_padroes', tipo_usuario='gestor', empresa=cls.company)
        Equipamento.objects.create(empresa=cls.company, nome='Motor permitido', numero_serie='MOTOR-PADROES-A')
        Equipamento.objects.create(empresa=other, nome='Motor secreto', numero_serie='MOTOR-PADROES-B')

    def test_export_endpoints_use_families_and_decorator_without_cross_company_data(self):
        self.client.force_authenticate(self.manager)
        for fmt, extension, magic in [('csv', 'csv', b'\xef\xbb\xbf'), ('excel', 'xlsx', b'PK'), ('pdf', 'pdf', b'%PDF')]:
            with self.subTest(format=fmt):
                with self.assertLogs('exportacao.utils.decorators', level='INFO'):
                    response = self.client.get(reverse('exportar-equipamentos', args=[fmt]))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content.startswith(magic))
                self.assertEqual(response['Content-Disposition'], f'attachment; filename="equipamentos.{extension}"')
                if fmt == 'csv':
                    content = response.content.decode('utf-8-sig')
                    self.assertIn('Motor permitido', content)
                    self.assertNotIn('Motor secreto', content)
                elif fmt == 'excel':
                    values = list(load_workbook(BytesIO(response.content)).active.values)
                    self.assertEqual(len(values), 2)
                    self.assertIn('Motor permitido', values[1])

    def test_invalid_format_and_anonymous_access_keep_existing_status_codes(self):
        self.assertEqual(self.client.get(reverse('exportar-equipamentos', args=['csv'])).status_code, 401)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(reverse('exportar-equipamentos', args=['inexistente'])).status_code, 400)
