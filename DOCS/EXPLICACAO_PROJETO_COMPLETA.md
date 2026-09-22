# 📋 Documentação Completa do Projeto — NanaSmart

> **Plataforma de Manutenção Industrial com Django REST Framework**
> Este documento explica **cada parte do projeto** de forma clara.w

---

## 📖 Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Configurações do Projeto (settings.py)](#2-configurações-do-projeto-settingspy)
3. [App: accounts — Usuários e Empresas](#3-app-accounts--usuários-e-empresas)
4. [App: authentication — Login e JWT](#4-app-authentication--login-e-jwt)
5. [App: ativos — Equipamentos e Planos de Manutenção](#5-app-ativos--equipamentos-e-planos-de-manutenção)
6. [App: manutencao — Ordens de Serviço e Histórico](#6-app-manutencao--ordens-de-serviço-e-histórico)
7. [App: telemetria — Sensores e Leituras](#7-app-telemetria--sensores-e-leituras)
8. [App: alertas — Sistema de Alertas](#8-app-alertas--sistema-de-alertas)
9. [App: exportacao — Exportação de Relatórios](#9-app-exportacao--exportação-de-relatórios)
10. [App: gemini_api — Inteligência Artificial](#10-app-gemini_api--inteligência-artificial)
11. [App: dashboards — KPIs e Métricas](#11-app-dashboards--kpis-e-métricas)
12. [Signals — Automações Inteligentes (IMPORTANTE)](#12-signals--automações-inteligentes)
13. [Permissions — Sistema de Permissões Customizado](#13-permissions--sistema-de-permissões-customizado)
14. [Simulador de Telemetria](#14-simulador-de-telemetria)
15. [Tabela Completa de Endpoints](#15-tabela-completa-de-endpoints)
16. [Fluxos Automatizados (Como tudo se conecta)](#16-fluxos-automatizados)
17. [Conceitos-Chave para a Apresentação](#17-conceitos-chave-para-a-apresentação)

---

## 1. Visão Geral da Arquitetura

O projeto é uma **API REST** construída com **Django + Django REST Framework (DRF)**. Não possui frontend no mesmo repositório (o front consome a API via HTTP).

### Stack Tecnológica

| Tecnologia | Para quê serve |
|---|---|
| **Django 5.2** | Framework web principal (ORM, migrations, admin) |
| **Django REST Framework** | Criação da API REST (serializers, viewsets, routers) |
| **SimpleJWT** | Autenticação via token JWT (login sem sessão) |
| **PostgreSQL** | Banco de dados relacional em produção |
| **django-filter** | Filtros avançados nos endpoints (ex: `?status=ativo`) |
| **drf-spectacular** | Documentação Swagger/OpenAPI automática |
| **django-cors-headers** | Permite o frontend em outro domínio acessar a API |
| **Google Gemini API** | IA para chat e análise de manutenção |
| **WeasyPrint / ReportLab** | Geração de PDF para relatórios |
| **openpyxl** | Geração de Excel para relatórios |

### Estrutura dos Apps

```
projeto/
├── app/              → Configurações globais (settings, urls raiz)
├── accounts/         → Empresa e Usuário (modelo customizado)
├── authentication/   → Login JWT, /me, troca de senha
├── ativos/           → Equipamentos, Localização, Planos de Manutenção
├── manutencao/       → Ordens de Serviço (O.S.) e Histórico
│   └── dashboards/   → KPIs (MTTR, MTBF, Disponibilidade)
├── telemetria/       → Sensores e Leituras de telemetria
├── alertas/          → Alertas automáticos e manuais
├── exportacao/       → Exportação em CSV, Excel e PDF
├── gemini_api/       → Chat IA com Google Gemini
└── scripts/          → Simulador de telemetria
```

### Isolamento Multi-Tenant

**Conceito fundamental**: cada usuário só vê dados da **sua empresa**. Isso é implementado no método `get_queryset()` de cada ViewSet:

```python
def get_queryset(self):
    user = self.request.user
    if user.tipo_usuario == 'admin':
        return Equipamento.objects.all()       # Admin vê TUDO
    if user.empresa:
        return Equipamento.objects.filter(empresa=user.empresa)  # Só da sua empresa
    return Equipamento.objects.none()          # Sem empresa = sem dados
```

**Por que isso é importante?** É uma prática real de mercado chamada **multi-tenancy**: múltiplas empresas usam o mesmo sistema, mas cada uma só vê seus próprios dados. É como se fosse um sistema separado para cada empresa, mas rodando na mesma infraestrutura.

---

## 2. Configurações do Projeto (settings.py)

Arquivo: `app/settings.py`

### Principais configurações explicadas

#### INSTALLED_APPS — Apps instalados
```python
INSTALLED_APPS = [
    # Apps nativos do Django
    'django.contrib.admin',          # Painel administrativo
    'django.contrib.auth',           # Sistema de autenticação
    'django.contrib.contenttypes',   # Tipos de conteúdo (usado internamente)
    'django.contrib.sessions',       # Sessões de usuário
    'django.contrib.messages',       # Sistema de mensagens
    'django.contrib.staticfiles',    # Arquivos estáticos (CSS, JS)
    
    # Libs de terceiros
    'rest_framework',                # Django REST Framework — cria a API
    'rest_framework_simplejwt',      # Autenticação JWT
    'django_filters',                # Filtros nos endpoints
    'django_extensions',             # Ferramentas extras para dev
    'corsheaders',                   # Permite acesso de outros domínios
    'drf_spectacular',               # Gera documentação Swagger
    
    # Nossos apps
    'authentication',                # Login/JWT
    'accounts',                      # Empresa/Usuário
    'ativos',                        # Equipamentos
    'manutencao',                    # Ordens de Serviço
    'telemetria',                    # Sensores
    'alertas',                       # Alertas
    'exportacao',                    # Relatórios
    'gemini_api',                    # IA
]
```

#### AUTH_USER_MODEL — Modelo de usuário customizado
```python
AUTH_USER_MODEL = 'accounts.Usuario'
```
**O que faz?** Diz ao Django: "em vez de usar o User padrão do Django, use o nosso modelo `Usuario` do app `accounts`". Isso permite adicionar campos como `empresa`, `tipo_usuario`, `cargo`.

#### REST_FRAMEWORK — Configuração da API
```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',  # Swagger automático
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Token JWT
        'rest_framework.authentication.SessionAuthentication',        # Sessão (para admin)
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # Todos os endpoints exigem login
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,           # Retorna 50 itens por página
    'MAX_PAGINATE_BY': 200,    # Máximo 200 itens por request
}
```

**O que isso significa?**
- Toda requisição precisa ter um token JWT válido no header
- Respostas são paginadas (nunca retorna a tabela inteira de uma vez)
- A documentação Swagger é gerada automaticamente

#### SIMPLE_JWT — Configuração dos tokens
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),    # Token de acesso dura 5 min
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),    # Token de refresh dura 24h
    'ROTATE_REFRESH_TOKENS': True,                    # Cada refresh gera novo refresh token
    'AUTH_HEADER_TYPES': ('Bearer',),                 # Formato: "Authorization: Bearer <token>"
}
```

**Fluxo de autenticação:**
1. Usuário faz login → recebe `access` (5 min) + `refresh` (24h)
2. Usa `access` nas requisições
3. Quando expira, envia o `refresh` para `/api/auth/refresh/` → recebe novo `access`
4. `ROTATE_REFRESH_TOKENS = True`: cada vez que usa o refresh, recebe um NOVO refresh (mais seguro)

---

## 3. App: accounts — Usuários e Empresas

### Models (accounts/models.py)

#### Empresa
```python
class Empresa(models.Model):
    nome = models.CharField(max_length=255)              # Nome da empresa
    cnpj = models.CharField(max_length=18, unique=True)  # CNPJ único
    email = models.EmailField()                          # Email de contato
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)  # Preenche sozinho na criação
```

**Explicação:** `unique=True` no CNPJ garante que não existam duas empresas com o mesmo CNPJ. `auto_now_add=True` faz o Django preencher a data automaticamente quando o registro é criado.

#### Usuario (modelo customizado)
```python
class Usuario(AbstractUser):  # Herda TUDO do User padrão do Django
    TIPO_USUARIO_CHOICES = (
        ('admin', 'Administrador'),
        ('gestor', 'Gestor'),
        ('tecnico', 'Técnico'),
    )
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, 
                                related_name='usuarios', null=True, blank=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES, default='tecnico')
    cargo = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
```

**O que é `AbstractUser`?** É a classe base de usuário do Django que já traz: `username`, `password`, `email`, `first_name`, `last_name`, `is_staff`, `is_superuser`, `is_active`. Ao herdar dela, **mantemos tudo isso** e adicionamos nossos campos extras.

**`ForeignKey`**: cria um relacionamento — cada usuário pertence a UMA empresa. `on_delete=models.CASCADE` significa: se a empresa for deletada, todos os usuários dela são deletados junto. `related_name='usuarios'` permite acessar `empresa.usuarios.all()` (todos os usuários daquela empresa).

**`choices`**: limita os valores possíveis. O banco armazena `'tecnico'` mas a interface mostra `'Técnico'`.

### Admin (accounts/admin.py)

```python
admin.site.register(Empresa)  # Registra Empresa no painel admin (configuração básica)

class CustomUserAdmin(UserAdmin):
    model = Usuario
    fieldsets = UserAdmin.fieldsets + (
        ('Informações da Empresa e Cargo', {
            'fields': ('empresa', 'tipo_usuario', 'cargo', 'telefone')
        }),
    )
admin.site.register(Usuario, CustomUserAdmin)
```

**O que faz?** O `UserAdmin` do Django já tem um formulário no painel admin para editar usuários (com seções como "Informações pessoais", "Permissões"). Nós **estendemos** esse formulário adicionando uma nova seção com nossos campos customizados. Sem isso, os campos `empresa`, `tipo_usuario` etc. não apareceriam no admin.

### Serializers (accounts/serializers.py)

```python
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'  # Serializa TODOS os campos do modelo

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'empresa', 'tipo_usuario', 'cargo', 'telefone']
```

**O que é um Serializer?** É o "tradutor" entre Python e JSON. Quando a API retorna dados, o serializer converte o objeto Python do Django para JSON. Quando o frontend envia dados, o serializer converte de JSON para objeto Python e valida os dados.

- `fields = '__all__'`: inclui todos os campos
- Lista explícita: controla exatamente quais campos aparecem na API (por segurança, não expomos a senha)

### Views (accounts/views.py)

```python
class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer     # Usa este serializer
    permission_classes = [IsGestor]           # Só Gestores e Admins acessam
    filter_backends = [filters.SearchFilter]  # Habilita busca
    search_fields = ['nome', 'cnpj']         # Campos onde a busca funciona

    def get_queryset(self):
        user = self.request.user
        if user.tipo_usuario == 'admin':
            return Empresa.objects.all()               # Admin vê todas
        if user.empresa:
            return Empresa.objects.filter(pk=user.empresa.pk)  # Só a sua
        return Empresa.objects.none()                  # Nenhuma
```

**O que é `ModelViewSet`?** É a classe mais poderosa do DRF. Com UMA classe, ele cria automaticamente **6 endpoints**:

| Método HTTP | URL | Ação | Nome DRF |
|---|---|---|---|
| `GET` | `/api/empresas/` | Listar todas | `list` |
| `POST` | `/api/empresas/` | Criar nova | `create` |
| `GET` | `/api/empresas/1/` | Ver uma | `retrieve` |
| `PUT` | `/api/empresas/1/` | Atualizar toda | `update` |
| `PATCH` | `/api/empresas/1/` | Atualizar parcial | `partial_update` |
| `DELETE` | `/api/empresas/1/` | Deletar | `destroy` |

### URLs (accounts/urls.py)

```python
router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresas')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('', include(router.urls)),
]
```

**O que é o Router?** É um componente do DRF que gera automaticamente todas as URLs para cada ViewSet. Um `router.register('empresas', ...)` gera `/empresas/`, `/empresas/<id>/`, etc. sem precisar escrever cada path manualmente.

### Endpoints gerados

| Método | URL | Quem acessa | O que faz |
|---|---|---|---|
| GET | `/api/empresas/` | Gestor/Admin | Lista empresas |
| POST | `/api/empresas/` | Gestor/Admin | Cria empresa |
| GET | `/api/empresas/{id}/` | Gestor/Admin | Detalhes de uma empresa |
| PUT/PATCH | `/api/empresas/{id}/` | Gestor/Admin | Atualiza empresa |
| DELETE | `/api/empresas/{id}/` | Gestor/Admin | Remove empresa |
| GET | `/api/usuarios/` | Gestor/Admin | Lista usuários |
| POST | `/api/usuarios/` | Gestor/Admin | Cria usuário |
| GET | `/api/usuarios/{id}/` | Gestor/Admin | Detalhes de um usuário |
| PUT/PATCH | `/api/usuarios/{id}/` | Gestor/Admin | Atualiza usuário |
| DELETE | `/api/usuarios/{id}/` | Gestor/Admin | Remove usuário |

---

## 4. App: authentication — Login e JWT

### URLs (authentication/urls.py)

```python
urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
```

### Endpoints

| Método | URL | Autenticação | O que faz |
|---|---|---|---|
| POST | `/api/auth/login/` | Não | Envia `username` + `password`, recebe tokens JWT |
| POST | `/api/auth/refresh/` | Não | Envia `refresh` token, recebe novo `access` token |
| GET | `/api/auth/me/` | Sim (JWT) | Retorna dados do usuário logado |
| POST | `/api/auth/change-password/` | Sim (JWT) | Troca a senha do usuário logado |

### Views customizadas

#### MeView — "Quem sou eu?"
```python
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)  # Serializa o usuário que fez a requisição
        return Response(serializer.data)
```

**O que é `request.user`?** O DRF decodifica o token JWT do header, busca o usuário no banco e coloca em `request.user`. Assim, sabemos exatamente quem está fazendo a requisição.

#### ChangePasswordView — Troca de senha
```python
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)   # Dados inválidos

        user = request.user
        if not user.check_password(serializer.validated_data['senha_atual']):
            return Response({'senha_atual': 'Senha atual incorreta.'}, status=400)

        user.set_password(serializer.validated_data['nova_senha'])  # Hash da nova senha
        user.save()
        return Response({'detail': 'Senha alterada com sucesso.'}, status=200)
```

**Detalhes importantes:**
- `check_password()` compara a senha digitada com o hash armazenado (nunca armazenamos a senha em texto puro)
- `set_password()` gera o hash da nova senha antes de salvar
- O serializer valida que `nova_senha == confirmar_nova_senha` e que a senha segue as regras do Django (tamanho mínimo, não pode ser totalmente numérica, etc.)

### Serializers

#### MeSerializer
```python
class MeSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'tipo_usuario', 'cargo', 'telefone', 'empresa', 'empresa_nome',
                  'is_staff', 'is_superuser']
        read_only_fields = fields  # Todos são somente leitura
```

**`source='empresa.nome'`**: campo calculado — pega o nome da empresa do usuário automaticamente. Assim o frontend recebe `"empresa_nome": "FabricaX"` junto com `"empresa": 1` (o ID).

#### ChangePasswordSerializer
```python
class ChangePasswordSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(required=True, write_only=True)
    nova_senha = serializers.CharField(required=True, write_only=True, min_length=6)
    confirmar_nova_senha = serializers.CharField(required=True, write_only=True)

    def validate_nova_senha(self, value):
        validate_password(value)  # Valida com as regras do Django
        return value

    def validate(self, data):
        if data['nova_senha'] != data['confirmar_nova_senha']:
            raise serializers.ValidationError({'confirmar_nova_senha': 'As senhas não coincidem.'})
        return data
```

**`write_only=True`**: esses campos só aparecem no INPUT. Nunca são retornados na resposta (por segurança).

**`validate_nova_senha`**: o DRF chama automaticamente métodos `validate_<campo>` para validação individual de cada campo.

**`validate`**: validação cruzada entre campos (compara duas senhas).

---

## 5. App: ativos — Equipamentos e Planos de Manutenção

### Models (ativos/models.py)

#### Equipamento
```python
class Equipamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipamentos')
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100, blank=True, null=True)
    fabricante = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    data_instalacao = models.DateField(blank=True, null=True)
    horimetro = models.FloatField(default=0)  # Horas de operação acumuladas

    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('manutencao', 'Em Manutenção'),
        ('inativo', 'Inativo'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
```

**`horimetro`**: é o campo mais importante deste modelo. Representa quantas horas o equipamento já operou. Quando esse valor muda, o **signal** `verificar_planos_por_horimetro` é disparado e pode gerar O.S. preditivas automaticamente.

#### EquipamentoLocalizacao
```python
class EquipamentoLocalizacao(models.Model):
    equipamento = models.OneToOneField(Equipamento, on_delete=models.CASCADE, related_name='localizacao')
    setor = models.CharField(max_length=100)
```

**`OneToOneField`**: cada equipamento tem NO MÁXIMO uma localização. É diferente de ForeignKey, que permite vários registros apontando para o mesmo.

#### PlanoManutencao
```python
class PlanoManutencao(models.Model):
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='planos_manutencao')
    nome_servico = models.CharField(max_length=200)       # Ex: "Troca de Óleo"
    descricao = models.TextField()
    intervalo_horas = models.FloatField()                  # A cada quantas horas fazer
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='medio')
    ativo = models.BooleanField(default=True)
    horimetro_ultima_os = models.FloatField(default=0)     # Quando foi a última vez

    def save(self, *args, **kwargs):
        if not self.pk:  # Se é um plano NOVO (ainda não tem ID)
            self.horimetro_ultima_os = self.equipamento.horimetro  # Começa a contar de agora
        super().save(*args, **kwargs)
```

**Lógica do Plano**: Se `intervalo_horas = 100` e `horimetro_ultima_os = 500`, a próxima O.S. será gerada quando o horímetro do equipamento atingir `600` (500 + 100).

**`save()` customizado**: sobrescreve o método `save()` para definir o `horimetro_ultima_os` automaticamente na criação. `self.pk` é o ID do registro — se não existe, é porque é novo.

### Endpoints gerados

| Método | URL | Quem acessa | O que faz |
|---|---|---|---|
| GET/POST | `/api/equipamentos/` | Gestor (CRUD) / Técnico (leitura) | Lista/Cria equipamentos |
| GET/PUT/PATCH/DELETE | `/api/equipamentos/{id}/` | Gestor/Admin | Detalhe/Edita/Remove |
| GET/POST | `/api/localizacao/` | Gestor/Técnico(leitura) | Localização dos equipamentos |
| GET/POST | `/api/planos-manutencao/` | Gestor/Admin | Planos de manutenção preditiva |

**Filtros disponíveis:**
- Equipamentos: `?empresa=1`, `?status=ativo`, `?tipo=motor_eletrico`, `?search=bomba`
- Planos: `?equipamento=1`, `?ativo=true`, `?prioridade=critico`

---

## 6. App: manutencao — Ordens de Serviço e Histórico

### Models (manutencao/models.py)

#### OrdemServico
```python
class OrdemServico(models.Model):
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='ordens_servico')
    responsavel = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='minhas_os')

    TIPO_OS_CHOICES = (
        ('corretiva',  'Corretiva'),   # Gerada por alerta de sensor
        ('preditiva',  'Preditiva'),   # Gerada por horímetro (plano)
        ('preventiva', 'Preventiva'),  # Criada manualmente
    )
    tipo_os = models.CharField(max_length=20, choices=TIPO_OS_CHOICES, default='preventiva')

    titulo = models.CharField(max_length=200)
    descricao = models.TextField()

    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='baixo')

    data_abertura = models.DateTimeField(default=timezone.now)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'concluida' and not self.data_conclusao:
            self.data_conclusao = timezone.now()  # Carimba a data automaticamente
        super().save(*args, **kwargs)
