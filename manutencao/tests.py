from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import OrdemServico, HistoricoManutencao
from ativos.models import Equipamento, Empresa
from accounts.models import Usuario
from .services import PrioridadeOSService

class OSTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Delta", cnpj="444", email="d@d.com")
        self.gestor = Usuario.objects.create_user(
            username="gestor_os", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.tecnico1 = Usuario.objects.create_user(
            username="tecnico_1", password="123", tipo_usuario="tecnico", empresa=self.empresa
        )
        self.tecnico2 = Usuario.objects.create_user(
            username="tecnico_2", password="123", tipo_usuario="tecnico", empresa=self.empresa
        )
        self.motor = Equipamento.objects.create(
            nome="Motor OS", tipo="Motor", numero_serie="OS-001", empresa=self.empresa
        )
        self.os_url = reverse('ordens-servico-list')

    def test_tecnico_visibility(self):
        """Testa se o técnico vê apenas O.S. sem responsável ou atribuídas a ele."""
        # 1. OS sem responsável (Todos os técnicos da empresa devem ver)
        os_livre = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Livre", descricao="Teste", responsavel=None
        )
        # 2. OS atribuída ao Tecnico 1
        os_tec1 = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Tec 1", descricao="Teste", responsavel=self.tecnico1
        )
        # 3. OS atribuída ao Tecnico 2
        os_tec2 = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Tec 2", descricao="Teste", responsavel=self.tecnico2
        )

        # Autentica como Tecnico 1
        self.client.force_authenticate(user=self.tecnico1)
        response = self.client.get(self.os_url)
        items = response.data.get('results', response.data)

        # Deve ver a "Livre" e a "Tec 1", mas NÃO a "Tec 2"
        self.assertEqual(len(items), 2)
        titulos = [item['titulo'] for item in items]
        self.assertIn("OS Livre", titulos)
        self.assertIn("OS Tec 1", titulos)
        self.assertNotIn("OS Tec 2", titulos)

    def test_tecnico_cannot_delete(self):
        """Garante que técnicos não podem deletar ordens de serviço."""
        os = OrdemServico.objects.create(
            equipamento=self.motor, titulo="OS Protegida", descricao="Teste"
        )
        self.client.force_authenticate(user=self.tecnico1)
        url = reverse('ordens-servico-detail', args=[os.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tecnico_cannot_assign_other_user_on_create(self):
        """Técnicos não podem atribuir outra pessoa ao criar uma O.S."""
        self.client.force_authenticate(user=self.tecnico1)
        payload = {
            'equipamento': self.motor.id,
            'titulo': 'OS Atribuida a Outro',
            'descricao': 'Teste',
            'responsavel': self.tecnico2.id,
        }
        response = self.client.post(self.os_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_concluir_os_sem_responsavel_atribui_usuario(self):
        """Ao concluir uma O.S. sem responsável, ela deve ser atribuída ao usuário que encerra."""
        os = OrdemServico.objects.create(
            equipamento=self.motor,
            titulo='OS para Concluir',
            descricao='Teste',
            status='andamento',
            responsavel=None,
        )
        self.client.force_authenticate(user=self.tecnico1)
        url = reverse('ordens-servico-detail', args=[os.id])
        response = self.client.patch(url, {'status': 'concluida'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['responsavel'], self.tecnico1.id)

    def test_tecnico_assume_os_backend_assigns_responsavel(self):
        """Ao assumir uma O.S. sem responsável, o backend deve atribuir o técnico automaticamente."""
        os = OrdemServico.objects.create(
            equipamento=self.motor,
            titulo='OS para Assumir',
            descricao='Teste',
            status='pendente',
            responsavel=None,
        )
        self.client.force_authenticate(user=self.tecnico1)
        url = reverse('ordens-servico-detail', args=[os.id])
        response = self.client.patch(url, {'status': 'andamento'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['responsavel'], self.tecnico1.id)

    def test_tecnico_create_os_andamento_assigns_self(self):
        """Ao criar uma O.S. em andamento, o backend deve atribuir o técnico automaticamente."""
        self.client.force_authenticate(user=self.tecnico1)
        payload = {
            'equipamento': self.motor.id,
            'titulo': 'OS Criada Andamento',
            'descricao': 'Teste',
            'status': 'andamento',
            'responsavel': None,
        }
        response = self.client.post(self.os_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['responsavel'], self.tecnico1.id)

    def test_concluir_os_cria_historico_unico_no_backend(self):
        os = OrdemServico.objects.create(
            equipamento=self.motor,
            titulo='OS com histórico',
            descricao='Serviço concluído',
            status='andamento',
        )
        self.client.force_authenticate(user=self.gestor)
        url = reverse('ordens-servico-detail', args=[os.id])

        response = self.client.patch(url, {'status': 'concluida'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(HistoricoManutencao.objects.filter(ordem_servico=os).count(), 1)
        self.assertIsNotNone(os.__class__.objects.get(pk=os.id).data_conclusao)

        self.client.patch(url, {'status': 'concluida'}, format='json')
        self.assertEqual(HistoricoManutencao.objects.filter(ordem_servico=os).count(), 1)

    def test_os_nao_aceita_equipamento_de_outra_empresa(self):
        outra_empresa = Empresa.objects.create(nome='Outra', cnpj='555', email='o@o.com')
        outro_motor = Equipamento.objects.create(
            nome='Motor isolado', tipo='Motor', numero_serie='OS-002', empresa=outra_empresa
        )
        self.client.force_authenticate(user=self.gestor)

        response = self.client.post(self.os_url, {
            'equipamento': outro_motor.id,
            'titulo': 'OS indevida',
            'descricao': 'Teste',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gestor_cannot_create_history_for_another_company_order(self):
        outra_empresa = Empresa.objects.create(
            nome='Outra empresa histórico', cnpj='556', email='hist@example.com'
        )
        outro_motor = Equipamento.objects.create(
            nome='Motor privado',
            tipo='Motor',
            numero_serie='OS-HIST-CROSS',
            empresa=outra_empresa,
        )
        outra_os = OrdemServico.objects.create(
            equipamento=outro_motor,
            titulo='OS privada',
            descricao='Teste',
        )

        self.client.force_authenticate(user=self.gestor)
        response = self.client.post(
            reverse('historico-list'),
            {
                'ordem_servico': outra_os.id,
                'descricao_servico': 'Histórico indevido',
                'data_execucao': '2026-10-22',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(HistoricoManutencao.objects.filter(ordem_servico=outra_os).exists())


class PriorizacaoTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Prioridade', cnpj='992', email='prioridade@a.com')
        self.gestor = Usuario.objects.create_user(username='gestor_prio', password='123', tipo_usuario='gestor', empresa=self.empresa)
        self.equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Linha crítica', numero_serie='PRIO-01', criticidade='A')

    def test_heranca_independe_de_gravidade_e_risco_de_seguranca(self):
        self.assertEqual(PrioridadeOSService.calcular(self.equipamento, 'corretiva', 'moderada')[0], 'A')
        self.assertEqual(PrioridadeOSService.calcular(self.equipamento, 'corretiva', 'critica')[0], 'A')
        self.assertEqual(PrioridadeOSService.calcular(self.equipamento, 'corretiva', 'baixa', True)[0], 'A')

    def test_critica_ausente_tem_tratamento_explicito(self):
        self.equipamento.criticidade = None
        self.equipamento.save()
        prioridade, justificativa, _ = PrioridadeOSService.calcular(self.equipamento, 'corretiva', 'critica')
        self.assertIsNone(prioridade)
        self.assertIn('sem criticidade avaliada', justificativa)

    def test_preventiva_herda_a_classe_sem_prioridade_do_plano(self):
        prioridade, _, _ = PrioridadeOSService.calcular(self.equipamento, 'preventiva', 'ausente', prioridade_plano='media')
        self.assertEqual(prioridade, 'A')

    def test_api_preserva_contexto_da_abertura_e_prioridade_manual_de_gestor(self):
        self.client.force_authenticate(self.gestor)
        resposta = self.client.post(reverse('ordens-servico-list'), {
            'equipamento': self.equipamento.id, 'titulo': 'Inspeção', 'descricao': 'Condição observada',
            'tipo_os': 'corretiva', 'gravidade_condicao': 'moderada',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.data)
        self.assertEqual(resposta.data['prioridade'], 'A')
        self.assertEqual(resposta.data['criticidade_na_abertura'], 'A')
        self.assertTrue(resposta.data['justificativa_prioridade'])
