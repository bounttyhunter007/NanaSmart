"""
Script de Testes Completo da API - Plataforma de Manutenção Industrial
Testa todos os endpoints, campos, lógica de negócio e permissões.
"""
import os
import sys
import django
import json
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import Empresa, Usuario
from ativos.models import Equipamento, EquipamentoLocalizacao
from telemetria.models import Sensor, Telemetria
from alertas.models import Alerta
from manutencao.models import OrdemServico, HistoricoManutencao


# ============================================================
#  HELPERS
# ============================================================
class BaseAPITestCase(TestCase):
    """Classe base com fixtures compartilhadas."""

    def setUp(self):
        self.client = APIClient()

        # --- Empresas ---
        self.empresa1 = Empresa.objects.create(
            nome='Indústria Alpha', cnpj='11.111.111/0001-11',
            email='alpha@ind.com', telefone='11999990001',
            endereco='Rua A, 100'
        )
        self.empresa2 = Empresa.objects.create(
            nome='Indústria Beta', cnpj='22.222.222/0001-22',
            email='beta@ind.com', telefone='11999990002',
            endereco='Rua B, 200'
        )

        # --- Usuários ---
        self.admin = Usuario.objects.create_user(
            username='admin_test', password='testpass123',
            email='admin@test.com', first_name='Admin', last_name='Geral',
            tipo_usuario='admin', cargo='Administrador',
            empresa=self.empresa1, is_superuser=True, is_staff=True
        )
        self.gestor = Usuario.objects.create_user(
            username='gestor_test', password='testpass123',
            email='gestor@test.com', first_name='Gestor', last_name='Alpha',
            tipo_usuario='gestor', cargo='Gerente de Manutenção',
            empresa=self.empresa1
        )
        self.tecnico = Usuario.objects.create_user(
            username='tecnico_test', password='testpass123',
            email='tec@test.com', first_name='Técnico', last_name='Alpha',
            tipo_usuario='tecnico', cargo='Eletricista Sênior',
            empresa=self.empresa1
        )
        self.gestor_beta = Usuario.objects.create_user(
            username='gestor_beta', password='testpass123',
            email='gestor_beta@test.com', first_name='Gestor', last_name='Beta',
            tipo_usuario='gestor', cargo='Gerente',
            empresa=self.empresa2
        )

        # --- Equipamentos ---
        self.equip1 = Equipamento.objects.create(
            empresa=self.empresa1, nome='Motor Elétrico ME-01',
            tipo='Motor Elétrico', fabricante='WEG', modelo='W22',
            numero_serie='SN-ALPHA-001', data_instalacao=date(2024, 1, 15),
            status='ativo'
        )
        self.equip2 = Equipamento.objects.create(
            empresa=self.empresa1, nome='Bomba Hidráulica BH-02',
            tipo='Bomba Hidráulica', fabricante='Rexroth', modelo='A10V',
            numero_serie='SN-ALPHA-002', data_instalacao=date(2024, 3, 10),
            status='ativo'
        )
        self.equip_beta = Equipamento.objects.create(
            empresa=self.empresa2, nome='Compressor Beta',
            tipo='Compressor', fabricante='Atlas Copco', modelo='GA37',
            numero_serie='SN-BETA-001', data_instalacao=date(2024, 6, 1),
            status='ativo'
        )

        # --- Localização ---
        self.loc1 = EquipamentoLocalizacao.objects.create(
            equipamento=self.equip1, setor='Linha de Produção 1'
        )

        # --- Sensores ---
        self.sensor1 = Sensor.objects.create(
            equipamento=self.equip1, tipo_sensor='temperatura',
            unidade_medida='°C', descricao='Sensor de temperatura do motor',
            ativo=True
        )
        self.sensor2 = Sensor.objects.create(
            equipamento=self.equip1, tipo_sensor='vibracao',
            unidade_medida='mm/s', descricao='Sensor de vibração do motor',
            ativo=True
        )

        # --- Telemetria (valores base baixos) ---
        self.leitura1 = Telemetria.objects.create(sensor=self.sensor1, valor=40.0)
        self.leitura2 = Telemetria.objects.create(sensor=self.sensor2, valor=1.0)

        # --- Alertas ---
        self.alerta1 = Alerta.objects.create(
            equipamento=self.equip1, tipo_alerta='Temperatura Elevada',
            nivel='medio', descricao='Temperatura acima do normal',
            status='ativo'
        )

        # --- Ordens de Serviço ---
        self.os1 = OrdemServico.objects.create(
            equipamento=self.equip1, responsavel=self.tecnico,
            titulo='Manutenção preventiva motor',
            descricao='Verificação completa do motor elétrico',
            status='pendente', prioridade='media'
        )
        self.os_concluida = OrdemServico.objects.create(
            equipamento=self.equip1, responsavel=self.tecnico,
            titulo='Troca de rolamento',
            descricao='Substituição de rolamento desgastado',
            status='concluida', prioridade='alta',
            data_abertura=timezone.now() - timedelta(days=5),
            data_conclusao=timezone.now() - timedelta(days=3)
        )

        # --- Histórico ---
        self.historico1 = HistoricoManutencao.objects.create(
            ordem_servico=self.os_concluida,
            descricao_servico='Rolamento substituído com sucesso',
            data_execucao=date.today() - timedelta(days=3),
            custo_pecas=Decimal('250.00'),
            custo_mao_de_obra=Decimal('180.00')
        )

    def login_as(self, user):
        self.client.force_authenticate(user=user)

    def logout(self):
        self.client.force_authenticate(user=None)


