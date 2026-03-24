# 🏭 Plataforma de Manutenção Industrial Preditiva

> API REST para gestão inteligente de ativos industriais, ordens de manutenção e telemetria de sensores — construída com Django + Django REST Framework, pronta para integração com front-end Node.js.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.16-ff1709?style=flat)
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
- 📡 **Receber telemetria de sensores** — temperatura, vibração, pressão e corrente em tempo real *(em desenvolvimento)*
- 🚨 **Emitir alertas automáticos** — quando leituras ultrapassam limites críticos *(planejado)*
- 📊 **Exibir dashboards analíticos** — KPIs como MTBF, MTTR e disponibilidade *(planejado)*
- 👥 **Controlar acesso por perfil** — admin, técnico e operador com permissões distintas

O projeto é modular: cada funcionalidade vive em seu próprio app Django. Adicionar um novo módulo não quebra o que já existe.

---

## 🛠 Tecnologias

### Back-end (esta API)

| Tecnologia | Versão | Função |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| Django | 5.2 | Framework web e ORM |
| Django REST Framework | 3.16 | Construção da API REST |
| drf-spectacular | latest | Documentação automática Swagger/OpenAPI |
| django-cors-headers | 4.9 | Permite requisições do front-end em outro domínio |
| django-filter | 25.2 | Filtros avançados nos endpoints de listagem |
| Faker | 40.11 | Geração de dados falsos para testes |
| SQLite | — | Banco de dados local (desenvolvimento) |
| PostgreSQL | — | Banco de dados em produção *(planejado)* |

### Front-end (projeto separado)

| Tecnologia | Função |
|---|---|
| Node.js | Runtime do servidor front-end |
| *(framework a definir)* | React, Next.js ou Vue — a ser escolhido |

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
│   ├── models.py               #     Modelo de usuário e perfis
│   ├── serializers.py          #     Validação e serialização de dados
│   ├── views.py                #     Login, registro, logout
│   └── urls.py                 #     Rotas: /api/accounts/...
│
├── ativos/                     # 🏗️  Módulo de ativos industriais
│   ├── models.py               #     Máquinas, equipamentos, localização
│   ├── serializers.py
│   ├── views.py                #     CRUD de ativos + filtros
│   └── urls.py                 #     Rotas: /api/ativos/...
│
├── manutencao/                 # 🔧  Módulo de ordens de manutenção
│   ├── models.py               #     Ordens, histórico, status, técnico
│   ├── serializers.py
│   ├── views.py                #     CRUD de manutenções + filtros
│   └── urls.py                 #     Rotas: /api/manutencao/...
│
├── telemetria/                 # 📡  Módulo de sensores (em desenvolvimento)
│   ├── models.py               #     LeituraSensor: tipo, valor, timestamp
│   ├── serializers.py
│   ├── views.py
│   └── urls.py                 #     Rotas: /api/telemetria/...
│
├── dashboards/                 # 📊  Módulo de KPIs (planejado)
│
├── alertas/                    # 🚨  Módulo de alertas automáticos (planejado)
│
├── manage.py                   # 🎛️  Ponto de entrada do Django (CLI)
├── requeriments.txt            # 📦  Dependências Python do projeto
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
pip install -r requeriments.txt
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

### 5. Aplique as migrações do banco de dados

As migrações criam as tabelas no banco com base nos models definidos no código.

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6. (Opcional) Crie um superusuário

O superusuário tem acesso total ao painel administrativo do Django.

```bash
python manage.py createsuperuser
```

O terminal pedirá nome de usuário, e-mail (opcional) e senha. Escolha uma senha segura.

---

### 7. Inicie o servidor de desenvolvimento

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

Todas as rotas (exceto login e registro) exigem o header de autenticação:
```
Authorization: Token seu_token_aqui
```

### Autenticação

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `POST` | `/api/accounts/register/` | Cadastra um novo usuário | Não |
| `POST` | `/api/accounts/login/` | Login — retorna o token | Não |
| `POST` | `/api/accounts/logout/` | Invalida o token atual | Sim |
| `GET` | `/api/accounts/me/` | Dados do usuário logado | Sim |