```

**`on_delete=models.SET_NULL`**: diferente do CASCADE — se o responsável for deletado, o campo fica `null` em vez de deletar a O.S. toda.

**`default=timezone.now`**: diferente de `auto_now_add` — aceita valores manuais, mas preenche com a hora atual se não informado.

**`save()` customizado**: quando alguém muda o status para "concluída", o Django automaticamente carimba a data de conclusão. O gestor não precisa preencher isso manualmente.

#### HistoricoManutencao
```python
class HistoricoManutencao(models.Model):
    ordem_servico = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='historico')
    descricao_servico = models.TextField()
    data_execucao = models.DateField()
    custo_pecas = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    custo_mao_de_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_de_obra
```

**`@property`**: cria um campo calculado que não existe no banco. `custo_total` é calculado em tempo real somando peças + mão de obra. Economiza espaço e evita inconsistência.

**`DecimalField`**: usado para valores monetários porque `FloatField` pode ter erros de precisão com dinheiro.

### Serializers (manutencao/serializers.py)

#### OrdemServicoSerializer — Validações de negócio
```python
class OrdemServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServico
        fields = '__all__'
        read_only_fields = ['data_abertura', 'data_conclusao']  # Frontend NÃO pode alterar

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.tipo_usuario == 'tecnico':
            responsavel = data.get('responsavel')
            if responsavel and responsavel != request.user:
                raise serializers.ValidationError({
                    'responsavel': 'Técnicos só podem assumir ordens para si mesmos.'
                })
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.tipo_usuario == 'tecnico':
            responsavel = validated_data.get('responsavel')
            if responsavel is None and validated_data.get('status') in ['andamento', 'concluida']:
                validated_data['responsavel'] = request.user  # Auto-atribui
        return super().create(validated_data)