# ============================================================
#  1. TESTES DE MODEL (Lógica de Negócio)
# ============================================================
class ModelTests(BaseAPITestCase):
    """Testa a integridade dos models, campos e lógica."""

    # --- Empresa ---
    def test_empresa_criacao(self):
        self.assertEqual(self.empresa1.nome, 'Indústria Alpha')
        self.assertEqual(self.empresa1.cnpj, '11.111.111/0001-11')
        self.assertIsNotNone(self.empresa1.data_cadastro)

    def test_empresa_str(self):
        self.assertEqual(str(self.empresa1), 'Indústria Alpha')

    def test_empresa_cnpj_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Empresa.objects.create(nome='Dup', cnpj='11.111.111/0001-11', email='x@x.com')

    # --- Usuario ---
    def test_usuario_criacao(self):
        self.assertEqual(self.tecnico.tipo_usuario, 'tecnico')
        self.assertEqual(self.tecnico.cargo, 'Eletricista Sênior')
        self.assertEqual(self.tecnico.empresa, self.empresa1)

    def test_usuario_str(self):
        s = str(self.tecnico)
        self.assertIn('tecnico_test', s)
        self.assertIn('Técnico', s)

    def test_usuario_tipo_choices(self):
        valid_types = ['admin', 'gestor', 'tecnico']
        for t in valid_types:
            u = Usuario(tipo_usuario=t)
            self.assertIn(u.tipo_usuario, valid_types)

    # --- Equipamento ---
    def test_equipamento_criacao(self):
        self.assertEqual(self.equip1.nome, 'Motor Elétrico ME-01')
        self.assertEqual(self.equip1.empresa, self.empresa1)
        self.assertEqual(self.equip1.status, 'ativo')

    def test_equipamento_numero_serie_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Equipamento.objects.create(
                empresa=self.empresa1, nome='Dup', tipo='X',
                numero_serie='SN-ALPHA-001'
            )

    def test_equipamento_str(self):
        s = str(self.equip1)
        self.assertIn('Motor Elétrico ME-01', s)
        self.assertIn('SN-ALPHA-001', s)

    # --- Localização ---
    def test_localizacao_one_to_one(self):
        self.assertEqual(self.loc1.equipamento, self.equip1)
        self.assertEqual(self.equip1.localizacao.setor, 'Linha de Produção 1')

    def test_localizacao_str(self):
        s = str(self.loc1)
        self.assertIn('Linha de Produção 1', s)

    # --- Sensor ---
    def test_sensor_criacao(self):
        self.assertEqual(self.sensor1.tipo_sensor, 'temperatura')
        self.assertEqual(self.sensor1.unidade_medida, '°C')
        self.assertEqual(self.sensor1.equipamento, self.equip1)
        self.assertTrue(self.sensor1.ativo)

    def test_sensor_fk_equipamento(self):
        """Sensor deve pertencer a Equipamento (não a OrdemServico)."""
        self.assertEqual(self.sensor1.equipamento.nome, 'Motor Elétrico ME-01')

    def test_sensor_str(self):
        s = str(self.sensor1)
        self.assertIn('Temperatura', s)

    # --- Telemetria ---
    def test_telemetria_criacao(self):
        self.assertEqual(self.leitura1.valor, 40.0)
        self.assertEqual(self.leitura1.sensor, self.sensor1)
        self.assertIsNotNone(self.leitura1.data_hora)

    def test_telemetria_ordering(self):
        """Deve retornar mais recente primeiro."""
        leituras = list(Telemetria.objects.filter(sensor=self.sensor1))
        if len(leituras) > 1:
            self.assertGreaterEqual(leituras[0].data_hora, leituras[1].data_hora)

    # --- Alerta Gradual ---
    def test_alertas_graduais_niveis(self):
        """Testa se o signal gera alertas nos níveis corretos conforme o percentual do limite."""
        from telemetria.config_alertas import obter_limite
        limite = obter_limite(self.equip1.tipo, self.sensor1.tipo_sensor) # ex: 85.0
        
        # 1. Nível BAIXO (>= 70%)
        val_baixo = limite * 0.75
        Telemetria.objects.create(sensor=self.sensor1, valor=val_baixo)
        alerta = Alerta.objects.filter(equipamento=self.equip1, nivel='baixo').order_by('-id').first()
        self.assertIsNotNone(alerta)
        
        # 2. Nível MÉDIO (>= 85%) - Deve atualizar o existente ou criar um que sobreponha
        val_medio = limite * 0.90
        Telemetria.objects.create(sensor=self.sensor1, valor=val_medio)
        alerta = Alerta.objects.filter(equipamento=self.equip1, status='ativo').order_by('-id').first()
        self.assertEqual(alerta.nivel, 'medio')
        
        # 3. Nível CRÍTICO (>= 100%)
        val_critico = limite * 1.10
        Telemetria.objects.create(sensor=self.sensor1, valor=val_critico)
        alerta = Alerta.objects.filter(equipamento=self.equip1, status='ativo').order_by('-id').first()
        self.assertEqual(alerta.nivel, 'critico')

    # --- Alerta ---
    def test_alerta_criacao(self):
        self.assertEqual(self.alerta1.nivel, 'medio')
        self.assertEqual(self.alerta1.status, 'ativo')
        self.assertEqual(self.alerta1.equipamento, self.equip1)

    def test_alerta_str(self):
        s = str(self.alerta1)
        self.assertIn('MEDIO', s)

    # --- OrdemServico ---
    def test_os_criacao(self):
        self.assertEqual(self.os1.status, 'pendente')
        self.assertEqual(self.os1.prioridade, 'media')
        self.assertEqual(self.os1.equipamento, self.equip1)
        self.assertEqual(self.os1.responsavel, self.tecnico)

    def test_os_auto_conclusao(self):
        """Ao marcar como concluída sem data_conclusao, o sistema preenche automaticamente."""
        os_nova = OrdemServico.objects.create(
            equipamento=self.equip2, responsavel=self.tecnico,
            titulo='Teste auto conclusão', descricao='Teste',
            status='pendente', prioridade='baixa'
        )
        self.assertIsNone(os_nova.data_conclusao)
        os_nova.status = 'concluida'
        os_nova.save()
        os_nova.refresh_from_db()
        self.assertIsNotNone(os_nova.data_conclusao)

    def test_os_str(self):
        s = str(self.os1)
        self.assertIn('Manutenção preventiva motor', s)

    # --- HistoricoManutencao ---
    def test_historico_criacao(self):
        self.assertEqual(self.historico1.custo_pecas, Decimal('250.00'))
        self.assertEqual(self.historico1.custo_mao_de_obra, Decimal('180.00'))

    def test_historico_custo_total(self):
        """Verifica que a property custo_total calcula corretamente."""
        self.assertEqual(self.historico1.custo_total, Decimal('430.00'))

    def test_historico_one_to_one(self):
        self.assertEqual(self.historico1.ordem_servico, self.os_concluida)

    def test_historico_campo_corrigido(self):
        """Confirma que o campo se chama custo_mao_de_obra (sem typo)."""
        field_names = [f.name for f in HistoricoManutencao._meta.get_fields()]
        self.assertIn('custo_mao_de_obra', field_names)
        self.assertNotIn('custo_maao_de_obra', field_names)


