# 🏭 Plataforma de Manutenção Industrial Preditiva

> API REST completa e profissional para gestão inteligente de ativos industriais, manutenção preditiva, ordens de serviço, telemetria IoT em tempo real, alertas automáticos e dashboards executivos.

---

## 📌 Sobre o Projeto

Esta é uma API REST desenvolvida em Django que tem como objetivo centralizar e digitalizar toda a gestão de manutenção industrial de uma empresa. 

O sistema permite que indústrias gerenciem de forma eficiente seus equipamentos, monitorem parâmetros em tempo real através de sensores IoT, recebam alertas automáticos quando algum parâmetro sai do normal, controlem todas as ordens de serviço desde a abertura até o fechamento, e tenham visibilidade gerencial através de dashboards com indicadores importantes como MTBF, MTTR e Disponibilidade dos ativos.

O projeto foi construído com foco em modularidade, segurança, escalabilidade, isolamento de dados por empresa (multi-tenant) e fácil integração com o Front-end em Vue.js.

---

## 🛠 Tecnologias Utilizadas

- Python 3.11 ou superior
- Django 5.2
- Django REST Framework
- djangorestframework-simplejwt para autenticação com tokens JWT
- drf-spectacular para geração automática de documentação Swagger e ReDoc
- django-cors-headers para permitir requisições do front-end
- django-filter para filtros avançados nas listagens
- Faker para geração de dados realistas durante o seed
- SQLite (suportado para desenvolvimento rápido)
- PostgreSQL (Banco de dados oficial de produção e desenvolvimento)

---

## 🚀 Como Rodar Localmente

Siga os passos abaixo na ordem exata:

1. Abra o terminal na pasta raiz do projeto e ative o ambiente virtual com o comando:
   .\.venv\Scripts\activate   (no Windows PowerShell)

2. Instale todas as dependências do projeto com o comando:
   pip install -r requirements.txt

3. Configure o seu banco de dados PostgreSQL (caso ainda não tenha feito):
   - Certifique-se de que o serviço do PostgreSQL está rodando.
   - Crie um banco de dados chamado `manutencao`.
   - Ajuste o usuário e senha no arquivo `app/settings.py` se necessário.

4. Execute as migrações para criar as tabelas no banco de dados:
   python manage.py migrate