```

**Lógica de negócio no serializer:**
1. **Técnico não pode atribuir O.S. para outro técnico** (validação no `validate`)
2. **Se um técnico muda o status para "andamento" sem definir responsável, ele é automaticamente atribuído** (lógica no `create` e `update`)
3. **Datas são read-only**: o frontend não pode manipular as datas de abertura/conclusão

### Views (manutencao/views.py)

```python
class OrdemServicoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedNoDeleteForTecnico, IsOwnerOrGestorOrUnassigned]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'prioridade', 'equipamento', 'responsavel', 'tipo_os']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['data_abertura', 'prioridade', 'status']
    ordering = ['-data_abertura']  # Padrão: mais recentes primeiro

    def get_queryset(self):
        user = self.request.user
        qs = OrdemServico.objects.select_related('equipamento', 'responsavel')
        
        if user.tipo_usuario == 'admin':
            return qs.all()
        
        if user.empresa:
            base_qs = qs.filter(equipamento__empresa=user.empresa)
            
            if user.tipo_usuario == 'tecnico':
                from django.db.models import Q
                # Técnico vê: O.S. dele OU O.S. sem responsável
                return base_qs.filter(Q(responsavel=user) | Q(responsavel__isnull=True))
            
            return base_qs  # Gestor vê todas da empresa
        return qs.none()
