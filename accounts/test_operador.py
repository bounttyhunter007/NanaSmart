from rest_framework.test import APITestCase

from accounts.models import Empresa, Usuario
from alertas.models import Alerta
from ativos.models import Equipamento, EquipamentoLocalizacao
from manutencao.models import OrdemServico
from manutencao.visibility import visible_work_orders


class OperadorAccessTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Operação', cnpj='111', email='a@example.com')
        self.outra_empresa = Empresa.objects.create(nome='Outra', cnpj='222', email='b@example.com')
        self.operador = Usuario.objects.create_user(username='operador', password='senha123', empresa=self.empresa)
        self.client.force_authenticate(self.operador)
        self.equipamentos = [Equipamento.objects.create(
            empresa=empresa, nome=f'Motor {i}', numero_serie=f'OP-{i}', criticidade='B',
        ) for i, empresa in enumerate([self.empresa, self.outra_empresa])]
        self.locais = [EquipamentoLocalizacao.objects.create(equipamento=eq, setor='Produção')
                       for eq in self.equipamentos]
        self.alertas = [Alerta.objects.create(equipamento=eq, tipo_alerta='Temperatura',
                                            descricao='Verificar motor', nivel='critico')
                        for eq in self.equipamentos]
        self.ordem = OrdemServico.objects.create(equipamento=self.equipamentos[0], titulo='Existente', descricao='Teste')

    def payload(self):
        return {'equipamento': self.equipamentos[0].pk, 'titulo': 'Ruído no motor',
                'descricao': 'Ruído observado durante a operação.', 'risco_seguranca': True}

    def test_defaults_login_and_superuser(self):
        self.assertEqual(self.operador.tipo_usuario, 'operador')
        admin = Usuario.objects.create_superuser('novo-admin', password='senha123')
        self.assertEqual(admin.tipo_usuario, 'admin')
        self.client.force_authenticate(None)
        response = self.client.post('/api/auth/login/', {'username': 'operador', 'password': 'senha123'})
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        self.assertEqual(self.client.get('/api/auth/me/').data['tipo_usuario'], 'operador')

    def test_basic_reads_are_company_scoped_and_reduced(self):
        for resource, objects in [('equipamentos', self.equipamentos), ('localizacao', self.locais),
                                  ('alertas', self.alertas)]:
            with self.subTest(resource=resource):
                response = self.client.get(f'/api/{resource}/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual([item['id'] for item in response.data['results']], [objects[0].pk])
                self.assertEqual(self.client.get(f'/api/{resource}/{objects[1].pk}/').status_code, 404)
                self.assertEqual(self.client.get(f'/api/{resource}/', {'empresa': self.outra_empresa.pk}).data['count'],
                                 1 if resource == 'localizacao' else 0)
        data = self.client.get(f'/api/equipamentos/{self.equipamentos[0].pk}/').data
        self.assertNotIn('criterios_utilizados', data)
        data = self.client.get(f'/api/alertas/{self.alertas[0].pk}/').data
        for field in ['ordem_servico_id', 'analise_ia', 'dados_analise', 'dados_deteccao']:
            self.assertNotIn(field, data)

    def test_operational_and_management_endpoints_are_forbidden(self):
        urls = ['/api/empresas/', '/api/usuarios/', '/api/tipos-equipamento/',
                '/api/criterios-criticidade/', '/api/criterios-criticidade/atual/',
                '/api/historico-criticidade/', '/api/planos-manutencao/', '/api/historico/',
                '/api/ordens-servico/', f'/api/ordens-servico/{self.ordem.pk}/',
                '/api/telemetria/sensores/', '/api/telemetria/leituras/',
                '/api/telemetria/trend-config/', '/api/telemetria/tendencias/',
                '/api/dashboards/resumo/', '/api/dashboards/kpis/', '/api/gemini/prompts/',
                '/api/gemini/prompts/analise-os/']
        urls += [f'/api/exportar/{resource}/csv/' for resource in
                 ['equipamentos', 'alertas', 'ordens-servico', 'telemetria', 'historico', 'dashboard']]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        for url in ['/api/gemini/chat/', '/api/gemini/ordens/analise/', '/api/gemini/ordens/sem-atribuicao/',
                    '/api/gemini/gestao/financeira/', '/api/gemini/tendencia/',
                    f'/api/ordens-servico/{self.ordem.pk}/analise-ia/',
                    f'/api/ordens-servico/{self.ordem.pk}/ajustar_prioridade/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}, format='json').status_code, 403)
        self.assertFalse(visible_work_orders(self.operador).exists())

    def test_operator_opens_only_pending_unassigned_manual_order(self):
        response = self.client.post('/api/ordens-servico/', self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        ordem = OrdemServico.objects.get(pk=response.data['id'])
        self.assertEqual((ordem.tipo_os, ordem.status, ordem.responsavel_id, ordem.prioridade),
                         ('corretiva', 'pendente', None, 'B'))
        self.assertTrue(ordem.risco_seguranca)
        self.assertIsNone(ordem.alerta_origem_id)
        self.assertEqual(ordem.evidencia_preditiva, {})
        self.assertEqual(self.client.patch(f'/api/ordens-servico/{ordem.pk}/', {'status': 'concluida'}).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/ordens-servico/{ordem.pk}/').status_code, 403)

    def test_creation_rejects_company_escape_and_managed_fields(self):
        before = OrdemServico.objects.count()
        for extra in [{'equipamento': self.equipamentos[1].pk}, {'status': 'concluida'},
                      {'responsavel': self.operador.pk}, {'prioridade': 'A'}, {'tipo_os': 'preditiva'},
                      {'data_abertura': '2020-01-01'}, {'custo_pecas': 100}, {'alerta_origem': self.alertas[0].pk}]:
            with self.subTest(extra=extra):
                response = self.client.post('/api/ordens-servico/', {**self.payload(), **extra}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(OrdemServico.objects.count(), before)

    def test_basic_resources_cannot_be_changed(self):
        for resource, obj in [('equipamentos', self.equipamentos[0]), ('localizacao', self.locais[0]),
                              ('alertas', self.alertas[0])]:
            self.assertEqual(self.client.post(f'/api/{resource}/', {}).status_code, 403)
            for method in [self.client.put, self.client.patch, self.client.delete]:
                self.assertEqual(method(f'/api/{resource}/{obj.pk}/').status_code, 403)

    def test_self_service_does_not_promote_or_change_company(self):
        response = self.client.patch('/api/auth/me/', {'first_name': 'Operador atualizado', 'tipo_usuario': 'admin',
                                                     'empresa': self.outra_empresa.pk, 'is_staff': True}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.first_name, 'Operador atualizado')
        self.assertEqual((self.operador.tipo_usuario, self.operador.empresa_id, self.operador.is_staff),
                         ('operador', self.empresa.pk, False))
        response = self.client.post('/api/auth/change-password/', {'senha_atual': 'senha123',
            'nova_senha': 'OutraSenhaSegura!249', 'confirmar_nova_senha': 'OutraSenhaSegura!249'})
        self.assertEqual(response.status_code, 200)

    def test_without_company_has_no_data_and_cannot_open_order(self):
        self.operador.empresa = None
        self.operador.save()
        for resource in ['equipamentos', 'localizacao', 'alertas']:
            self.assertEqual(self.client.get(f'/api/{resource}/').data['count'], 0)
        self.assertEqual(self.client.post('/api/ordens-servico/', self.payload(), format='json').status_code, 400)

    def test_manager_can_create_operator_but_cannot_assign_them(self):
        gestor = Usuario.objects.create_user('gestor', tipo_usuario='gestor', empresa=self.empresa)
        self.client.force_authenticate(gestor)
        response = self.client.post('/api/usuarios/', {'username': 'outro-operador', 'empresa': self.empresa.pk,
                                                      'tipo_usuario': 'operador'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post('/api/ordens-servico/', {**self.payload(), 'responsavel': self.operador.pk}, format='json')
        self.assertEqual(response.status_code, 400)