# ============================================================
#  2. TESTES DE AUTENTICAÇÃO JWT
# ============================================================
class AuthTests(BaseAPITestCase):
    """Testa login JWT, refresh e endpoint /me/."""

    def test_login_sucesso(self):
        resp = self.client.post('/api/auth/token/', {
            'username': 'admin_test', 'password': 'testpass123'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_falha(self):
        resp = self.client.post('/api/auth/token/', {
            'username': 'admin_test', 'password': 'senhaerrada'
        })
        self.assertEqual(resp.status_code, 401)

    def test_refresh_token(self):
        login = self.client.post('/api/auth/token/', {
            'username': 'admin_test', 'password': 'testpass123'
        })
        refresh = login.data['refresh']
        resp = self.client.post('/api/auth/token/refresh/', {'refresh': refresh})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_me_autenticado(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/auth/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['username'], 'admin_test')
        self.assertEqual(resp.data['tipo_usuario'], 'admin')
        self.assertIn('empresa_nome', resp.data)

    def test_me_nao_autenticado(self):
        resp = self.client.get('/api/auth/me/')
        self.assertEqual(resp.status_code, 401)

    def test_endpoints_sem_auth(self):
        """Todos endpoints protegidos devem retornar 401 sem token."""
        endpoints = [
            '/api/empresas/', '/api/usuarios/',
            '/api/equipamentos/', '/api/localizacao/',
            '/api/ordens-servico/', '/api/historico/',
            '/api/telemetria/sensores/', '/api/telemetria/leituras/',
            '/api/alertas/',
            '/api/dashboards/resumo/', '/api/dashboards/kpis/',
        ]
        for url in endpoints:
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [401, 403], f"{url} deveria ser protegido, retornou {resp.status_code}")

    def test_troca_senha_sucesso(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/auth/change-password/', {
            'senha_atual': 'testpass123',
            'nova_senha': 'newsecurepassword123',
            'confirmar_nova_senha': 'newsecurepassword123'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.tecnico.check_password('newsecurepassword123'))

    def test_troca_senha_falha_atual_incorreta(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/auth/change-password/', {
            'senha_atual': 'senhaerrada',
            'nova_senha': 'newpassword123',
            'confirmar_nova_senha': 'newpassword123'
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn('senha_atual', resp.data)

    def test_troca_senha_falha_confirmacao(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/auth/change-password/', {
            'senha_atual': 'testpass123',
            'nova_senha': 'newpassword123',
            'confirmar_nova_senha': 'diferente'
        })
        self.assertEqual(resp.status_code, 400)


# ============================================================
#  3. TESTES DE CRUD — EMPRESAS
# ============================================================
class EmpresaAPITests(BaseAPITestCase):

    def test_list_empresas_admin(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/empresas/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_list_empresas_gestor(self):
        """Gestor só vê a própria empresa."""
        self.login_as(self.gestor)
        resp = self.client.get('/api/empresas/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['nome'], 'Indústria Alpha')

    def test_list_empresas_tecnico_negado(self):
        """Técnico NÃO deve acessar endpoint de empresas (IsGestor)."""
        self.login_as(self.tecnico)
        resp = self.client.get('/api/empresas/')
        self.assertEqual(resp.status_code, 403)

    def test_create_empresa(self):
        self.login_as(self.admin)
        resp = self.client.post('/api/empresas/', {
            'nome': 'Nova Empresa', 'cnpj': '33.333.333/0001-33',
            'email': 'nova@emp.com'
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['nome'], 'Nova Empresa')

    def test_detail_empresa(self):
        self.login_as(self.admin)
        resp = self.client.get(f'/api/empresas/{self.empresa1.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['cnpj'], '11.111.111/0001-11')

    def test_update_empresa(self):
        self.login_as(self.admin)
        resp = self.client.patch(f'/api/empresas/{self.empresa1.id}/', {
            'telefone': '119999-NOVO'
        })
        self.assertEqual(resp.status_code, 200)

    def test_search_empresa(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/empresas/?search=Alpha')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 1)


# ============================================================
#  4. TESTES DE CRUD — USUÁRIOS
# ============================================================
class UsuarioAPITests(BaseAPITestCase):

    def test_list_usuarios_admin(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/usuarios/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 4)

    def test_list_usuarios_gestor_isolamento(self):
        """Gestor da empresa1 não enxerga usuários da empresa2."""
        self.login_as(self.gestor)
        resp = self.client.get('/api/usuarios/')
        self.assertEqual(resp.status_code, 200)
        for u in resp.data:
            self.assertEqual(u['empresa'], self.empresa1.id)

    def test_create_usuario(self):
        self.login_as(self.admin)
        resp = self.client.post('/api/usuarios/', {
            'username': 'novo_user', 'email': 'novo@test.com',
            'first_name': 'Novo', 'last_name': 'User',
            'tipo_usuario': 'tecnico', 'empresa': self.empresa1.id,
        })
        self.assertIn(resp.status_code, [201, 200])

    def test_filter_usuarios_tipo(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/usuarios/?tipo_usuario=tecnico')
        self.assertEqual(resp.status_code, 200)
        for u in resp.data:
            self.assertEqual(u['tipo_usuario'], 'tecnico')

    def test_search_usuarios(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/usuarios/?search=Admin')
        self.assertEqual(resp.status_code, 200)


# ============================================================
#  5. TESTES DE CRUD — EQUIPAMENTOS
# ============================================================
class EquipamentoAPITests(BaseAPITestCase):

    def test_list_equipamentos_admin(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/equipamentos/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

    def test_list_equipamentos_isolamento(self):
        """Gestor Alpha não vê equipamentos da Beta."""
        self.login_as(self.gestor)
        resp = self.client.get('/api/equipamentos/')
        self.assertEqual(resp.status_code, 200)
        for eq in resp.data:
            self.assertEqual(eq['empresa'], self.empresa1.id)

    def test_tecnico_readonly(self):
        """Técnico consegue LER mas NÃO criar (IsGestorOrReadOnly)."""
        self.login_as(self.tecnico)
        resp_get = self.client.get('/api/equipamentos/')
        self.assertEqual(resp_get.status_code, 200)

        resp_post = self.client.post('/api/equipamentos/', {
            'nome': 'Teste', 'tipo': 'X', 'numero_serie': 'SN-NEW',
            'empresa': self.empresa1.id
        })
        self.assertEqual(resp_post.status_code, 403)

    def test_create_equipamento(self):
        self.login_as(self.gestor)
        resp = self.client.post('/api/equipamentos/', {
            'nome': 'Esteira E-03', 'tipo': 'Esteira',
            'fabricante': 'Rexnord', 'modelo': 'S300',
            'numero_serie': 'SN-ALPHA-003',
            'empresa': self.empresa1.id, 'status': 'ativo'
        })
        self.assertEqual(resp.status_code, 201)

    def test_filter_por_status(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/equipamentos/?status=ativo')
        self.assertEqual(resp.status_code, 200)
        for eq in resp.data:
            self.assertEqual(eq['status'], 'ativo')

    def test_search_equipamento(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/equipamentos/?search=WEG')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 1)


# ============================================================
#  6. TESTES DE CRUD — LOCALIZAÇÃO
# ============================================================
class LocalizacaoAPITests(BaseAPITestCase):

    def test_list_localizacao(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/localizacao/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 1)

    def test_create_localizacao(self):
        self.login_as(self.gestor)
        resp = self.client.post('/api/localizacao/', {
            'equipamento': self.equip2.id,
            'setor': 'Caldeiraria'
        })
        self.assertEqual(resp.status_code, 201)

    def test_localizacao_isolamento(self):
        """Gestor Beta não vê a localização da Alpha."""
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/localizacao/')
        self.assertEqual(resp.status_code, 200)
        for loc in resp.data:
            equip = Equipamento.objects.get(pk=loc['equipamento'])
            self.assertEqual(equip.empresa, self.empresa2)


# ============================================================
#  7. TESTES DE CRUD — SENSORES
# ============================================================
class SensorAPITests(BaseAPITestCase):

    def test_list_sensores(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/telemetria/sensores/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 2)

    def test_create_sensor(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/telemetria/sensores/', {
            'equipamento': self.equip1.id,
            'tipo_sensor': 'pressao',
            'unidade_medida': 'bar',
            'descricao': 'Sensor de pressão',
            'ativo': True
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['tipo_sensor'], 'pressao')
        self.assertEqual(resp.data['unidade_medida'], 'bar')

    def test_filter_sensor_por_tipo(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/telemetria/sensores/?tipo_sensor=temperatura')
        self.assertEqual(resp.status_code, 200)
        for s in resp.data:
            self.assertEqual(s['tipo_sensor'], 'temperatura')

    def test_sensor_isolamento(self):
        """Gestor Beta não vê sensores da Alpha."""
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/telemetria/sensores/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)


# ============================================================
#  8. TESTES DE CRUD — TELEMETRIA (LEITURAS)
# ============================================================
class TelemetriaAPITests(BaseAPITestCase):

    def test_list_leituras(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/telemetria/leituras/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 2)

    def test_create_leitura(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/telemetria/leituras/', {
            'sensor': self.sensor1.id,
            'valor': 85.3
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(float(resp.data['valor']), 85.3)

    def test_filter_leitura_por_sensor(self):
        self.login_as(self.tecnico)
        resp = self.client.get(f'/api/telemetria/leituras/?sensor={self.sensor1.id}')
        self.assertEqual(resp.status_code, 200)
        for l in resp.data:
            self.assertEqual(l['sensor'], self.sensor1.id)


# ============================================================
#  9. TESTES DE CRUD — ALERTAS
# ============================================================
class AlertaAPITests(BaseAPITestCase):

    def test_list_alertas(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/alertas/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 1)

    def test_create_alerta(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/alertas/', {
            'equipamento': self.equip1.id,
            'tipo_alerta': 'Vibração Excessiva',
            'nivel': 'critico',
            'descricao': 'Vibração acima de 10mm/s',
            'status': 'ativo'
        })
        self.assertEqual(resp.status_code, 201)

    def test_update_alerta_status(self):
        self.login_as(self.tecnico)
        resp = self.client.patch(f'/api/alertas/{self.alerta1.id}/', {
            'status': 'resolvido'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'resolvido')

    def test_filter_alerta_nivel(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/alertas/?nivel=medio')
        self.assertEqual(resp.status_code, 200)
        for a in resp.data:
            self.assertEqual(a['nivel'], 'medio')

    def test_alerta_isolamento(self):
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/alertas/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)


# ============================================================
#  10. TESTES DE CRUD — ORDENS DE SERVIÇO
# ============================================================
class OrdemServicoAPITests(BaseAPITestCase):

    def test_list_os(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/ordens-servico/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 2)

    def test_create_os(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/ordens-servico/', {
            'equipamento': self.equip2.id,
            'responsavel': self.tecnico.id,
            'titulo': 'Inspeção geral',
            'descricao': 'Inspeção programada trimestral',
            'status': 'pendente',
            'prioridade': 'baixa'
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['titulo'], 'Inspeção geral')

    def test_os_read_only_fields(self):
        """data_abertura e data_conclusao devem ser read-only."""
        self.login_as(self.tecnico)
        resp = self.client.post('/api/ordens-servico/', {
            'equipamento': self.equip2.id,
            'titulo': 'Teste readonly',
            'descricao': 'Teste',
            'status': 'pendente', 'prioridade': 'baixa',
            'data_abertura': '2020-01-01T00:00:00Z',
            'data_conclusao': '2020-01-02T00:00:00Z',
        })
        self.assertEqual(resp.status_code, 201)
        # data_abertura não deve ser 2020 (é read_only, sistema preenche)
        self.assertNotIn('2020', str(resp.data.get('data_abertura', '')))

    def test_filter_os_status(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/ordens-servico/?status=pendente')
        self.assertEqual(resp.status_code, 200)
        for os in resp.data:
            self.assertEqual(os['status'], 'pendente')

    def test_filter_os_prioridade(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/ordens-servico/?prioridade=alta')
        self.assertEqual(resp.status_code, 200)

    def test_os_isolamento(self):
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/ordens-servico/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)


# ============================================================
#  11. TESTES DE CRUD — HISTÓRICO DE MANUTENÇÃO
# ============================================================
class HistoricoAPITests(BaseAPITestCase):

    def test_list_historico(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/historico/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) >= 1)

    def test_historico_custo_total_na_api(self):
        """Verifica que custo_total aparece na resposta da API."""
        self.login_as(self.tecnico)
        resp = self.client.get(f'/api/historico/{self.historico1.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(float(resp.data['custo_total']), 430.00)
        self.assertEqual(float(resp.data['custo_mao_de_obra']), 180.00)
        self.assertEqual(float(resp.data['custo_pecas']), 250.00)

    def test_historico_filter_data(self):
        self.login_as(self.tecnico)
        hoje = date.today().isoformat()
        resp = self.client.get(f'/api/historico/?data_execucao_antes={hoje}')
        self.assertEqual(resp.status_code, 200)

    def test_historico_isolamento(self):
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/historico/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)


# ============================================================
#  12. TESTES DE DASHBOARD / KPIs
# ============================================================
class DashboardAPITests(BaseAPITestCase):

    def test_dashboard_resumo(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/dashboards/resumo/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('resumo_status', resp.data)
        self.assertIn('kpis_globais', resp.data)
        self.assertIn('detalhes_equipamentos', resp.data)

    def test_dashboard_resumo_campos(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/dashboards/resumo/')
        status_data = resp.data['resumo_status']
        self.assertIn('total', status_data)
        self.assertIn('ativo', status_data)
        self.assertIn('manutencao', status_data)
        self.assertIn('inativo', status_data)

        kpi = resp.data['kpis_globais']
        self.assertIn('mttr_medio', kpi)
        self.assertIn('mtbf_medio', kpi)
        self.assertIn('disponibilidade_media', kpi)

    def test_dashboard_kpis_individual(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/dashboards/kpis/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        if len(resp.data) > 0:
            item = resp.data[0]
            self.assertIn('equipamento', item)
            self.assertIn('mttr_hours', item)
            self.assertIn('mtbf_hours', item)
            self.assertIn('disponibilidade_porcentagem', item)

    def test_dashboard_kpi_por_equipamento(self):
        self.login_as(self.admin)
        resp = self.client.get(f'/api/dashboards/kpis/?equipamento_id={self.equip1.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_dashboard_isolamento_empresa(self):
        self.login_as(self.gestor)
        resp = self.client.get('/api/dashboards/resumo/')
        self.assertEqual(resp.status_code, 200)
        for eq in resp.data['detalhes_equipamentos']:
            equip_db = Equipamento.objects.get(pk=eq['equipamento_id'])
            self.assertEqual(equip_db.empresa, self.empresa1)

    def test_dashboard_campos_novos(self):
        """Valida a presença de custo_total_manutencao, alertas_ativos e os_abertas."""
        self.login_as(self.gestor)
        resp = self.client.get('/api/dashboards/resumo/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('alertas_ativos', resp.data)
        self.assertIn('os_abertas', resp.data)
        self.assertIn('custo_total_manutencao', resp.data['kpis_globais'])
        self.assertTrue(resp.data['kpis_globais']['custo_total_manutencao'] > 0)

    def test_dashboard_filtro_periodo(self):
        """Valida que o filtro ?dias= limita os resultados."""
        self.login_as(self.gestor)
        # Sem filtro
        resp1 = self.client.get('/api/dashboards/resumo/')
        # Com filtro de 1 dia (não deve ter OS concluída hoje nos mocks)
        resp2 = self.client.get('/api/dashboards/resumo/?dias=1')
        self.assertEqual(resp2.status_code, 200)
        # O custo total e manutenções devem ser diferentes (ou zero no resp2)
        custo1 = resp1.data['kpis_globais']['custo_total_manutencao']
        custo2 = resp2.data['kpis_globais']['custo_total_manutencao']
        self.assertNotEqual(custo1, custo2)


# ============================================================
#  13. TESTES DE PERMISSÕES (RBAC)
# ============================================================
class PermissaoTests(BaseAPITestCase):

    def test_tecnico_nao_acessa_empresas(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/empresas/')
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_nao_acessa_usuarios(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/usuarios/')
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_le_equipamentos(self):
        self.login_as(self.tecnico)
        resp = self.client.get('/api/equipamentos/')
        self.assertEqual(resp.status_code, 200)

    def test_tecnico_nao_cria_equipamento(self):
        self.login_as(self.tecnico)
        resp = self.client.post('/api/equipamentos/', {
            'nome': 'X', 'tipo': 'Y', 'numero_serie': 'SNX',
            'empresa': self.empresa1.id
        })
        self.assertEqual(resp.status_code, 403)

    def test_gestor_cria_equipamento(self):
        self.login_as(self.gestor)
        resp = self.client.post('/api/equipamentos/', {
            'nome': 'Perm Test', 'tipo': 'Test', 'numero_serie': 'SN-PERM',
            'empresa': self.empresa1.id, 'status': 'ativo'
        })
        self.assertEqual(resp.status_code, 201)

    def test_tecnico_cria_os(self):
        """Técnico PODE criar OS (IsAuthenticated no OrdemServicoViewSet)."""
        self.login_as(self.tecnico)
        resp = self.client.post('/api/ordens-servico/', {
            'equipamento': self.equip1.id, 'titulo': 'OS Tec',
            'descricao': 'Teste', 'status': 'pendente', 'prioridade': 'baixa'
        })
        self.assertEqual(resp.status_code, 201)

    def test_tecnico_nao_deleta_alerta(self):
        self.login_as(self.tecnico)
        resp = self.client.delete(f'/api/alertas/{self.alerta1.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_nao_deleta_telemetria(self):
        self.login_as(self.tecnico)
        resp = self.client.delete(f'/api/telemetria/leituras/{self.leitura1.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_tecnico_nao_deleta_os(self):
        self.login_as(self.tecnico)
        resp = self.client.delete(f'/api/ordens-servico/{self.os1.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_gestor_deleta_alerta_sucesso(self):
        self.login_as(self.gestor)
        resp = self.client.delete(f'/api/alertas/{self.alerta1.id}/')
        self.assertEqual(resp.status_code, 204)


# ============================================================
#  14. TESTES DE ISOLAMENTO MULTI-TENANT
# ============================================================
class MultiTenantTests(BaseAPITestCase):

    def test_gestor_beta_nao_ve_equip_alpha(self):
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/equipamentos/')
        for eq in resp.data:
            self.assertEqual(eq['empresa'], self.empresa2.id)

    def test_gestor_beta_nao_ve_os_alpha(self):
        self.login_as(self.gestor_beta)
        resp = self.client.get('/api/ordens-servico/')
        self.assertEqual(len(resp.data), 0)

    def test_admin_ve_tudo(self):
        self.login_as(self.admin)
        resp = self.client.get('/api/equipamentos/')
        empresas = set(eq['empresa'] for eq in resp.data)
        self.assertEqual(len(empresas), 2)


# ============================================================
#  RUNNER
# ============================================================
if __name__ == '__main__':
    runner = DiscoverRunner(verbosity=2, interactive=False)
    # Cria banco de teste
    old_config = runner.setup_databases()

    from django.test.utils import setup_test_environment
    setup_test_environment()

    from unittest import TestLoader, TextTestRunner

    loader = TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    text_runner = TextTestRunner(verbosity=2)
    result = text_runner.run(suite)

    runner.teardown_databases(old_config)

    # Resumo
    print("\n" + "=" * 70)
    print(f"  TOTAL : {result.testsRun}")
    print(f"  PASS  : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  FAIL  : {len(result.failures)}")
    print(f"  ERROR : {len(result.errors)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