```

**`select_related`**: otimização de performance — faz um JOIN no SQL para pegar equipamento e responsável na mesma query, em vez de fazer uma query separada para cada.

**`Q objects`**: o `Q` permite construir queries complexas com `|` (OR) e `&` (AND). Aqui, o técnico vê O.S. onde (`responsavel = eu`) **OU** (`responsavel = null`).

**`ordering = ['-data_abertura']`**: o `-` significa ordem decrescente (mais recente primeiro).

### Endpoints

| Método | URL | O que faz |
|---|---|---|
| GET | `/api/ordens-servico/` | Lista O.S. (com filtros e busca) |
| POST | `/api/ordens-servico/` | Cria nova O.S. |
| GET | `/api/ordens-servico/{id}/` | Detalhe de uma O.S. |
| PUT/PATCH | `/api/ordens-servico/{id}/` | Atualiza O.S. |
| DELETE | `/api/ordens-servico/{id}/` | Remove (só Gestor/Admin) |
| GET/POST | `/api/historico/` | Lista/Cria histórico de manutenção |
| GET/PUT/PATCH/DELETE | `/api/historico/{id}/` | Detalhe/Edita/Remove histórico |

**Filtros disponíveis:**
- `?status=pendente`
- `?prioridade=critico`
- `?tipo_os=corretiva`
- `?equipamento=1`
- `?responsavel=2`
- `?search=motor` (busca no título e descrição)
- `?ordering=-prioridade` (ordenar por prioridade)

---

## 7. App: telemetria — Sensores e Leituras

### Models (telemetria/models.py)

#### Sensor
```python
class Sensor(models.Model):
    TIPO_SENSOR_CHOICES = (
        ('temperatura', 'Temperatura'),
        ('vibracao', 'Vibração'),
        ('pressao', 'Pressão'),
        ('corrente', 'Corrente Elétrica'),
        ('umidade', 'Umidade'),
    )

    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='sensores')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPO_SENSOR_CHOICES)
    unidade_medida = models.CharField(max_length=20)        # Ex: °C, mm/s, bar, A
    limite_alerta = models.FloatField()                      # Limite máximo absoluto
    limite_alerta_baixo_pct = models.FloatField(null=True)   # % do limite para alerta baixo
    limite_alerta_medio_pct = models.FloatField(null=True)   # % do limite para alerta médio
    limite_alerta_critico_pct = models.FloatField(null=True) # % do limite para alerta crítico
    ativo = models.BooleanField(default=True)
```

**Sistema de limites por percentual:**
- Se `limite_alerta = 100°C`:
  - `limite_alerta_baixo_pct = 70` → alerta baixo a partir de 70°C
  - `limite_alerta_medio_pct = 85` → alerta médio a partir de 85°C
  - `limite_alerta_critico_pct = 100` → alerta crítico a partir de 100°C

**Validação customizada (`clean`):** garante que `baixo < médio < crítico` e que todos estejam entre 0 e 100%.

#### Telemetria (leitura de sensor)
```python
class Telemetria(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='leituras')
    valor = models.FloatField()                      # O valor lido
    timestamp = models.DateTimeField(auto_now_add=True)  # Quando foi lido

    class Meta:
        ordering = ['-timestamp']  # Sempre ordenado do mais recente para o mais antigo
```

**Esta é a tabela que mais cresce no sistema.** Cada leitura de sensor cria um registro aqui. O simulador gera uma leitura a cada 7-10 segundos por sensor.

### Endpoints

| Método | URL | O que faz |
|---|---|---|
| GET/POST | `/api/telemetria/sensores/` | Lista/Cria sensores |
| GET/PUT/PATCH/DELETE | `/api/telemetria/sensores/{id}/` | Detalhe/Edita/Remove sensor |
| GET/POST | `/api/telemetria/leituras/` | Lista/Cria leituras de telemetria |
| GET/PUT/PATCH/DELETE | `/api/telemetria/leituras/{id}/` | Detalhe/Edita/Remove leitura |

**Filtros:**
- Sensores: `?equipamento=1`, `?tipo=temperatura`, `?ativo=true`
- Leituras: `?sensor=1`, `?sensor__equipamento=2`, `?valor_min=50`, `?valor_max=100`

---

## 8. App: alertas — Sistema de Alertas

### Model (alertas/models.py)

```python
class Alerta(models.Model):
    NIVEL_CHOICES = (
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('critico', 'Crítico'),
    )
    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('resolvido', 'Resolvido'),
        ('ignorado', 'Ignorado'),
    )

    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='alertas')
    tipo_alerta = models.CharField(max_length=100)   # Ex: "Alerta de Temperatura"
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='baixo')
    descricao = models.TextField()
    data_alerta = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
