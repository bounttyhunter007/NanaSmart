from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Empresa, Equipamento, PlanoManutencao, TipoEquipamento, HistoricoCriticidadeEquipamento, CriteriosCriticidade
from manutencao.models import OrdemServico
from accounts.models import Usuario

class AtivosTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Alpha", cnpj="111", email="a@a.com")
        self.user = Usuario.objects.create_user(
            username="gestor_ativos", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.client.force_authenticate(user=self.user)
        self.equip_url = reverse('equipamentos-list')

    def test_create_equipamento(self):
        """Testa a criação de equipamento e se o horímetro padrão é 0.0."""
        data = {
            "nome": "Motor Teste",
            "tipo": "Motor",
            "numero_serie": "SN-001",
            "empresa": self.empresa.id
        }
        response = self.client.post(self.equip_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['horimetro'], 0.0)

    def test_gestor_cannot_create_equipment_for_another_company(self):
        outra_empresa = Empresa.objects.create(
            nome='Outra', cnpj='112', email='outra@a.com'
        )
        response = self.client.post(self.equip_url, {
            'nome': 'Motor de outra empresa',
            'tipo': 'outro',
            'numero_serie': 'SN-CROSS',
            'empresa': outra_empresa.id,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Equipamento.objects.filter(numero_serie='SN-CROSS').exists())

    def test_gestor_cannot_create_location_or_plan_for_another_company(self):
        outra_empresa = Empresa.objects.create(
            nome='Outra', cnpj='113', email='outra2@a.com'
        )
        equipamento = Equipamento.objects.create(
            nome='Motor privado',
            tipo='outro',
            numero_serie='SN-PRIVATE',
            empresa=outra_empresa,
        )

        location_response = self.client.post(
            reverse('localizacao-list'),
            {'equipamento': equipamento.id, 'setor': 'Privado'},
            format='json',
        )
        plan_response = self.client.post(
            reverse('planos-manutencao-list'),
            {
                'equipamento': equipamento.id,
                'nome_servico': 'Plano privado',
                'descricao': 'Teste',
                'intervalo_horas': 100,
                'prioridade': 'media',
                'ativo': True,
            },
            format='json',
        )

        self.assertEqual(location_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(plan_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PlanoManutencao.objects.filter(equipamento=equipamento).exists())

class PlanoManutencaoTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome="Beta", cnpj="222", email="b@b.com")
        self.user = Usuario.objects.create_user(
            username="gestor_planos", password="123", tipo_usuario="gestor", empresa=self.empresa
        )
        self.client.force_authenticate(user=self.user)
        self.motor = Equipamento.objects.create(
            nome="Motor Preditivo", tipo="Motor", numero_serie="PRED-999", 
            empresa=self.empresa, horimetro=200.0
        )
        self.plano_url = reverse('planos-manutencao-list')

    def test_horimetro_trigger(self):
        """Testa se a O.S. preditiva é gerada corretamente ao atingir o horímetro."""
        # Cria plano de 100h (proximo disparo em 300h pois o motor já tem 200h)
        plano_data = {
            "equipamento": self.motor.id,
            "nome_servico": "Troca de Óleo",
            "descricao": "Serviço de teste",
            "intervalo_horas": 100.0,
            "prioridade": "media",
            "ativo": True
        }
        response = self.client.post(self.plano_url, plano_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        
        # 1. Atualiza para 250h (não deve gerar OS)
        self.motor.horimetro = 250.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 0)

        # 2. Atualiza para 310h (DEVE gerar OS)
        self.motor.horimetro = 310.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)

        # 3. Teste anti-duplicação (315h não gera nova OS)
        self.motor.horimetro = 315.0
        self.motor.save()
        self.assertEqual(OrdemServico.objects.filter(tipo_os='preditiva').count(), 1)


class CriticidadeTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Crit', cnpj='991', email='crit@a.com')
        self.gestor = Usuario.objects.create_user(username='gestor_crit', password='123', tipo_usuario='gestor', empresa=self.empresa)
        self.tecnico = Usuario.objects.create_user(username='tecnico_crit', password='123', tipo_usuario='tecnico', empresa=self.empresa)
        CriteriosCriticidade.objects.create(empresa=self.empresa, revisao=1, criterio_a='Impacto alto', criterio_b='Impacto médio', criterio_c='Impacto baixo', representante_manutencao='Responsável de teste', data_validacao=timezone.localdate())
        self.tipo = TipoEquipamento.objects.create(empresa=self.empresa, nome='Bomba de processo', criticidade_padrao='B', descricao_criterios='Impacto alto na continuidade.')

    def test_tipo_sugere_criticidade_sem_usar_nome_do_equipamento(self):
        self.client.force_authenticate(self.gestor)
        response = self.client.post(reverse('equipamentos-list'), {
            'empresa': self.empresa.id, 'nome': 'Bomba instalada na linha 2', 'numero_serie': 'CRIT-01',
            'tipo_equipamento': self.tipo.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data['criticidade'])
        self.assertEqual(response.data['criticidade_sugerida'], 'B')
        self.assertEqual(response.data['criticidade_origem'], 'nao_avaliada')
        accepted = self.client.patch(reverse('equipamentos-detail', args=[response.data['id']]), {
            'aceitar_sugestao': True, 'justificativa_criticidade': 'Contingência limitada validada.'}, format='json')
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(accepted.data['criticidade'], 'B')
        self.assertEqual(accepted.data['criticidade_origem'], 'tipo')

    def test_ajuste_individual_exige_justificativa_e_gera_historico(self):
        equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Equipamento', numero_serie='CRIT-02')
        self.client.force_authenticate(self.gestor)
        response = self.client.patch(reverse('equipamentos-detail', args=[equipamento.id]), {
            'criticidade': 'A', 'justificativa_criticidade': 'Sem redundância e com risco ambiental.'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(HistoricoCriticidadeEquipamento.objects.filter(equipamento=equipamento, criticidade_nova='A').count(), 1)

    def test_tecnico_nao_altera_criticidade(self):
        equipamento = Equipamento.objects.create(empresa=self.empresa, nome='Equipamento', numero_serie='CRIT-03')
        self.client.force_authenticate(self.tecnico)
        response = self.client.patch(reverse('equipamentos-detail', args=[equipamento.id]), {'criticidade': 'A'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
