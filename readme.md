# 🏭 Plataforma de Manutenção Industrial Preditiva

> API REST completa para gestão inteligente de ativos industriais, ordens de manutenção, telemetria IoT e alertas preditivos.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.15-ff1709?style=flat)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=flat)

</div>

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Tecnologias](#-tecnologias)
- [Endpoints da API](#-endpoints-da-api)
- [Como Rodar Localmente](#-como-rodar-localmente)
- [Credenciais Padrão](#-credenciais-padrão)
- [Segurança e Controle de Acesso](#-segurança-e-controle-de-acesso)
- [Documentação Interativa](#-documentação-interativa)
- [Problemas Comuns](#-problemas-comuns)
- [Roadmap](#-roadmap)

---

## 📌 Sobre o Projeto

Esta é uma API REST desenvolvida em Django para gestão completa de manutenção industrial preditiva. Permite controlar equipamentos, sensores em tempo real, alertas automáticos, ordens de serviço e dashboards executivos.

---

## 🛠 Tecnologias

- Python 3.11+
- Django 5.2
- Django REST Framework
- SimpleJWT (Autenticação JWT)
- drf-spectacular (Swagger/OpenAPI)
- Faker (para dados de teste)

---

## 🔗 Endpoints da API

**Base URL:** `http://localhost:8000/api/`

### 🔐 Autenticação

| Método | Endpoint                        | Descrição                                      |
|--------|----------------------------------|------------------------------------------------|
| POST   | /api/auth/token/                | Login - Obter token JWT                        |
| POST   | /api/auth/token/refresh/        | Renovar token JWT                              |
| GET    | /api/auth/me/                   | Dados do usuário logado                        |

### 🏢 Empresas

| Método | Endpoint                        | Descrição                  |
|--------|----------------------------------|----------------------------|
| GET    | /api/empresas/                  | Listar empresas            |
| POST   | /api/empresas/                  | Criar empresa              |

### 👤 Usuários

| Método | Endpoint                        | Descrição                  |
|--------|----------------------------------|----------------------------|
| GET    | /api/usuarios/                  | Listar usuários            |
| POST   | /api/usuarios/                  | Criar usuário              |

### ⚙️ Equipamentos

| Método | Endpoint                        | Descrição                        |
|--------|----------------------------------|----------------------------------|
| GET    | /api/equipamentos/              | Listar equipamentos              |
| POST   | /api/equipamentos/              | Cadastrar equipamento            |
| GET    | /api/equipamentos/{id}/         | Detalhe                          |
| PUT/PATCH/DELETE | /api/equipamentos/{id}/ | Atualizar / Excluir              |

### 📍 Localização

| Método | Endpoint                        | Descrição                  |
|--------|----------------------------------|----------------------------|
| GET    | /api/localizacao/               | Listar localizações        |
| POST   | /api/localizacao/               | Cadastrar localização      |

### 🚨 Alertas

| Método | Endpoint                        | Descrição                        |
|--------|----------------------------------|----------------------------------|
| GET    | /api/alertas/                   | Listar alertas                   |
| PATCH  | /api/alertas/{id}/              | Marcar como resolvido            |

### 🛠️ Ordens de Serviço

| Método | Endpoint                        | Descrição                        |
|--------|----------------------------------|----------------------------------|
| GET    | /api/ordens-servico/            | Listar ordens                    |
| POST   | /api/ordens-servico/            | Criar ordem                      |
| GET    | /api/ordens-servico/{id}/       | Detalhe                          |
| PATCH  | /api/ordens-servico/{id}/       | Atualizar status                 |

### 📡 Telemetria

| Método | Endpoint                           | Descrição                        |
|--------|-------------------------------------|----------------------------------|
| GET    | /api/telemetria/sensores/          | Listar sensores                  |
| POST   | /api/telemetria/sensores/          | Cadastrar sensor                 |
| GET    | /api/telemetria/leituras/          | Listar leituras                  |
| POST   | /api/telemetria/leituras/          | Enviar nova leitura              |

### 📊 Dashboards

| Método | Endpoint                        | Descrição                        |
|--------|----------------------------------|----------------------------------|
| GET    | /api/dashboards/resumo/         | Resumo geral e KPIs              |

---

## 🚀 Como Rodar Localmente

1. Ative o ambiente virtual:
   .venv\Scripts\activate

2. Instale as dependências:
   pip install -r requirements.txt

3. Aplique as migrações:
   python manage.py migrate

4. Popule o banco com dados de teste:
   python scripts/automate_seed.py

5. Inicie o servidor:
   python manage.py runserver

---

## 🔑 Credenciais Padrão

- **Django Admin**:  
  Usuário: `admin`  
  Senha: `admin123`

- **Usuários normais** (gestores e técnicos):  
  Senha padrão: `123`

---

## 🛡 Segurança e Controle de Acesso

- Autenticação via **JWT** (Bearer Token)
- Isolamento multi-tenant: cada usuário vê apenas dados da sua empresa
- Perfis: `admin`, `gestor` e `tecnico`

---

## 📖 Documentação Interativa

Acesse com o servidor rodando:

- Swagger UI: http://localhost:8000/api/schema/swagger-ui/
- ReDoc: http://localhost:8000/api/schema/redoc/
- Django Admin: http://localhost:8000/admin/

---

## 🐛 Problemas Comuns

- `python` não reconhecido → Use `py` no Windows
- Ambiente virtual não ativado → Rode o activate novamente
- Porta 8000 em uso → Use `python manage.py runserver 9000`
- Erro 403 Forbidden → Usuário sem permissão (técnico tentando criar equipamento)
- Lista vazia mesmo tendo dados → Usuário não tem empresa vinculada

---

## 🗺 Roadmap

### ✅ Concluído
- Estrutura completa dos apps
- CRUD de Equipamentos, Ordens de Serviço, Alertas e Telemetria
- Autenticação JWT + RBAC
- Isolamento por empresa
- Dashboards e KPIs
- Script de seed automático

### 🔄 Em Desenvolvimento
- Testes automatizados
- Paginação avançada
- Deploy em produção

---

**Pronto!**  
Este README está completo, organizado, atualizado e fácil de ler. Você pode colar diretamente no arquivo.

Se quiser deixar alguma seção mais curta, mais longa ou adicionar algo específico, me avise!