```

**Alertas são criados automaticamente pelos signals** quando uma leitura de telemetria ultrapassa os limites do sensor. Também podem ser criados manualmente via API.

### Endpoints

| Método | URL | O que faz |
|---|---|---|
| GET | `/api/alertas/` | Lista alertas (filtráveis) |
| POST | `/api/alertas/` | Cria alerta manual |
| GET | `/api/alertas/{id}/` | Detalhe do alerta |
| PATCH | `/api/alertas/{id}/` | Atualiza (ex: marcar como resolvido) |
| DELETE | `/api/alertas/{id}/` | Remove (só Gestor/Admin) |

**Filtros:** `?equipamento=1`, `?nivel=critico`, `?status=ativo`

---

## 9. App: exportacao — Exportação de Relatórios

### Como funciona

Os endpoints de exportação recebem um **formato** na URL (`csv`, `excel` ou `pdf`) e retornam o arquivo para download.

### Endpoints

| Método | URL | O que exporta |
|---|---|---|
| GET | `/api/exportar/ordens-servico/{formato}/` | Ordens de Serviço |
| GET | `/api/exportar/equipamentos/{formato}/` | Equipamentos |
| GET | `/api/exportar/alertas/{formato}/` | Alertas |
| GET | `/api/exportar/telemetria/{formato}/` | Leituras de Telemetria |
| GET | `/api/exportar/historico/{formato}/` | Histórico de Manutenção |
| GET | `/api/exportar/dashboard/{formato}/` | KPIs do Dashboard |

**Exemplo de uso:** `GET /api/exportar/ordens-servico/pdf/?status=pendente&prioridade=critico`

Isso gera um PDF com todas as O.S. pendentes e críticas da empresa do usuário logado.

### Estrutura do código

```python
class ExportarOrdensServicoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, formato):
        # 1. Isolamento multi-tenant (mesmo padrão das views normais)
        # 2. Aplica filtros dos query params
        # 3. Monta lista de colunas e linhas
        # 4. Despacha para o exporter correto
        return _despachar_formato(formato, 'ordens_servico', 'Ordens de Serviço', colunas, linhas)
```

A função `_despachar_formato` redireciona para o exporter correto:
- `exportar_csv()` → retorna arquivo `.csv`
- `exportar_excel()` → retorna arquivo `.xlsx` (usa `openpyxl`)
- `exportar_pdf()` → retorna arquivo `.pdf` (usa `WeasyPrint` ou `ReportLab`)

---

## 10. App: gemini_api — Inteligência Artificial

### Arquitetura da IA

O app de IA tem 4 componentes:

```
gemini_api/
├── cliente.py          → Comunicação com a API do Google Gemini
├── context_service.py  → Coleta dados do banco para dar contexto à IA
├── prompt_builder.py   → Monta os prompts com o contexto
├── views.py            → Endpoints da API
└── serializers.py      → Validação de input/output
```

### cliente.py — Cliente da API Gemini

```python
def generate_content(system_instruction, user_prompt, history=None, 
                     model_candidates=None, temperature=0.4):
    client = get_gemini_client()

    # Tenta múltiplos modelos em sequência (fallback)
    model_candidates = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
    
    for model_name in model_candidates:
        try:
            response = client.models.generate_content(...)
            return response.text, model_name
        except Exception as e:
            if recoverable:  # 503, 429, 404
                continue     # Tenta o próximo modelo
            raise            # Erro fatal, interrompe
    
    raise RuntimeError("Todos os modelos falharam.")
```

**Fallback de modelos**: se o `gemini-3.5-flash` estiver indisponível, tenta o `gemini-2.5-flash`, e depois o `gemini-flash-latest`. Isso garante que a IA funcione mesmo com instabilidade dos servidores do Google.

### context_service.py — Coleta de contexto

```python
def build_base_context(user):
    # Busca TODOS os dados relevantes da empresa do usuário
    return {
        'company_name': ...,
        'total_equipment': ...,
        'active_equipment': ...,
        'alerts': ...,            # Alertas ativos
        'open_orders': ...,       # O.S. abertas
        'telemetry': ...,         # Últimas leituras
        'equipment_kpis': ...,    # KPIs dos equipamentos
    }
```

**Por que isso existe?** A IA do Gemini não tem acesso direto ao banco de dados. Então coletamos os dados relevantes e enviamos como **contexto** junto com a pergunta do usuário. Assim a IA pode responder "Quantas O.S. estão abertas?" porque recebeu essa informação no prompt.

### prompt_builder.py — Monta os prompts

```python
def build_system_instruction(user, purpose):
    # Ajusta o tom da IA baseado no tipo de usuário
    if user.tipo_usuario == 'tecnico':
        focus = 'foco técnico de campo, sem dados financeiros'
    elif user.tipo_usuario == 'gestor':
        focus = 'foco em gestão e impacto financeiro'
    else:
        focus = 'visão estratégica e governança'
    
    return f"Você é a NanaSmart AI... {focus}"
```

**Personalização por perfil**: técnicos recebem respostas práticas de campo; gestores recebem análises gerenciais; admins recebem visão estratégica.

### Endpoints da IA

| Método | URL | O que faz | Quem acessa |
|---|---|---|---|
| POST | `/api/gemini/chat/` | Chat livre sobre manutenção | Todos |
| POST | `/api/gemini/ordens/analise/` | Análise das O.S. abertas | Todos |
| POST | `/api/gemini/ordens/sem-atribuicao/` | Sugere priorização de O.S. sem dono | Todos |
| POST | `/api/gemini/gestao/financeira/` | Análise financeira de custos | Só Gestor/Admin |

**Payload de todos os endpoints:**
```json
{
    "message": "Qual equipamento mais gasta com manutenção?",
    "history": [
        {"role": "user", "text": "Olá"},
        {"role": "model", "text": "Olá! Como posso ajudar?"}
    ]
}
```

O campo `history` permite manter uma conversa com contexto (a IA lembra das mensagens anteriores).

---

## 11. App: dashboards — KPIs e Métricas

### KpiService — Cálculo de indicadores

```python
class KpiService:
    @staticmethod
    def calcular_kpi(equipamento, os_queryset):
        # MTTR (Mean Time To Repair) — Tempo Médio de Reparo
        # Fórmula: média(data_conclusao - data_abertura) de cada O.S. concluída
        
        # MTBF (Mean Time Between Failures) — Tempo Médio Entre Falhas
        # Fórmula: média(data_abertura_OS_seguinte - data_conclusao_OS_anterior)
        
        # Disponibilidade = (MTBF / (MTBF + MTTR)) × 100
        
        # Custo total = soma(custo_pecas + custo_mao_de_obra) de todos os históricos
        
        return {
            'equipamento': ...,
            'mttr_hours': ...,
            'mtbf_hours': ...,
            'disponibilidade_porcentagem': ...,
            'total_manutencoes': ...,
            'custo_total_manutencao': ...,
        }