4. Popule o banco de dados com dados realistas. Veja a seção [Scripts de Utilidade](#-scripts-de-utilidade) para detalhes:
   python scripts/seed_db.py

5. Inicie o servidor de desenvolvimento com o comando:
   python manage.py runserver
   Caso a porta 8000 esteja ocupada, utilize:
   python manage.py runserver 9000

Após iniciar, a API estará acessível em: http://localhost:8000

---

## 🧪 Como Executar os Testes

O projeto utiliza o framework de testes nativo do Django. Os testes são isolados e não afetam o banco de dados de produção.

1. Para rodar todos os testes do sistema:
   python manage.py test

2. Para rodar testes de um módulo específico (ex: ativos):
   python manage.py test ativos

3. Para ver o log detalhado dos testes:
   python manage.py test -v 2

---

## 🛠️ Scripts de Utilidade

O projeto conta com scripts na pasta `scripts/` para facilitar o desenvolvimento e testes de carga.

### 1. Seed de Banco de Dados (`seed_db.py`)
Popula o banco com uma estrutura completa, multi-tenant e realista (inclui Horímetros e Planos de Manutenção).

*   **Uso Padrão** (3 empresas, 15 equipamentos/cada):
    ```bash
    python scripts/seed_db.py
    ```
*   **Uso Customizado** (Ex: 5 empresas, 30 equipamentos/cada):
    ```bash
    python scripts/seed_db.py --empresas 5 --equipamentos 30
    ```

### 2. Teste de Estresse de Telemetria (`stress_telemetry.py`)
Simula o envio massivo de dados de sensores para testar a performance e a escalada de alertas e O.S.

*   **Uso Padrão** (100 leituras, 5 threads):
    ```bash
    python scripts/stress_telemetry.py
    ```
*   **Uso Pesado** (Ex: 1000 leituras, 20 threads):
    ```bash
    python scripts/stress_telemetry.py --leituras 1000 --threads 20
    ```

---

## 🔑 Credenciais Padrão

Após executar o script de seed:

- Django Admin:
  Usuário: admin
  Senha: admin123

- Usuários normais do sistema (Gestores e Técnicos):
  Senha padrão para todos: 123

---

## 📁 Estrutura do Projeto

P.I-PlataformaManuntencaoWeb/
├── app/                      # Configurações principais do Django (settings, urls, etc.)
├── accounts/                 # Empresas, Usuários e Autenticação
├── ativos/                   # Equipamentos e Localização
├── manutencao/               # Ordens de Serviço e Histórico
├── telemetria/               # Sensores e Leituras IoT
├── alertas/                  # Sistema de Alertas automáticos
├── dashboards/               # KPIs e Dashboards executivos
├── scripts/                  # Scripts de automação (seed)
└── manage.py

### Descrição detalhada de cada pasta:

- **app/** → Contém as configurações centrais do projeto (settings.py, urls.py principais, wsgi.py, etc.)
- **accounts/** → Gerencia Empresas e Usuários (modelos, serializers, views e permissões)
- **ativos/** → Módulo responsável por Equipamentos e sua Localização física
- **manutencao/** → Ordens de Serviço (O.S.) e Histórico de Manutenções
- **telemetria/** → Sensores IoT e Leituras de telemetria em tempo real
- **alertas/** → Sistema de alertas automáticos gerados pela telemetria
- **dashboards/** → Cálculo e retorno de KPIs (MTBF, MTTR, Disponibilidade, etc.)
- **scripts/** → Scripts auxiliares como `seed_db.py` e `stress_telemetry.py`

---

## 🔗 Principais Vinculações e Regras de Cascade

| Modelo                    | Relacionado com               | Tipo de Relacionamento     | Cascade / Comportamento                              | Observação |
|---------------------------|-------------------------------|----------------------------|-----------------------------------------------------|----------|
| **Usuario**               | Empresa                       | ForeignKey                 | PROTECT (não permite excluir empresa com usuários) | Cada usuário pertence a uma empresa |
| **Equipamento**           | Empresa                       | ForeignKey                 | CASCADE (excluir empresa exclui equipamentos)      | Ativo pertence a uma empresa |
| **Equipamento**           | EquipamentoLocalizacao        | OneToOneField              | CASCADE                                             | Localização é única por equipamento |
| **Sensor**                | Equipamento                   | ForeignKey                 | CASCADE                                             | Sensor pertence a um equipamento |
| **Telemetria**            | Sensor                        | ForeignKey                 | CASCADE                                             | Leituras pertencem a um sensor |
| **Alerta**                | Equipamento                   | ForeignKey                 | CASCADE                                             | Alertas são gerados por equipamento |
| **OrdemServico**          | Equipamento                   | ForeignKey                 | PROTECT                                             | Não permite excluir equipamento com OS aberta |
| **OrdemServico**          | Usuario (responsavel)         | ForeignKey                 | SET_NULL                                            | Se o responsável for excluído, fica nulo |
| **HistoricoManutencao**   | OrdemServico                  | OneToOneField              | CASCADE                                             | Histórico é excluído junto com a OS |
| **PlanoManutencao**      | Equipamento                   | ForeignKey                 | CASCADE                                             | Planos pertencem a um equipamento |

---

## 🛡 Segurança e Controle de Acesso

A API utiliza autenticação JWT através do header:
Authorization: Bearer SEU_TOKEN_AQUI

O sistema possui isolamento completo por empresa (multi-tenant). Um usuário só consegue ver e alterar dados da empresa à qual está vinculado.

Perfis Disponíveis:
- admin → Tem acesso total ao sistema
- gestor → Pode gerenciar usuários, equipamentos e ordens da própria empresa
- tecnico → Pode visualizar dados e registrar manutenções. **Regra de Sigilo**: Técnicos só visualizam Ordens de Serviço que estão "sem responsável" ou que foram atribuídas a eles.

---

## ⚙️ Inteligência Preditiva e Automação

O sistema monitora a telemetria em tempo real e toma decisões automáticas para prevenir falhas:

### 1. Regras de Disparo de Alertas
A severidade do alerta é calculada com base no percentual atingido do `limite_alerta` configurado no sensor:
- 🟢 **Baixo**: Valor >= **70%** do limite.
- 🟡 **Médio**: Valor >= **85%** do limite.
- 🔴 **Crítico**: Valor >= **100%** do limite.

### 2. Geração Automática de O.S.
Qualquer anomalia detectada gera instantaneamente uma **Ordem de Serviço** para inspeção. A prioridade da O.S. (`baixo`, `medio`, `critico`) reflete exatamente o nível do alerta gerado.

### 3. Escalada e Agrupamento Inteligente
- **Escalada**: Se uma falha de nível "Médio" piorar para "Crítico", o sistema **eleva a prioridade** da O.S. já aberta em vez de criar uma duplicata.
- **Multifuncionalidade**: Se houver falhas de tipos diferentes (ex: Temperatura e Vibração) no mesmo motor, o sistema cria **duas O.S. distintas** para rastreamento individual.

### 4. Manutenção Preditiva por Horímetro (Tempo de Uso)
Além dos sensores que detectam anomalias, o sistema conta com um motor preditivo baseado no desgaste natural (tempo de operação), medido pelo campo `horimetro` do equipamento.

**Fluxo de Funcionamento Completo (A "Lógica de Ouro"):**

1. **Criação do Equipamento (O Ponto de Partida)**:
   - Ao cadastrar uma máquina (`POST /api/equipamentos/`), o gestor informa o horímetro atual (ex: `200` horas). 
   - Se não for informado, o sistema assume `0.0`. Isso é crucial para máquinas que já estão em operação antes da adoção do sistema.

2. **Criação dos Planos Customizados**:
   - Uma máquina pode ter *múltiplos* planos de manutenção. Em vez de definir isso no equipamento, você cria planos vinculados a ele (`POST /api/planos-manutencao/`).
   - Exemplo: "Troca de Óleo" a cada 100h e "Revisão Geral" a cada 1000h.
   - **O Segredo (Carimbo Inicial)**: No exato momento em que você cria o plano "Troca de Óleo" (intervalo 100h) para a máquina que tem 200h, o sistema grava internamente: *Última manutenção foi em 200h*. Portanto, o **próximo disparo será em 300h**.

3. **Monitoramento e Disparo Automático**:
   - Conforme a máquina trabalha, o sistema externo ou o técnico atualiza o horímetro (`PATCH /api/equipamentos/{id}/`).
   - Se o horímetro atingir ou ultrapassar 300h (ex: `PATCH` enviando `305`), o sistema intercepta essa atualização (via Signals) e **gera automaticamente uma O.S.** do tipo `preditiva`.

4. **Ciclo Contínuo e Anti-Duplicação**:
   - Após o disparo, o plano é atualizado. O novo "carimbo" passa a ser 305h. O próximo disparo será projetado para 405h.
   - O sistema possui inteligência anti-duplicação: se o horímetro continuar subindo (ex: 310h), mas a O.S. Preditiva de "Troca de Óleo" ainda estiver aberta, ele **não** criará uma nova. Ele aguarda o fechamento do ciclo atual.

---

## 📖 Documentação Interativa

Com o servidor rodando, acesse:

- Swagger UI (interface visual interativa): http://localhost:8000/api/schema/swagger-ui/
- ReDoc (documentação mais limpa): http://localhost:8000/api/schema/redoc/
- Painel Administrativo Django: http://localhost:8000/admin/

---

## 🐛 Problemas Comuns e Soluções

- O comando python não é reconhecido → Use py no lugar de python no Windows
- Ambiente virtual não ativado → Rode novamente o comando de ativação
- Porta 8000 já está em uso → Use python manage.py runserver 9000
- Erro 403 Forbidden → O usuário logado não tem permissão para realizar a ação
- Listagens retornando vazias → Verifique se o usuário está vinculado a uma empresa no painel admin

---

## 🗺 Roadmap do Projeto

### ✅ Concluído
- Criação da estrutura completa de aplicativos Django
- Implementação de todos os CRUDs necessários
- Sistema completo de autenticação JWT com Refresh e Blacklist
- Sistema de permissões RBAC por perfil e isolamento multi-tenant
- Geração automática e escalada de O.S. para todos os níveis de alerta
- Limites de alerta customizáveis individualmente por sensor
- **Manutenção Preditiva por Horímetro**: Geração automática de O.S. baseada em horas de uso
- **Classificação de O.S.**: Distinção entre ordens Corretivas (sensores), Preditivas (horímetro) e Preventivas (manuais)
- Regras de visibilidade restrita para técnicos (Sigilo de O.S.)
- Cálculo automático de KPIs no dashboard (Em testes)
- Migração oficial para PostgreSQL (Pronto para produção)
- Script de seed completo e realista
- Documentação automática com Swagger e ReDoc
- Suíte de 102 testes automatizados de integração e estresse

### 🔄 Em Desenvolvimento
- Paginação e filtros avançados em todas as listagens
- Suporte a WebSockets para telemetria em tempo real
- Preparação e deploy em ambiente de produção

---

## 🔗 Endpoints da API - Lista Completa

**Base URL:** http://localhost:8000/api/

### 🔐 Autenticação

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| POST   | /api/auth/token/                  | Realizar login e obter tokens JWT (access e refresh) |
| POST   | /api/auth/token/refresh/          | Renovar o token de acesso quando expirado |
| GET    | /api/auth/me/                     | Retornar todos os dados do usuário atualmente logado |

### 🏢 Empresas

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/empresas/                    | Listar todas as empresas |
| POST   | /api/empresas/                    | Criar nova empresa |
| GET    | /api/empresas/{id}/               | Retornar detalhes de uma empresa específica |
| PUT    | /api/empresas/{id}/               | Atualizar completamente uma empresa |
| PATCH  | /api/empresas/{id}/               | Atualizar parcialmente uma empresa |
| DELETE | /api/empresas/{id}/               | Excluir uma empresa |

### 👤 Usuários

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/usuarios/                    | Listar todos os usuários |
| POST   | /api/usuarios/                    | Criar novo usuário |
| GET    | /api/usuarios/{id}/               | Detalhes de um usuário específico |
| PUT    | /api/usuarios/{id}/               | Atualizar completamente um usuário |
| PATCH  | /api/usuarios/{id}/               | Atualizar parcialmente um usuário |
| DELETE | /api/usuarios/{id}/               | Excluir um usuário |

### ⚙️ Equipamentos

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/equipamentos/                | Listar todos os equipamentos |
| POST   | /api/equipamentos/                | Cadastrar novo equipamento |
| GET    | /api/equipamentos/{id}/           | Detalhes de um equipamento específico |
| PUT    | /api/equipamentos/{id}/           | Atualizar completamente um equipamento |
| PATCH  | /api/equipamentos/{id}/           | Atualizar parcialmente um equipamento |
| DELETE | /api/equipamentos/{id}/           | Excluir um equipamento |

### 📍 Localização

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/localizacao/                 | Listar localizações dos equipamentos |
| POST   | /api/localizacao/                 | Cadastrar localização de um equipamento |
| GET    | /api/localizacao/{id}/            | Detalhes de uma localização |
| PUT    | /api/localizacao/{id}/            | Atualizar completamente uma localização |
| PATCH  | /api/localizacao/{id}/            | Atualizar parcialmente uma localização |
| DELETE | /api/localizacao/{id}/            | Excluir uma localização |

### 🚨 Alertas

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/alertas/                     | Listar todos os alertas |
| GET    | /api/alertas/{id}/                | Detalhes de um alerta específico |
| PATCH  | /api/alertas/{id}/                | Atualizar status do alerta (ex: marcar como resolvido) |

### 🛠️ Ordens de Serviço

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/ordens-servico/              | Listar todas as ordens de serviço |
| POST   | /api/ordens-servico/              | Criar nova ordem de serviço |
| GET    | /api/ordens-servico/{id}/         | Detalhes de uma ordem específica |
| PUT    | /api/ordens-servico/{id}/         | Atualizar completamente uma ordem |
| PATCH  | /api/ordens-servico/{id}/         | Atualizar parcialmente ou status da ordem |
| DELETE | /api/ordens-servico/{id}/         | Excluir uma ordem de serviço |

### 📡 Telemetria - Sensores

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/telemetria/sensores/         | Listar todos os sensores |
| POST   | /api/telemetria/sensores/         | Cadastrar novo sensor (com limite_alerta customizado) |
| GET    | /api/telemetria/sensores/{id}/    | Detalhes de um sensor |
| PUT    | /api/telemetria/sensores/{id}/    | Atualizar completamente um sensor |
| PATCH  | /api/telemetria/sensores/{id}/    | Atualizar parcialmente um sensor |
| DELETE | /api/telemetria/sensores/{id}/    | Excluir um sensor |

### 📡 Telemetria - Leituras

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/telemetria/leituras/         | Listar todas as leituras de telemetria |
| POST   | /api/telemetria/leituras/         | Enviar nova leitura de sensor |
| GET    | /api/telemetria/leituras/{id}/    | Detalhes de uma leitura específica |

### 📅 Planos de Manutenção (Horímetro)

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/planos-manutencao/           | Listar todos os planos de manutenção preditiva |
| POST   | /api/planos-manutencao/           | Criar novo plano de manutenção por horímetro |
| GET    | /api/planos-manutencao/{id}/      | Detalhes de um plano específico |
| PATCH  | /api/planos-manutencao/{id}/      | Atualizar intervalo ou detalhes do plano |
| DELETE | /api/planos-manutencao/{id}/      | Excluir um plano de manutenção |

### 📊 Dashboards

| Método | Endpoint                          | Descrição |
|--------|-----------------------------------|---------|
| GET    | /api/dashboards/resumo/           | Retornar resumo geral e KPIs da empresa |

---