### Ativos industriais

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/ativos/` | Lista todos os ativos (suporta filtros) |
| `POST` | `/api/ativos/` | Cadastra um novo ativo |
| `GET` | `/api/ativos/{id}/` | Detalhe de um ativo específico |
| `PUT` | `/api/ativos/{id}/` | Atualiza completamente um ativo |
| `PATCH` | `/api/ativos/{id}/` | Atualiza parcialmente um ativo |
| `DELETE` | `/api/ativos/{id}/` | Remove um ativo |

**Filtros disponíveis:**
```
GET /api/ativos/?status=ativo
GET /api/ativos/?search=bomba
GET /api/ativos/?ordering=-criado_em
GET /api/ativos/?criado_depois=2024-01-01&status=ativo
```

### Manutenções

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/manutencao/` | Lista todas as ordens de manutenção |
| `POST` | `/api/manutencao/` | Cria uma nova ordem |
| `GET` | `/api/manutencao/{id}/` | Detalhe de uma ordem específica |
| `PUT` | `/api/manutencao/{id}/` | Atualiza uma ordem |
| `PATCH` | `/api/manutencao/{id}/` | Atualiza parcialmente |
| `DELETE` | `/api/manutencao/{id}/` | Remove uma ordem |

### Telemetria *(em desenvolvimento)*

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/telemetria/leituras/` | Lista leituras de sensores |
| `POST` | `/api/telemetria/leituras/` | Envia uma nova leitura de sensor |
| `GET` | `/api/telemetria/leituras/?ativo={id}` | Filtra leituras por ativo |
| `GET` | `/api/telemetria/leituras/?tipo=temperatura` | Filtra por tipo de sensor |

---

## 📖 Documentação Interativa

Com o servidor rodando, acesse no navegador:

| Interface | URL | Descrição |
|---|---|---|
| **Swagger UI** | `http://localhost:8000/api/schema/swagger-ui/` | Interface visual — teste endpoints direto no browser |
| **ReDoc** | `http://localhost:8000/api/schema/redoc/` | Documentação em formato de referência |
| **Schema OpenAPI** | `http://localhost:8000/api/schema/` | JSON/YAML bruto para geração de clientes |
| **Admin Django** | `http://localhost:8000/admin/` | Painel administrativo completo |

> A documentação é **gerada automaticamente** pelo `drf-spectacular`. Cada novo endpoint adicionado ao projeto aparece no Swagger UI sem nenhuma configuração extra.

---

## 🔗 Integração com Front-end Node.js

Esta API foi projetada para ser consumida por um front-end Node.js separado (React, Next.js, Vue ou similar).

### Fluxo de autenticação

**1. Login — obter o token:**
```javascript
const response = await fetch('http://localhost:8000/api/accounts/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'seu_usuario', password: 'sua_senha' })
})
const { token } = await response.json()
// Salve o token (localStorage, cookie, contexto global)
localStorage.setItem('token', token)
```

**2. Requisições autenticadas:**
```javascript
const token = localStorage.getItem('token')

const response = await fetch('http://localhost:8000/api/ativos/', {
  headers: {
    'Authorization': `Token ${token}`,
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
    'Authorization': `Token ${token}`,
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
    'Authorization': `Token ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    ativo: 1,
    tipo: 'temperatura',
    valor: 78.5,
    unidade: '°C'
  })
})
```

### CORS

A API já está configurada com `django-cors-headers`. Para liberar o seu front-end, adicione a URL no `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Reinicie o servidor após qualquer mudança no `.env`.

---

## 🗺 Roadmap

### ✅ Concluído
- [x] Estrutura base do projeto Django
- [x] CRUD de ativos industriais
- [x] CRUD de ordens de manutenção
- [x] Sistema de autenticação por token
- [x] Documentação automática Swagger UI via drf-spectacular
- [x] Configuração de CORS para front-end externo

### 🔄 Em Desenvolvimento
- [ ] App `telemetria` — leituras de sensores por ativo
- [ ] Filtros avançados por data e intervalo de valor
- [ ] Permissões por perfil de usuário (admin, técnico, operador)

### 📋 Planejado
- [ ] App `alertas` — notificações automáticas quando leituras ultrapassam limites
- [ ] App `dashboards` — KPIs: MTBF, MTTR, taxa de disponibilidade
- [ ] Autenticação JWT (mais segura que token simples)
- [ ] Migração do banco para PostgreSQL em produção
- [ ] Exportação de relatórios em PDF
- [ ] Deploy em servidor (Railway / Render / VPS)
- [ ] Testes automatizados com pytest

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

**Erro de CORS no front-end Node.js**
Confirme que a URL do seu front-end está em `CORS_ALLOWED_ORIGINS` no `.env` e reinicie o servidor Django após a mudança.

**`django.core.exceptions.ImproperlyConfigured`**
O arquivo `.env` provavelmente não foi criado. Siga o Passo 4 da instalação.

---

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie uma branch descritiva:
   ```bash
   git checkout -b feat/telemetria-sensores
   ```
3. Faça commits claros e descritivos:
   ```bash
   git commit -m "feat: adiciona modelo LeituraSensor com limites de alerta"
   ```
4. Envie para o seu fork:
   ```bash
   git push origin feat/telemetria-sensores
   ```
5. Abra um **Pull Request** descrevendo o que foi feito e por quê

### Convenção de commits

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
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