```

**O que são essas métricas?**
- **MTTR**: "Quando uma máquina quebra, quanto tempo leva para consertar?" (menor = melhor)
- **MTBF**: "De quanto em quanto tempo a máquina quebra?" (maior = melhor)
- **Disponibilidade**: "Que % do tempo a máquina funciona?" (mais perto de 100% = melhor)

### Endpoints

| Método | URL | O que faz |
|---|---|---|
| GET | `/api/dashboards/resumo/` | Dashboard completo (status, KPIs, alertas, O.S.) |
| GET | `/api/dashboards/kpis/` | KPIs individuais por equipamento |

**Filtros:**
- `?empresa_id=1` (admin filtra por empresa)
- `?dias=30` (só dados dos últimos 30 dias)
- `?equipamento_id=1` (KPI de um equipamento específico)

### Dashboard para Técnicos vs Gestores

O endpoint `/api/dashboards/resumo/` retorna dados diferentes dependendo do tipo de usuário:

**Técnico recebe:**
- Contagem de status dos equipamentos (apenas os que têm O.S. dele)
- Alertas ativos
- `minhas_ordens` (quantas O.S. ele tem)
- `ordens_sem_tecnico` (O.S. disponíveis para pegar)
- Últimas 5 O.S. recentes

**Gestor/Admin recebe:**
- Tudo do técnico +
- KPIs globais (MTTR, MTBF, Disponibilidade médios)
- Custo total de manutenção
- KPIs detalhados por equipamento

---

## 12. Signals — Automações Inteligentes

**Signals são o recurso mais importante e diferenciado deste projeto.** São "gatilhos" que o Django dispara automaticamente quando algo acontece no banco de dados.

### Signal 1: Telemetria → Alerta (telemetria/signals.py)

```
FLUXO: Nova leitura de sensor → checa limites → cria/atualiza Alerta
```

```python
@receiver(post_save, sender=Telemetria)
def checar_limites_telemetria(sender, instance, created, **kwargs):
    if not created:
        return  # Só processa leituras NOVAS

    sensor = instance.sensor
    valor = instance.valor
    limite = sensor.limite_alerta

    percentual = (valor / limite) * 100  # Ex: 85°C / 100°C = 85%

    # Determina o nível
    if percentual >= limite_critico:   nivel = 'critico'
    elif percentual >= limite_medio:   nivel = 'medio'
    elif percentual >= limite_baixo:   nivel = 'baixo'
    else: return  # Normal, nenhum alerta

    # Deduplicação: se já existe alerta ativo do mesmo tipo, SÓ atualiza se piorou
    alerta_existente = Alerta.objects.filter(
        equipamento=equipamento, tipo_alerta=tipo_alerta, status='ativo'
    ).first()

    if alerta_existente:
        if novo_nivel > nivel_atual:
            alerta_existente.nivel = nivel
            alerta_existente.save()  # Isso dispara o Signal 2!
        return

    # Cria novo alerta (isso dispara o Signal 2!)
    Alerta.objects.create(equipamento=equipamento, tipo_alerta=..., nivel=nivel, ...)
```

**Deduplicação**: evita criar 50 alertas iguais. Se já existe um alerta ativo de temperatura no mesmo equipamento, apenas atualiza o nível se piorou (de baixo para médio, de médio para crítico).

### Signal 2: Alerta → Ordem de Serviço (alertas/signals.py)

```
FLUXO: Novo alerta criado → gera O.S. corretiva automaticamente
```

```python
@receiver(post_save, sender=Alerta)
def vincular_ordem_servico_ao_alerta(sender, instance, created, **kwargs):
    if instance.status != 'ativo':
        return  # Só processa alertas ativos

    titulo_os = f"MANUTENÇÃO: {instance.tipo_alerta}"

    # Verifica se já existe O.S. ativa para este problema
    os_ativa = OrdemServico.objects.filter(
        equipamento=instance.equipamento,
        status__in=['pendente', 'andamento'],
        titulo=titulo_os
    ).first()

    if not os_ativa:
        # Cria nova O.S. corretiva
        OrdemServico.objects.create(
            equipamento=instance.equipamento,
            titulo=titulo_os,
            descricao=f"O.S. vinculada ao alerta: {instance.descricao}",
            prioridade=prioridade_alvo,
            tipo_os='corretiva',
            status='pendente'
        )
    else:
        # Se já existe, escala a prioridade se necessário
        if nova_prioridade > prioridade_atual:
            os_ativa.prioridade = prioridade_alvo
            os_ativa.save()
```

### Signal 3: Horímetro → O.S. Preditiva (ativos/signals.py)

```
FLUXO: Horímetro atualizado → checa planos de manutenção → gera O.S. preditiva
```

```python
@receiver(post_save, sender=Equipamento)
def verificar_planos_por_horimetro(sender, instance, **kwargs):
    for plano in instance.planos_manutencao.filter(ativo=True):
        proximo_disparo = plano.horimetro_ultima_os + plano.intervalo_horas

        if instance.horimetro < proximo_disparo:
            continue  # Ainda não chegou na hora

        # Verifica duplicação
        ja_existe = OrdemServico.objects.filter(
            equipamento=instance,
            tipo_os='preditiva',
            titulo__contains=plano.nome_servico,
            status__in=['pendente', 'andamento']
        ).exists()

        if ja_existe:
            continue  # Não duplica

        # Cria O.S. preditiva
        OrdemServico.objects.create(
            equipamento=instance,
            titulo=f"[PREDITIVA] {plano.nome_servico}",
            tipo_os='preditiva',
            prioridade=plano.prioridade,
            status='pendente',
        )

        # Atualiza o plano para o próximo ciclo
        plano.horimetro_ultima_os = instance.horimetro
        plano.save()
```

**Exemplo prático:**
- Plano "Troca de Óleo" com `intervalo_horas = 100`, `horimetro_ultima_os = 500`
- Equipamento atualizado para `horimetro = 605`
- `proximo_disparo = 500 + 100 = 600`
- `605 >= 600` → DISPARA! Cria O.S. preditiva
- Atualiza `horimetro_ultima_os = 605`, próximo disparo será em `705`

### Signal 4: O.S. sem descrição → IA gera descrição (ativos/signals.py)

```python
@receiver(pre_save, sender=OrdemServico)
def verificar_manutencao(sender, instance, **kwargs):
    if not instance.descricao:  # Se a O.S. foi criada sem descrição
        if api_key:  # Se a chave do Gemini está configurada
            texto = get_media_quebras_equipamentos(instance.equipamento.nome)
            instance.descricao = texto  # IA gera a descrição automaticamente
