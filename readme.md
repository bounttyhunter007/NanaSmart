# 🏭 Plataforma de Manutenção Industrial Preditiva

> API REST para gestão inteligente de ativos industriais, ordens de manutenção e telemetria de sensores — construída com Django + Django REST Framework, pronta para integração com front-end Node.js.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.15-ff1709?style=flat)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=flat)
![License](https://img.shields.io/badge/Licença-Acadêmica-blue?style=flat)

</div>

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Tecnologias](#-tecnologias)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Como Rodar Localmente](#-como-rodar-localmente)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Endpoints da API](#-endpoints-da-api)
- [Segurança e Controle de Acesso](#-segurança-e-controle-de-acesso)
- [Alertas Automáticos](#-alertas-automáticos)
- [Documentação Interativa](#-documentação-interativa)
- [Integração com Front-end Node.js](#-integração-com-front-end-nodejs)
- [Roadmap](#-roadmap)
- [Problemas Comuns](#-problemas-comuns)
- [Contribuindo](#-contribuindo)

---

## 📌 Sobre o Projeto

Esta plataforma centraliza e digitaliza a gestão de manutenção industrial preditiva. Em vez de planilhas e processos manuais dispersos, a API oferece uma interface padronizada para que qualquer sistema — web, mobile ou desktop — possa:

- 📦 **Gerenciar ativos industriais** — máquinas, equipamentos e sensores da planta
- 🔧 **Controlar ordens de manutenção** — histórico, status e responsáveis por cada intervenção
- 📡 **Receber telemetria de sensores** — temperatura, vibração, pressão e corrente em tempo real
- 🚨 **Emitir alertas automáticos** — sistema de inteligência que gera alertas ao detectar anomalias
- 📊 **Exibir dashboards analíticos** — KPIs como MTBF, MTTR e Disponibilidade atualizados em tempo real
- 👥 **Controlar acesso por perfil** — isolamento automático de dados por empresa (multi-tenant) com restrições para Gestores e Técnicos (RBAC)

O projeto é modular: cada funcionalidade vive em seu próprio app Django. Adicionar um novo módulo não quebra o que já existe.

---

## 🛠 Tecnologias

### Back-end (esta API)

| Tecnologia | Versão | Função |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| Django | 5.2 | Framework web e ORM |
| Django REST Framework | 3.15 | Construção da API REST |
| djangorestframework-simplejwt | 5.x | Autenticação JWT segura |
| drf-spectacular | 0.27+ | Documentação automática Swagger/OpenAPI |
| django-cors-headers | 4.x | Permite requisições do front-end em outro domínio |
| django-filter | 24.x | Filtros avançados nos endpoints de listagem |
| Faker | — | Geração de dados falsos para testes e seed |
| SQLite | — | Banco de dados local (desenvolvimento) |
| PostgreSQL | — | Banco de dados em produção *(planejado)* |

### Front-end (projeto separado)

| Tecnologia | Função |
|---|---|
| Node.js | Runtime do servidor front-end |
| Vue.js | Progressive JavaScript Framework |

---

## 📁 Estrutura do Projeto

```
P.I-PlataformaManuntencaoWeb/
│
├── app/                        # ⚙️  Configurações centrais do Django
│   ├── settings.py             #     Banco, apps instalados, CORS, autenticação
│   ├── urls.py                 #     Mapa central de todas as rotas
│   ├── wsgi.py                 #     Servidor web (produção)
│   └── asgi.py                 #     Servidor assíncrono (WebSocket futuro)
│
├── accounts/                   # 👥  Módulo de usuários e autenticação
│   ├── models.py               #     Empresa e Usuario (AbstractUser com RBAC)
│   ├── serializers.py          #     Validação e serialização de dados
│   ├── permissions.py          #     Classes de permissão: IsGestor, IsGestorOrReadOnly
│   ├── views.py                #     EmpresaViewSet, UsuarioViewSet, MeView
│   └── urls.py                 #     Rotas: /api/accounts/... e /api/auth/me/
│
├── ativos/                     # 🏗️  Módulo de ativos industriais
│   ├── models.py               #     Equipamento e EquipamentoLocalizacao
│   ├── serializers.py
│   ├── views.py                #     CRUD de ativos + filtros por empresa
│   └── urls.py                 #     Rotas: /api/ativos/ e /api/localizacao/
│
├── manutencao/                 # 🔧  Módulo de ordens de manutenção
│   ├── models.py               #     OrdemServico e HistoricoManutencao
│   ├── serializers.py
│   ├── views.py                #     CRUD de manutenções + filtros por empresa
│   └── urls.py                 #     Rotas: /api/manutencao/ e /api/manutencao/historico/
│
├── telemetria/                 # 📡  Módulo de sensores e IoT
│   ├── models.py               #     Sensor e Telemetria (leituras)
│   ├── serializers.py
│   ├── signals.py              #     Dispara alertas automáticos a cada nova leitura
│   ├── views.py                #     CRUD de sensores e ingestão de telemetria
│   └── urls.py                 #     Rotas: /api/telemetria/sensores/ e /api/telemetria/leituras/
│
├── alertas/                    # 🚨  Módulo de alertas automáticos
│   ├── models.py               #     Modelo Alerta (gerado via Signals da telemetria)
│   ├── serializers.py
│   ├── views.py                #     Listagem e gestão de alertas
│   └── urls.py                 #     Rotas: /api/alertas/
│
├── dashboards/                 # 📊  Módulo de KPIs Industriais
│   ├── views.py                #     KpiDashboardView — calcula MTBF, MTTR e Disponibilidade
│   └── urls.py                 #     Rotas: /api/dashboards/kpis/
│
├── scripts/                    # 🛠️  Utilitários de linha de comando
│   ├── automate_seed.py        #     Setup automático completo (limpa + popula + cria admin)
│   └── seed_db.py              #     População manual interativa
│
├── manage.py                   # 🎛️  Ponto de entrada do Django (CLI)
├── requirements.txt            # 📦  Dependências Python do projeto
├── .env.example                # 🔐  Exemplo de variáveis de ambiente
└── .gitignore                  # 🙈  Arquivos ignorados pelo Git
```

---

## 🚀 Como Rodar Localmente

Siga os passos abaixo **na ordem**. Execute cada comando no terminal dentro da pasta do projeto.

### Pré-requisitos

Certifique-se de ter instalado:

- **Python 3.11+** → [python.org/downloads](https://www.python.org/downloads/)
- **Git** → [git-scm.com](https://git-scm.com/)

Para verificar:
```bash
python --version
git --version
```

---

### 1. Clone o repositório

```bash
git clone https://github.com/BugHunterAV/P.I-PlataformaManuntencaoWeb.git
cd P.I-PlataformaManuntencaoWeb
```

---

### 2. Crie e ative o ambiente virtual

O ambiente virtual isola as bibliotecas deste projeto do restante do seu computador. **Sempre use um.**

```bash
# Criar o ambiente virtual
python -m venv .venv
```

```bash
# Ativar — Linux / macOS
source .venv/bin/activate

# Ativar — Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Ativar — Windows (CMD)
.\.venv\Scripts\activate.bat
```

Quando ativo, você verá `(.venv)` no início da linha do terminal:

```
(.venv) C:\Projetos\P.I-PlataformaManuntencaoWeb>
```

> ⚠️ **Importante:** sempre que abrir um novo terminal, ative o `.venv` novamente antes de rodar qualquer comando.

---

### 3. Instale as dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo e preencha com seus valores:

```bash
# Linux / macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Edite o `.env` com um editor de texto. Veja a seção [Variáveis de Ambiente](#-variáveis-de-ambiente) para saber o que preencher.

---

### 5. Aplique as migrações

```bash
python manage.py migrate
```

Este comando cria todas as tabelas do banco de dados com base nos models do projeto.

---

### 6. População e superusuário (recomendado)

Para agilizar o setup, use o script de automação que limpa o banco, popula com dados de exemplo e cria o administrador padrão:

```bash
python scripts/automate_seed.py
```

Este script irá:
1. Limpar o banco de dados
2. Popular **5 empresas** e diversos usuários
3. Gerar **~200 ativos** com localizações industriais
4. Criar histórico de **7 dias de telemetria** para cada sensor
5. Garantir o superusuário `admin` com a senha `admin123`

---

### 7. (Alternativa) Setup manual

Se preferir fazer manualmente:

```bash
# Crie seu próprio superusuário
python manage.py createsuperuser

# (Opcional) Popule o banco interativamente
python scripts/seed_db.py
```

---

### 8. Inicie o servidor de desenvolvimento

```bash
# Porta padrão (8000)
python manage.py runserver

# Ou em outra porta, se a 8000 estiver ocupada
python manage.py runserver 9000
```

Se tudo estiver certo, você verá no terminal:

```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 5.2, using settings 'app.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL+C.
```

O servidor estará disponível em **http://localhost:8000**.

---

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto. **Nunca versione este arquivo** — ele já está no `.gitignore`.

```env
# Segurança — gere uma chave em: https://djecrety.ir/
DJANGO_SECRET_KEY=sua-chave-secreta-muito-longa-aqui

# Ambiente: True em desenvolvimento, False em produção
DJANGO_DEBUG=True

# Hosts permitidos (separados por vírgula)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Origens permitidas para o front-end Node.js (CORS)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Banco de dados em produção (deixe vazio para usar SQLite em dev)
DATABASE_URL=
```

---

## 🌐 Endpoints da API

Base URL em desenvolvimento: `http://localhost:8000/api/`

Todas as rotas (exceto login e refresh) exigem o header de autenticação:
```
Authorization: Bearer seu_token_aqui
```

### Autenticação

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `POST` | `/api/auth/login/` | Login — retorna access e refresh tokens | Livre |
| `POST` | `/api/auth/refresh/` | Renova o access token expirado | Ref. Token |
| `GET` | `/api/auth/me/` | Dados completos do usuário logado | JWT |

---

### Ativos industriais

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/ativos/` | Lista equipamentos da empresa |
| `POST` | `/api/ativos/` | Cadastra um novo equipamento |
| `GET` | `/api/ativos/{id}/` | Detalhe de um equipamento |
| `PUT` | `/api/ativos/{id}/` | Atualiza completamente |
| `PATCH` | `/api/ativos/{id}/` | Atualiza parcialmente |
| `DELETE` | `/api/ativos/{id}/` | Remove um equipamento |

**Filtros disponíveis:**
```
GET /api/ativos/?status=ativo
GET /api/ativos/?tipo=Motor+Elétrico
GET /api/ativos/?search=bomba
```

---

### Localização de ativos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/localizacao/` | Lista localização dos ativos da empresa |
| `POST` | `/api/localizacao/` | Define setor de um equipamento |
| `PATCH` | `/api/localizacao/{id}/` | Atualiza localização |

**Filtros disponíveis:**
```
GET /api/localizacao/?search=linha+A
GET /api/localizacao/?equipamento=5
```

---

### Manutenções (Ordens de Serviço)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/manutencao/` | Lista ordens da empresa |
| `POST` | `/api/manutencao/` | Cria uma nova ordem |
| `GET` | `/api/manutencao/{id}/` | Detalhe de uma ordem |
| `PUT` | `/api/manutencao/{id}/` | Atualiza uma ordem |
| `PATCH` | `/api/manutencao/{id}/` | Atualiza parcialmente |
| `DELETE` | `/api/manutencao/{id}/` | Remove uma ordem |

**Filtros disponíveis:**
```
GET /api/manutencao/?status=pendente
GET /api/manutencao/?prioridade=urgente
GET /api/manutencao/?equipamento=3
GET /api/manutencao/?responsavel=7
GET /api/manutencao/?search=bomba
GET /api/manutencao/?ordering=-data_abertura
GET /api/manutencao/?ordering=prioridade
```

> **Nota:** ao mudar o status de uma OS para `concluida`, a `data_conclusao` é preenchida automaticamente pelo servidor.

---

### Histórico de manutenção

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/manutencao/historico/` | Lista histórico e custos de manutenção |
| `POST` | `/api/manutencao/historico/` | Registra histórico de uma OS |

**Filtros disponíveis:**
```
GET /api/manutencao/historico/?ordem_servico=12
GET /api/manutencao/historico/?data_execucao_depois=2024-01-01
GET /api/manutencao/historico/?data_execucao_antes=2024-12-31
GET /api/manutencao/historico/?data_execucao_depois=2024-01-01&data_execucao_antes=2024-06-30
GET /api/manutencao/historico/?search=troca+de+rolamento
```

---

### Telemetria e Sensores

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/telemetria/sensores/` | Lista sensores da empresa |
| `POST` | `/api/telemetria/sensores/` | Cadastra novo sensor em equipamento |
| `GET` | `/api/telemetria/leituras/` | Lista histórico de telemetria |
| `POST` | `/api/telemetria/leituras/` | Envia nova leitura (pode gerar alertas automáticos) |

**Filtros disponíveis:**
```
GET /api/telemetria/sensores/?tipo_sensor=temperatura
GET /api/telemetria/sensores/?equipamento=4
GET /api/telemetria/sensores/?ativo=true
GET /api/telemetria/leituras/?sensor=2
GET /api/telemetria/leituras/?sensor__equipamento=4
```

---

### Alertas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/alertas/` | Lista alertas da empresa |
| `PATCH` | `/api/alertas/{id}/` | Atualiza status do alerta (ex: resolvido) |

**Filtros disponíveis:**
```
GET /api/alertas/?nivel=critico
GET /api/alertas/?status=ativo
GET /api/alertas/?equipamento=3
GET /api/alertas/?search=temperatura
```

---

### Dashboards (KPIs)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/dashboards/kpis/` | Retorna MTBF, MTTR e disponibilidade de todos os equipamentos da empresa |
| `GET` | `/api/dashboards/kpis/?equipamento_id={id}` | KPIs de um equipamento específico |

**Exemplo de resposta:**
```json
[
  {
    "equipamento": "Motor Elétrico M-01",
    "equipamento_id": 3,
    "mttr_hours": 4.5,
    "mtbf_hours": 312.0,
    "disponibilidade_porcentagem": 98.57,
    "total_manutencoes": 8
  }
]
```

---

## 🛡 Segurança e Controle de Acesso

### Modelo de permissões (RBAC)

A plataforma usa três perfis de usuário definidos no campo `tipo_usuario`:

| Perfil | O que pode fazer |
|---|---|
| `admin` | Acesso total — vê e edita dados de todas as empresas |
| `gestor` | Gerencia usuários, equipamentos e OS da própria empresa |
| `tecnico` | Lê dados e registra manutenções da própria empresa |

### Isolamento multi-tenant

Cada usuário vê **apenas os dados da sua empresa**. O isolamento é aplicado automaticamente em todos os endpoints via `get_queryset()`. Um técnico da empresa A nunca consegue acessar — nem listando, nem por ID — dados da empresa B.

Os endpoints protegidos e seus filtros de isolamento são:

| App | Filtro aplicado |
|---|---|
| `accounts` | `empresa=user.empresa` |
| `ativos` | `empresa=user.empresa` |
| `manutencao` | `equipamento__empresa=user.empresa` |
| `telemetria` | `equipamento__empresa=user.empresa` |
| `alertas` | `equipamento__empresa=user.empresa` |
| `dashboards` | `equipamento__empresa=user.empresa` |

### Endpoints que exigem perfil gestor

Os endpoints abaixo exigem `tipo_usuario = gestor` ou `admin`. Técnicos recebem `403 Forbidden`:

- `POST/PUT/PATCH/DELETE /api/ativos/`
- `POST/PUT/PATCH/DELETE /api/localizacao/`
- `GET/POST/PUT/DELETE /api/accounts/usuarios/`
- `GET/POST/PUT/DELETE /api/accounts/empresas/`

---

## 🚨 Alertas Automáticos

A plataforma possui um sistema de **inteligência preditiva** que monitora todas as entradas de telemetria e gera alertas instantâneos ao detectar valores fora do normal.

### Como funciona

Sempre que uma nova leitura chega via `POST /api/telemetria/leituras/`, o Django dispara um *Signal* que:

1. Identifica o tipo do equipamento (ex: Motor, Bomba)
2. Busca o limite máximo configurado para aquele sensor
3. Se o valor for maior que o limite, cria um registro em **Alertas** com nível "Crítico"

### Como configurar os limites

Os limites vivem no arquivo `telemetria/config_alertas.py`. Edite o dicionário `LIMITES_ALERTA`:

```python
LIMITES_ALERTA = {
    'Motor Elétrico': {
        'temperatura': 85.0,  # Dispara alerta se > 85°C
        'vibracao': 8.5       # Dispara alerta se > 8.5 mm/s
    },
    'Bomba Hidráulica': {
        'pressao': 12.0       # Dispara alerta se > 12 bar
    },
    'default': {
        'temperatura': 80.0   # Valor padrão para outros equipamentos
    }
}
```

> [!TIP]
> Você pode adicionar novos tipos de equipamentos ou sensores diretamente nesse arquivo sem precisar reiniciar o servidor em modo Debug.

### CORS

A API já está configurada com `django-cors-headers`. Para liberar o front-end, adicione a URL no `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Reinicie o servidor após qualquer mudança no `.env`.

---

## 📖 Documentação Interativa

Com o servidor rodando, acesse no navegador:

| Interface | URL | Descrição |
|---|---|---|
| **Swagger UI** | `http://localhost:8000/api/schema/swagger-ui/` | Interface visual — teste endpoints direto no browser |
| **ReDoc** | `http://localhost:8000/api/schema/redoc/` | Documentação em formato de referência |
| **Schema OpenAPI** | `http://localhost:8000/api/schema/` | JSON/YAML bruto para geração de clientes |
| **Admin Django** | `http://localhost:8000/admin/` | Painel administrativo completo |

> A documentação é **gerada automaticamente** pelo `drf-spectacular`. Cada novo endpoint adicionado ao projeto aparece no Swagger UI sem configuração extra.

---

## 🔗 Integração com Front-end Node.js

Esta API foi projetada para ser consumida por um front-end Node.js separado (React, Next.js, Vue ou similar).

### Fluxo de autenticação

**1. Login — obter os tokens:**
```javascript
const response = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'seu_usuario', password: 'sua_senha' })
})
const { access, refresh } = await response.json()
localStorage.setItem('access_token', access)
localStorage.setItem('refresh_token', refresh)
```

**2. Requisições autenticadas:**
```javascript
const token = localStorage.getItem('access_token')

const response = await fetch('http://localhost:8000/api/ativos/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
const ativos = await response.json()
```

**3. Criar um ativo:**
```javascript
await fetch('http://localhost:8000/api/ativos/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nome: 'Bomba Centrífuga B-01',
    numero_serie: 'BC-2024-001',
    status: 'ativo'
  })
})
```

**4. Enviar leitura de sensor:**
```javascript
await fetch('http://localhost:8000/api/telemetria/leituras/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    sensor: 1,
    valor: 95.5
  })
})
```

**5. Buscar KPIs de um equipamento:**
```javascript
const response = await fetch('http://localhost:8000/api/dashboards/kpis/?equipamento_id=3', {
  headers: { 'Authorization': `Bearer ${token}` }
})
const kpis = await response.json()
```

---

## 🗺 Roadmap

### ✅ Concluído

- [x] Estrutura base do projeto Django
- [x] CRUD de ativos industriais (Equipamentos e Localização)
- [x] CRUD de ordens de manutenção (OS e Histórico)
- [x] CRUD de usuários e empresas
- [x] App `telemetria` — Sensores e IoT
- [x] App `alertas` — Inteligência preditiva via Signals
- [x] Histórico de manutenção e controle de custos
- [x] App `dashboards` — KPIs: MTBF, MTTR e Disponibilidade
- [x] Autenticação JWT (SimpleJWT)
- [x] RBAC — perfis Gestor, Técnico e Admin
- [x] **Isolamento multi-tenant** — cada usuário vê apenas dados da própria empresa
- [x] **Correção de segurança** — endpoints de alertas e telemetria protegidos com autenticação
- [x] **Filtros de data por intervalo** no histórico de manutenção
- [x] **Ordenação configurável** nas ordens de serviço
- [x] Scripts de automação de população e setup
- [x] Documentação automática (Swagger + ReDoc via drf-spectacular)

### 🔄 Em Desenvolvimento

- [ ] Testes automatizados (pytest-django)
- [ ] Paginação global configurável
- [ ] Suporte a PostgreSQL em produção
- [ ] Deploy (Railway / Render)

---

## 🐛 Problemas Comuns

**`python` não é reconhecido como comando**
No Windows, tente `py` no lugar de `python`. Se não funcionar, reinstale o Python marcando a opção **"Add Python to PATH"**.

**`No module named django`**
O ambiente virtual não está ativo. Execute o comando de ativação do Passo 2 novamente.

**Porta 8000 já está em uso**
```bash
python manage.py runserver 9000
```

**Script de ativação bloqueado no PowerShell (Windows)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Erro ao aplicar migrações**
```bash
python manage.py migrate --run-syncdb
```

**Erro de CORS no front-end**
Confirme que a URL do seu front-end está em `CORS_ALLOWED_ORIGINS` no `.env` e reinicie o servidor Django após a mudança.

**`django.core.exceptions.ImproperlyConfigured`**
O arquivo `.env` provavelmente não foi criado. Siga o Passo 4 da instalação.

**`403 Forbidden` em um endpoint**
Você está logado com um técnico tentando acessar um endpoint restrito a gestores. Troque para um usuário com `tipo_usuario = gestor` ou `admin`.

**Resposta retorna lista vazia `[]` mesmo com dados no banco**
Seu usuário não tem empresa vinculada (`empresa = null`). Associe o usuário a uma empresa pelo painel admin em `http://localhost:8000/admin/`.

---

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie uma branch descritiva:
   ```bash
   git checkout -b feat/nome-da-funcionalidade
   ```
3. Faça commits claros e descritivos:
   ```bash
   git commit -m "feat: adiciona filtro de data por intervalo no histórico"
   ```
4. Envie para o seu fork:
   ```bash
   git push origin feat/nome-da-funcionalidade
   ```
5. Abra um **Pull Request** descrevendo o que foi feito e por quê

### Convenção de commits

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug ou segurança |
| `docs:` | Alteração na documentação |
| `refactor:` | Refatoração sem mudança de comportamento |
| `chore:` | Configurações, dependências, tarefas auxiliares |

---

## 📄 Licença

Projeto acadêmico — Projeto Interdisciplinar. Todos os direitos reservados aos autores.

---

<div align="center">
  Feito com Python 🐍 e Django 🎸
</div>