```

**`pre_save` vs `post_save`**: este usa `pre_save` porque precisa modificar o objeto ANTES de salvar. O `post_save` é chamado DEPOIS que já salvou no banco.

### Como os signals são ativados

No arquivo `apps.py` de cada app:
```python
class AtivosConfig(AppConfig):
    name = 'ativos'

    def ready(self):
        import ativos.signals  # Importa o arquivo de signals quando o app inicia
```

**`ready()`**: método chamado uma vez quando o Django inicializa. Importar os signals aqui garante que os `@receiver` sejam registrados.

---

## 13. Permissions — Sistema de Permissões Customizado

### IsGestor (accounts/permissions.py)
```python
class IsGestor(permissions.BasePermission):
    """Somente Gestores e Admins acessam."""
    def has_permission(self, request, view):
        return request.user.tipo_usuario in ['gestor', 'admin'] or request.user.is_superuser
```
**Onde é usado:** `EmpresaViewSet`, `UsuarioViewSet` — somente gestão de empresa/usuários.

### IsGestorOrReadOnly
```python
class IsGestorOrReadOnly(permissions.BasePermission):
    """Gestores fazem tudo. Técnicos só lêem."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return request.user.tipo_usuario in ['gestor', 'admin']
```
**Onde é usado:** `EquipamentoViewSet`, `PlanoManutencaoViewSet` — técnicos consultam, gestores editam.

**`SAFE_METHODS`**: GET, HEAD e OPTIONS são considerados "seguros" porque não alteram dados.

### IsAuthenticatedNoDeleteForTecnico
```python
class IsAuthenticatedNoDeleteForTecnico(permissions.BasePermission):
    """Todos fazem GET/POST/PATCH. Técnicos NÃO podem DELETE."""
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user.tipo_usuario in ['gestor', 'admin']
        return True
```
**Onde é usado:** `OrdemServicoViewSet`, `SensorViewSet`, `TelemetriaViewSet`, `AlertaViewSet`

### IsOwnerOrGestorOrUnassigned (manutencao/permissions.py)
```python
class IsOwnerOrGestorOrUnassigned(permissions.BasePermission):
    """
    Gestores: acesso total.
    Técnicos:
    - Podem editar se forem o responsável
    - Podem editar se a O.S. não tem responsável (para "pegar" a tarefa)
    - NÃO podem editar O.S. de outro técnico
    - NÃO podem atribuir O.S. para outra pessoa
    """
    def has_object_permission(self, request, view, obj):
        if user.tipo_usuario in ['gestor', 'admin']:
            return True

        if user.tipo_usuario == 'tecnico':
            if obj.responsavel and obj.responsavel != user:
                return False  # O.S. de outro técnico
            # Verifica se não está tentando atribuir para outro
            novo_responsavel_id = request.data.get('responsavel')
            if novo_responsavel_id and int(novo_responsavel_id) != user.id:
                return False
            return True
```

**`has_permission` vs `has_object_permission`:**
- `has_permission`: verifica antes de acessar qualquer objeto (para list/create)
- `has_object_permission`: verifica para um objeto específico (para retrieve/update/delete)

### Resumo de permissões por perfil

| Recurso | Admin | Gestor | Técnico |
|---|---|---|---|
| Empresas | CRUD total | CRUD (só sua) | ❌ Sem acesso |
| Usuários | CRUD total | CRUD (da empresa) | ❌ Sem acesso |
| Equipamentos | CRUD total | CRUD | Somente leitura |
| O.S. | CRUD total | CRUD | Lê/Edita (próprias + sem dono) |
| Sensores | CRUD total | CRUD | Lê/Cria (sem DELETE) |
| Alertas | CRUD total | CRUD | Lê/Cria (sem DELETE) |
| Dashboard | Todas empresas | Sua empresa | Só suas O.S. |
| IA Financeira | ✅ | ✅ | ❌ Bloqueado |

---

## 14. Simulador de Telemetria

Arquivo: `scripts/simulador_realtime.py`

### O que faz?
Simula sensores IoT enviando leituras de telemetria para o banco de dados. É como se fossem sensores reais conectados aos equipamentos.

### Como funciona
```
1. Busca todos os sensores ativos de equipamentos ativos
2. Para cada sensor, gera um valor próximo ao anterior (transição suave)
3. Salva no banco → isso dispara os signals automaticamente
4. Espera 7-10 segundos e repete
```

### Como rodar
```bash
python scripts/simulador_realtime.py
python scripts/simulador_realtime.py --cycles 10       # Só 10 ciclos
python scripts/simulador_realtime.py --dry-run          # Não salva no banco
python scripts/simulador_realtime.py --sensor 1 2 3     # Só estes sensores
python scripts/simulador_realtime.py --equipamento 1    # Só sensores deste equipamento
```

### Lógica de geração de valores
```python
def gerar_valor_sensor(sensor, valor_anterior):
    limite = sensor.limite_alerta    # Ex: 100°C
    alvo_minimo = limite * 0.62      # 62°C — o valor fica flutuando nessa faixa
    alvo_maximo = limite * 0.68      # 68°C — faixa "normal"

    flutuacao = random.uniform(-0.4, 0.4)  # Varia entre -0.4 e +0.4
    novo_valor = valor_anterior + flutuacao

    # Se saiu da faixa alvo, puxa de volta
    if novo_valor > alvo_maximo:
        novo_valor -= random.uniform(0.2, 0.5)
    elif novo_valor < alvo_minimo:
        novo_valor += random.uniform(0.2, 0.5)
```

Os valores ficam em torno de 65% do limite, simulando operação normal. Raramente atingem os limites de alerta.

---

## 15. Tabela Completa de Endpoints

### Autenticação
| Método | URL Completa | Descrição |
|---|---|---|
| POST | `/api/auth/login/` | Login — retorna tokens JWT |
| POST | `/api/auth/refresh/` | Renova token de acesso |
| GET | `/api/auth/me/` | Dados do usuário logado |
| POST | `/api/auth/change-password/` | Troca de senha |

### Contas (Empresas e Usuários)
| Método | URL Completa | Descrição |
|---|---|---|
| GET/POST | `/api/empresas/` | Listar/Criar empresas |
| GET/PUT/PATCH/DELETE | `/api/empresas/{id}/` | Detalhe/Editar/Remover empresa |
| GET/POST | `/api/usuarios/` | Listar/Criar usuários |
| GET/PUT/PATCH/DELETE | `/api/usuarios/{id}/` | Detalhe/Editar/Remover usuário |

### Ativos (Equipamentos)
| Método | URL Completa | Descrição |
|---|---|---|
| GET/POST | `/api/equipamentos/` | Listar/Criar equipamentos |
| GET/PUT/PATCH/DELETE | `/api/equipamentos/{id}/` | Detalhe/Editar/Remover equipamento |
| GET/POST | `/api/localizacao/` | Localização dos equipamentos |
| GET/PUT/PATCH/DELETE | `/api/localizacao/{id}/` | Detalhe/Editar/Remover localização |
| GET/POST | `/api/planos-manutencao/` | Planos de manutenção preditiva |
| GET/PUT/PATCH/DELETE | `/api/planos-manutencao/{id}/` | Detalhe/Editar/Remover plano |

### Manutenção (O.S. e Histórico)
| Método | URL Completa | Descrição |
|---|---|---|
| GET/POST | `/api/ordens-servico/` | Listar/Criar O.S. |
| GET/PUT/PATCH/DELETE | `/api/ordens-servico/{id}/` | Detalhe/Editar/Remover O.S. |
| GET/POST | `/api/historico/` | Listar/Criar histórico |
| GET/PUT/PATCH/DELETE | `/api/historico/{id}/` | Detalhe/Editar/Remover histórico |

### Telemetria
| Método | URL Completa | Descrição |
|---|---|---|
| GET/POST | `/api/telemetria/sensores/` | Listar/Criar sensores |
| GET/PUT/PATCH/DELETE | `/api/telemetria/sensores/{id}/` | Detalhe/Editar/Remover sensor |
| GET/POST | `/api/telemetria/leituras/` | Listar/Criar leituras |
| GET/PUT/PATCH/DELETE | `/api/telemetria/leituras/{id}/` | Detalhe/Editar/Remover leitura |

### Alertas
| Método | URL Completa | Descrição |
|---|---|---|
| GET/POST | `/api/alertas/` | Listar/Criar alertas |
| GET/PUT/PATCH/DELETE | `/api/alertas/{id}/` | Detalhe/Editar/Remover alerta |

### Dashboards
| Método | URL Completa | Descrição |
|---|---|---|
| GET | `/api/dashboards/resumo/` | Dashboard completo (KPIs + status + alertas) |
| GET | `/api/dashboards/kpis/` | KPIs individuais por equipamento |

### Exportação
| Método | URL Completa | Descrição |
|---|---|---|
| GET | `/api/exportar/ordens-servico/{csv\|excel\|pdf}/` | Exporta O.S. |
| GET | `/api/exportar/equipamentos/{csv\|excel\|pdf}/` | Exporta Equipamentos |
| GET | `/api/exportar/alertas/{csv\|excel\|pdf}/` | Exporta Alertas |
| GET | `/api/exportar/telemetria/{csv\|excel\|pdf}/` | Exporta Telemetria |
| GET | `/api/exportar/historico/{csv\|excel\|pdf}/` | Exporta Histórico |
| GET | `/api/exportar/dashboard/{csv\|excel\|pdf}/` | Exporta Dashboard KPIs |

### IA (Gemini)
| Método | URL Completa | Descrição |
|---|---|---|
| POST | `/api/gemini/chat/` | Chat livre sobre manutenção |
| POST | `/api/gemini/ordens/analise/` | Análise de O.S. abertas |
| POST | `/api/gemini/ordens/sem-atribuicao/` | Priorização de O.S. sem dono |
| POST | `/api/gemini/gestao/financeira/` | Análise financeira (Gestor/Admin) |

### Documentação automática
| Método | URL Completa | Descrição |
|---|---|---|
| GET | `/api/schema/` | Schema OpenAPI (JSON) |
| GET | `/api/schema/swagger-ui/` | Interface Swagger interativa |
| GET | `/api/schema/redoc/` | Documentação ReDoc |

---

## 16. Fluxos Automatizados

### Fluxo 1: Sensor detecta anomalia → O.S. automática

```
Simulador envia leitura
        │
        ▼
[Telemetria criada no banco]
        │
        ▼ (Signal: checar_limites_telemetria)
        │
  valor >= limite?
   /          \
  NÃO        SIM
  (nada)       │
               ▼
    [Alerta criado/atualizado]
               │
               ▼ (Signal: vincular_ordem_servico_ao_alerta)
               │
    [O.S. Corretiva criada]
```

### Fluxo 2: Horímetro atinge limite → O.S. preditiva

```
Horímetro do equipamento é atualizado
        │
        ▼ (Signal: verificar_planos_por_horimetro)
        │
  horimetro >= próximo_disparo?
   /          \
  NÃO        SIM
  (nada)       │
               ▼
  já existe O.S. aberta?
   /          \
  SIM        NÃO
  (nada)       │
               ▼
    [O.S. Preditiva criada]
    [Plano atualizado para próximo ciclo]
```

### Fluxo 3: Login e autenticação

```
Frontend envia username + password
        │
        ▼
  POST /api/auth/login/
        │
        ▼
  [Retorna access_token + refresh_token]
        │
        ▼
  Frontend usa access_token no header:
  Authorization: Bearer eyJ...
        │
        ▼
  Token expira (5 min)
        │
        ▼
  POST /api/auth/refresh/ (com refresh_token)
        │
        ▼
  [Novo access_token + novo refresh_token]
```

---

## 17. Conceitos-Chave para a Apresentação

### O que é uma API REST?
É uma interface que permite que programas se comuniquem via HTTP. O frontend (site/app) faz requisições HTTP para o backend (nosso Django) e recebe respostas em JSON.

### O que é JWT?
JSON Web Token — é um token criptografado que contém as informações do usuário. É enviado em todas as requisições no header `Authorization: Bearer <token>`. O servidor decodifica o token para saber quem é o usuário, sem precisar de sessão.

### O que é um ViewSet?
É uma classe do Django REST Framework que agrupa todas as ações de um recurso (listar, criar, ver, atualizar, deletar) em uma única classe. Economiza código.

### O que é um Serializer?
É o componente que converte dados entre Python↔JSON e faz validação. Funciona como um "formulário" da API.

### O que é um Signal?
É um mecanismo do Django que permite que partes desacopladas do código se comuniquem. Quando algo acontece (ex: salvou um registro), o Django avisa todos os "ouvintes" registrados.

### O que é Multi-Tenancy?
É o padrão onde múltiplas empresas compartilham a mesma aplicação, mas cada uma só vê seus próprios dados. Implementado no `get_queryset()` de cada view.

### O que são as métricas MTTR, MTBF e Disponibilidade?
- **MTTR** (Mean Time To Repair): tempo médio para consertar um equipamento
- **MTBF** (Mean Time Between Failures): tempo médio entre duas falhas
- **Disponibilidade**: percentual do tempo em que o equipamento está funcional

### O que é `select_related`?
Otimização do Django ORM. Em vez de fazer N+1 queries (uma para cada relacionamento), faz um JOIN SQL e busca tudo de uma vez. Melhora muito a performance.

### O que é `@property`?
Um método Python que se comporta como um campo. Permite criar campos calculados que não existem no banco (ex: `custo_total = custo_pecas + custo_mao_de_obra`).

### O que é o Router do DRF?
Gera automaticamente as URLs para cada ViewSet. Um `router.register('empresas', ...)` cria `/empresas/`, `/empresas/{id}/` com todos os métodos HTTP necessários.
