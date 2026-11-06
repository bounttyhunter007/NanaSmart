# 📡 Documentação da API

## 📌 Visão Geral

Esta é uma **API REST** desenvolvida em Django, com autenticação JWT, operações CRUD completas, telemetria IoT e dashboards. A estrutura segue boas práticas de organização por apps (`authentication`, `accounts`, `ativos`, etc.).

**Base da API:** Todos os endpoints estão sob o prefixo `/api/`.

---

## 🔐 Autenticação (AUTH)

| Método | Endpoint                        | Descrição                                      |
|--------|----------------------------------|------------------------------------------------|
| POST   | `/api/auth/token/`              | Gerar token JWT (login)                        |
| POST   | `/api/auth/token/refresh/`      | Renovar token JWT                              |
| GET    | `/api/auth/me/`                 | Retornar dados do usuário autenticado          |
| POST   | `/api/auth/change-password/`    | Trocar a senha do próprio usuário               |

**Observações:**
- Autenticação principal via **Bearer Token (JWT)**
- Header obrigatório nos endpoints protegidos:  
  `Authorization: Bearer SEU_TOKEN`

---

## 🏢 Empresas (CRUD)

**Endpoints:**
- `GET /api/empresas/`
- `POST /api/empresas/`
- `GET /api/empresas/{id}/`
- `PUT /api/empresas/{id}/`
- `PATCH /api/empresas/{id}/`
- `DELETE /api/empresas/{id}/`

**Model:** `Empresa`

### Campos do modelo

| Campo           | Tipo              | PK / FK | Descrição                              | Observação                     |
|-----------------|-------------------|---------|----------------------------------------|--------------------------------|
| id              | Integer           | **PK**  | Identificador único                    | Auto-incrementado              |
| nome            | String(255)       | -       | Nome da empresa                        | Obrigatório                    |
| cnpj            | String(18)        | Unique  | CNPJ da empresa                        | Obrigatório e único            |
| email           | Email             | -       | E-mail institucional                   | Obrigatório                    |
| telefone        | String(20)        | -       | Telefone de contato                    | Opcional                       |
| endereco        | Text              | -       | Endereço completo                      | Opcional                       |
| data_cadastro   | DateTime          | -       | Data de cadastro                       | Auto (auto_now_add)            |

---

## 👤 Usuários (CRUD)

**Endpoints:**
- `GET /api/usuarios/`
- `POST /api/usuarios/`
- `GET /api/usuarios/{id}/`
- `PUT /api/usuarios/{id}/`
- `PATCH /api/usuarios/{id}/`
- `DELETE /api/usuarios/{id}/`

**Model:** `Usuario` (herda de `AbstractUser`)

### Campos do modelo

| Campo          | Tipo           | PK / FK             | Descrição                                      | Observação                     |
|----------------|----------------|---------------------|------------------------------------------------|--------------------------------|
| id             | Integer        | **PK**              | Identificador único                            | Auto-incrementado              |
| username       | String         | Unique              | Nome de usuário                                | Obrigatório                    |
| email          | Email          | -                   | E-mail do usuário                              | Obrigatório                    |
| first_name     | String         | -                   | Primeiro nome                                  | Opcional                       |
| last_name      | String         | -                   | Sobrenome                                      | Opcional                       |
| empresa        | Integer        | **FK** → Empresa.id | Empresa vinculada                              | Obrigatório                    |
| tipo_usuario   | String         | -                   | Tipo (admin, gestor, tecnico)                  | Obrigatório (default: tecnico) |
| cargo          | String(100)    | -                   | Cargo/função                                   | Opcional                       |
| telefone       | String(20)     | -                   | Telefone                                       | Opcional                       |

---

## ⚙️ Equipamentos (CRUD)

**Endpoints:**
- `GET /api/equipamentos/`
- `POST /api/equipamentos/`
- `GET /api/equipamentos/{id}/`
- `PUT /api/equipamentos/{id}/`
- `PATCH /api/equipamentos/{id}/`
- `DELETE /api/equipamentos/{id}/`

**Model:** `Equipamento`

### Campos do modelo

| Campo            | Tipo           | PK / FK             | Descrição                                      | Observação                     |
|------------------|----------------|---------------------|------------------------------------------------|--------------------------------|
| id               | Integer        | **PK**              | Identificador único                            | Auto-incrementado              |
| empresa          | Integer        | **FK** → Empresa.id | Empresa proprietária                           | Obrigatório                    |
| nome             | String(255)    | -                   | Nome do equipamento                            | Obrigatório                    |
| tipo             | String(100)    | -                   | Tipo (Motor, Bomba, etc.)                      | Obrigatório                    |
| fabricante       | String(100)    | -                   | Fabricante                                     | Opcional                       |
| modelo           | String(100)    | -                   | Modelo                                         | Opcional                       |
| numero_serie     | String(100)    | Unique              | Número de série                                | Obrigatório e único            |
| data_instalacao  | Date           | -                   | Data de instalação                             | Opcional                       |
| horimetro        | Float          | -                   | Horas de operação do equipamento               | Opcional (default: 0.0)        |
| status           | String         | -                   | Status (ativo, manutencao, inativo)            | Obrigatório (default: ativo)   |

---

## 📅 Planos de Manutenção (CRUD)

**Endpoints:**
- `GET /api/planos-manutencao/`
- `POST /api/planos-manutencao/`
- `GET /api/planos-manutencao/{id}/`
- `PUT /api/planos-manutencao/{id}/`
- `PATCH /api/planos-manutencao/{id}/`
- `DELETE /api/planos-manutencao/{id}/`

**Model:** `PlanoManutencao`

### Campos do modelo

| Campo                 | Tipo           | PK / FK                 | Descrição                                      | Observação                     |
|-----------------------|----------------|-------------------------|------------------------------------------------|--------------------------------|
| id                    | Integer        | **PK**                  | Identificador único                            | Auto-incrementado              |
| equipamento           | Integer        | **FK** → Equipamento.id | Equipamento vinculado                          | Obrigatório                    |
| nome_servico          | String(200)    | -                       | Nome do serviço (ex: Troca de Óleo)            | Obrigatório                    |
| descricao             | Text           | -                       | Descrição detalhada do serviço                 | Obrigatório                    |
| intervalo_horas       | Float          | -                       | A cada quantas horas a O.S. será gerada        | Obrigatório                    |
| prioridade            | String         | -                       | Prioridade ABC (A, B, C ou null)             | Herdada do equipamento na abertura   |
| ativo                 | Boolean        | -                       | Se o plano está rodando                        | Obrigatório (default: True)    |
| horimetro_ultima_os   | Float          | -                       | Horímetro do equipamento no último disparo     | Read-only (preenchido auto)    |
| proximo_disparo_horas | Float          | -                       | Quando a próxima O.S. será gerada (calculado)  | Read-only (Serializer Method)  |

---

## 📍 Localização dos Equipamentos

**Endpoints:**
- `GET /api/localizacao/`
- `POST /api/localizacao/`
- `GET /api/localizacao/{id}/`
- `PUT /api/localizacao/{id}/`
- `PATCH /api/localizacao/{id}/`
- `DELETE /api/localizacao/{id}/`

**Model:** `EquipamentoLocalizacao` (relação **OneToOne** com Equipamento)

### Campos do modelo

| Campo       | Tipo     | PK / FK                    | Descrição                        | Observação                     |
|-------------|----------|----------------------------|----------------------------------|--------------------------------|
| id          | Integer  | **PK**                     | Identificador único              | Auto-incrementado              |
| equipamento | Integer  | **FK** → Equipamento.id (OneToOne) | Equipamento                  | Obrigatório                    |
| setor       | String(100) | -                       | Setor / localização física       | Obrigatório                    |

---

## Tendências de sensores

API administrativa de demonstração: `GET/POST /api/telemetria/tendencias/demo/` e `GET/POST /api/telemetria/tendencias/demo/<uuid>/`, restrita a admin e à própria sessão. A análise também retorna `checks`, `threshold_per_hour` e `projected_breach_minutes`. Contratos, exemplos e migração: [Demonstração de tendências](DEMONSTRACAO_TENDENCIAS.md).

Revisão de UX de 06/11/2026: sensores retornam `equipamento_nome`; leituras retornam `sensor_nome`, `equipamento_nome` e `unidade_medida` (todos somente leitura). Leituras aceitam `sensor__equipamento__empresa`; tendências aceitam `empresa_id`; configurações aceitam `sensor__isnull=true`, com ordenação pela mais recente. Os filtros sempre respeitam a visibilidade do usuário. Detalhes e testes: [Telemetria e tendências](TELEMETRIA_UX.md).

Configurações: CRUD `/api/telemetria/trend-config/`. Consulta sem gravações: `GET /api/telemetria/tendencias/?sensor_id=1` ou lista com `?all=true`. A criação dos alertas e OS ocorre na ingestão ou por `python manage.py analisar_tendencias`.

`TrendConfig` inclui `ativo`, `periodo_horas`, `num_leituras` (máximo), `minimo_leituras`, `duracao_minima_minutos`, `sensibilidade`, `persistencia_minima`, `r2_minimo` e `direcao_alerta` (`crescente`, `decrescente`, `ambas`). A configuração específica prevalece sobre a global, inclusive se inativa. Somente administrador gerencia a global; o acesso aos sensores respeita a empresa e o perfil existentes.

A resposta de análise inclui `analysis_enabled`, `insufficient_data`, `data_quality`, `direction`, `is_anomalous`, `r_squared`, `persistence_ratio`, `sample_duration_minutes`, `config_used`, `readings_summary`, `projected_breach_hours`, `intervention_recommended`, `active_alert_id` e `predictive_work_order`. Toda anomalia confirmada abre uma OS preditiva de inspeção por episódio; reduções não têm projeção de limite inferior.

Defaults, validações, exemplo JSON e critérios de aceitação: [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md), revisão de 06/11/2026.

## 🚨 Histórico de alertas (somente consulta)

Especificação vigente: [Histórico de alertas](HISTORICO_ALERTAS.md). Ocorrências são geradas pelo monitoramento; problemas percebidos por pessoas são registrados diretamente em uma O.S.

- `GET /api/alertas/`: histórico paginado, com crítico → médio → baixo antes da paginação; `-data_alerta, -id` desempata dentro de cada nível. As exportações seguem essa mesma ordem.
- `GET /api/alertas/{id}/`: ocorrência e evidências preservadas.
- `POST`, `PUT`, `PATCH` e `DELETE`: `405 Method Not Allowed`, inclusive para administradores. Consultas exigem autenticação e respeitam a empresa.

Filtros compartilhados com `GET /api/exportar/alertas/{csv|excel|pdf}/`: `search`, `equipamento`, `sensor`, `origem`, `nivel`, `data_de`, `data_ate`, `equipamento__empresa` (ou `empresa`). Datas são ISO 8601, com início e fim inclusivos; a interface converte o horário local para UTC. `status` continua aceito para compatibilidade, sem controle de edição na interface.

| Campo | Significado |
| --- | --- |
| `equipamento`, `sensor`, `equipamento_nome`, `sensor_nome` | Identificação; o nome do sensor usa a evidência se o cadastro tiver sido excluído. |
| `origem` | `limite`, `tendencia` ou `manual` legado. |
| `dados_deteccao` | Contexto preservado na abertura: nomes, unidade, limite, nível e descrição iniciais, leituras e análise/configuração utilizada. Não é reescrito pelo acompanhamento. |
| `dados_analise`, `data_ultima_analise` | Último acompanhamento automático; não substituem a evidência inicial. |
| `nivel` | Maior gravidade atingida pela ocorrência, inclusive nas tendências. |
| `data_alerta`, `data_normalizacao` | Registro da ocorrência e normalização detectada; uma data desconhecida permanece nula. |
| `ordem_servico_id` | Ordem exata que atende a ocorrência, quando disponível. |
| `legado` | Informa que a abertura não possui evidência histórica preservada. |
| `status`, `evento_chave` | Controle interno do episódio e compatibilidade. Não representam uma fila de atendimento. |
| `analise_ia` | Explicação opcional; não decide a abertura nem altera as evidências. |

Limites mantêm os percentuais configurados por sensor (padrões 70/85/100). Duas novas leituras normais consecutivas confirmam recuperação. Tendências mantêm os critérios próprios. Cada episódio mantém uma ocorrência; recorrências de limite podem compartilhar uma O.S. ainda aberta do mesmo sensor. Recuperação não conclui a ordem, e conclusão/cancelamento não recria trabalho no mesmo episódio.


## 🛠️ Ordens de Serviço (CRUD)

**Endpoints:**
- `GET /api/ordens-servico/`
- `POST /api/ordens-servico/`
- `GET /api/ordens-servico/{id}/`
- `PUT /api/ordens-servico/{id}/`
- `PATCH /api/ordens-servico/{id}/`
- `DELETE /api/ordens-servico/{id}/`

**Model:** `OrdemServico`

`alerta_origem` e `sensor_origem` são campos controlados pelo backend no CRUD. A origem inicial permanece preservada; várias ocorrências podem apontar para a mesma ordem aberta via `Alerta.ordem_servico`. Concluir/cancelar uma ordem não resolve alertas, e recuperar uma leitura não encerra a ordem. Concluída e cancelada são estados terminais quanto ao status. A conclusão registra data e um único histórico.

### Campos do modelo

| Campo           | Tipo     | PK / FK                  | Descrição                                      | Observação                          |
|-----------------|----------|--------------------------|------------------------------------------------|-------------------------------------|
| id              | Integer  | **PK**                   | Identificador único                            | Auto-incrementado                   |
| equipamento     | Integer  | **FK** → Equipamento.id  | Equipamento                                    | Obrigatório                         |
| responsavel     | Integer  | **FK** → Usuario.id      | Responsável técnico/gestor                     | Opcional (SET_NULL)                 |
| titulo          | String(200) | -                     | Título da OS                                   | Obrigatório                         |
| descricao       | Text     | -                        | Descrição do problema/serviço                  | Obrigatório                         |
| tipo_os         | String   | -                        | Tipo (corretiva, preditiva, preventiva)        | Obrigatório (default: preventiva)   |
| status          | String   | -                        | Status (pendente, andamento, concluida, cancelada) | Obrigatório (default: pendente) |
| prioridade      | String   | -                        | Prioridade legada do plano, somente leitura       | Não determina a prioridade de novas OS        |
| data_abertura   | DateTime | -                        | Data de abertura                               | Auto (timezone.now)                 |
| data_conclusao  | DateTime | -                        | Data de conclusão                              | Preenchido automaticamente         |

---

## 📜 Histórico de Manutenção (CRUD)

**Endpoints:**
- `GET /api/historico/`
- `POST /api/historico/`
- `GET /api/historico/{id}/`
- `PUT /api/historico/{id}/`
- `PATCH /api/historico/{id}/`
- `DELETE /api/historico/{id}/`

**Model:** `HistoricoManutencao` (relação **OneToOne** com OrdemServico)

### Campos do modelo

| Campo               | Tipo            | PK / FK                     | Descrição                            | Observação                     |
|---------------------|-----------------|-----------------------------|--------------------------------------|--------------------------------|
| id                  | Integer         | **PK**                      | Identificador único                  | Auto-incrementado              |
| ordem_servico       | Integer         | **FK** → OrdemServico.id (OneToOne) | OS relacionada               | Obrigatório                    |
| descricao_servico   | Text            | -                           | Serviços realizados                  | Obrigatório                    |
| data_execucao       | Date            | -                           | Data da execução                     | Obrigatório                    |
| custo_pecas         | Decimal(10,2)   | -                           | Custo das peças                      | Default 0.00                   |
| custo_mao_de_obra  | Decimal(10,2)   | -                           | Custo da mão de obra                 | Default 0.00                   |
| custo_total         | Decimal         | -                           | Soma dos custos (property)           | Calculado automaticamente      |

---

## 📡 Telemetria (IoT)

### Sensores (CRUD)

**Endpoints:**
- `GET /api/telemetria/sensores/`
- `POST /api/telemetria/sensores/`
- `GET /api/telemetria/sensores/{id}/`
- `PUT /api/telemetria/sensores/{id}/`
- `PATCH /api/telemetria/sensores/{id}/`
- `DELETE /api/telemetria/sensores/{id}/`

**Model:** `Sensor`

### Campos do modelo

| Campo          | Tipo        | PK / FK               | Descrição                                      | Observação                     |
|----------------|-------------|-----------------------|------------------------------------------------|--------------------------------|
| id             | Integer     | **PK**                | Identificador único                            | Auto-incrementado              |
| equipamento    | Integer     | **FK** → Equipamento.id | Equipamento vinculado                        | Obrigatório                    |
| tipo_sensor    | String      | -                     | Tipo de sensor                                 | Obrigatório (choices)          |
| unidade_medida | String(20)  | -                     | Unidade (°C, mm/s, bar, A, etc.)               | Obrigatório                    |
| descricao      | Text        | -                     | Descrição adicional                            | Opcional                       |
| ativo          | Boolean     | -                     | Sensor está ativo?                             | Default: True                  |

### Leituras / Telemetria (CRUD)

**Endpoints:**
- `GET /api/telemetria/leituras/`
- `POST /api/telemetria/leituras/`
- `GET /api/telemetria/leituras/{id}/`
- `PUT /api/telemetria/leituras/{id}/`
- `PATCH /api/telemetria/leituras/{id}/`
- `DELETE /api/telemetria/leituras/{id}/`

**Model:** `Telemetria`

### Campos do modelo

| Campo     | Tipo      | PK / FK           | Descrição                        | Observação                     |
|-----------|-----------|-------------------|----------------------------------|--------------------------------|
| id        | Integer   | **PK**            | Identificador único              | Auto-incrementado              |
| sensor    | Integer   | **FK** → Sensor.id| Sensor que gerou a leitura       | Obrigatório                    |
| valor     | Float     | -                 | Valor medido                     | Obrigatório                    |
| data_hora | DateTime  | -                 | Data e hora da leitura           | Auto (auto_now_add)            |

---

## 📊 Dashboards (Somente leitura)

**Endpoints:**
- `GET /api/dashboards/kpis/`
- `GET /api/dashboards/resumo/`

**Função:** Retornar indicadores consolidados (KPIs, quantidade de alertas, equipamentos por status, etc.).

### Endpoints Detalhados

#### 1. Resumo Completo (`/api/dashboards/resumo/`)
Retorna uma visão geral da empresa:
- **resumo_status**: Total de equipamentos por status (ativo, manutencao, inativo).
- **kpis_globais**: 
    - `mttr_medio`: Tempo Médio de Reparo (horas).
    - `mtbf_medio`: Tempo Médio Entre Falhas (horas).
    - `disponibilidade_media`: Percentual de uptime (calculado apenas sobre ativos com histórico).
    - `custo_total_manutencao`: Soma de todos os custos de peças e mão de obra.
- **alertas_24h**: Novas ocorrências das últimas 24 horas por nível e total, inclusive normalizadas.
- **alertas_recentes**: Até seis ocorrências mais recentes dessa janela, em ordem cronológica decrescente.
- **alertas_ativos**: Campo mantido para compatibilidade, com o significado anterior de episódios ainda ativos.
- **os_abertas**: Quantidade de OS pendentes ou em andamento.
- **detalhes_equipamentos**: Lista de todos os equipamentos com seus KPIs individuais.

**Filtros:**
- `?dias=X`: Limita os cálculos de KPIs e custos aos últimos X dias.
- `?empresa_id=X`: (Admin apenas) Filtra por empresa específica.

#### 2. KPIs Individuais (`/api/dashboards/kpis/`)
Retorna uma lista de KPIs focada em cada equipamento.
- **Filtros:** `?equipamento_id=X`, `?dias=X`.

---

## 🤖 Inteligência Artificial (Gemini API)

**Endpoints:**
- `POST /api/gemini/chat/`

**Função:** Prover uma interface conversacional e de inteligência artificial generativa com suporte a regras de negócio e controle de acesso estrito (RBAC).

### Detalhes da Integração

A integração utiliza a biblioteca `google-generativeai` e exige a chave de API configurada no arquivo `.env` através da variável `GEMINI_API_KEY`. O modelo selecionado garante respostas precisas e rápidas para o tipo de prompt.

O prompt base enviado para o Google Gemini é dinamicamente alterado dependendo do `tipo_usuario` extraído do Token JWT:
- **Admin:** Recebe o contexto completo e acesso a respostas globais sobre o estado da aplicação.
- **Gestor:** Recebe apenas os relatórios, alertas e O.S. da sua própria empresa. A IA é instruída a manter a privacidade (Multi-tenant).
- **Técnico:** Recebe um contexto limitado a nível de execução. A IA atua como um conselheiro técnico focado em ajudar na resolução de problemas de O.S. e alertas locais de onde ele opera, e omite expressamente dados gerenciais se questionada.

---

## 🛡️ Permissões e Segurança (RBAC)

O sistema utiliza **Role-Based Access Control** para garantir a segurança dos dados:

| Papel | Permissões |
|-------|------------|
| **Admin** | Acesso total a todas as empresas, usuários e ativos. |
| **Gestor** | Acesso total, mas restrito aos dados da **própria empresa** (Multi-tenant). |
| **Técnico**| Pode visualizar e criar ativos/OS, mas é **bloqueado para DELETE** em registros críticos (Alertas, Telemetria, OS). |

**Regra Restritiva:** Técnicos recebem `403 Forbidden` ao tentar deletar qualquer registro de manutenção ou sensor.

---

## 🔗 Principais Relacionamentos

- **Empresa** → **Equipamento** → **Sensor** → **Telemetria**
- **Equipamento** → **Alerta**
- **Equipamento** → **PlanoManutencao**
- **Equipamento** → **OrdemServico** → **HistoricoManutencao** (OneToOne)
- **Equipamento** → **EquipamentoLocalizacao** (OneToOne)
- **Usuario** → **OrdemServico** (responsavel)

---

## 🎯 Resumo

A API possui uma estrutura completa e bem normalizada para **gestão de ativos industriais**, com forte foco em manutenção preditiva e corretiva, monitoramento IoT em tempo real e controle de custos. Todos os relacionamentos importantes estão mapeados via ForeignKey e OneToOneField, com regras claras de cascade e campos calculados.

---


## Priorização ABC (06/11/2026)

Equipamentos e OS usam A/B/C ou `null` (Não avaliada / A definir). Novas OS herdam a classe na abertura; reclassificação de equipamento e agravamento de alerta não recalculam ordens abertas. Ajustar ou restaurar exige ação específica de gestor/admin e justificativa. Enviar `prioridade` no formulário geral da OS retorna 400.

| Método | Endpoint | Comportamento |
|---|---|---|
| GET | `/api/criterios-criticidade/atual/?empresa=ID` | Guia vigente ou sugestão ainda não validada |
| GET/POST | `/api/criterios-criticidade/` | Consultar revisões / publicar nova revisão validada |
| GET | `/api/historico-criticidade/?equipamento=ID` | Histórico do equipamento no escopo permitido |
| POST | `/api/ordens-servico/ID/ajustar_prioridade/` | Ajustar A/B/C com justificativa |
| POST | `/api/ordens-servico/ID/restaurar_prioridade/` | Restaurar herança conhecida com justificativa |
| GET | `/api/ordens-servico/ID/historico_prioridade/` | Histórico paginado da prioridade |

A listagem e a exportação de OS compartilham filtros e ordenação antes da paginação. Use `prioridade=a_definir` para localizar pendências. Consulte os contratos, exemplos e conversões em [Priorização ABC](PRIORIZACAO_ABC.md).
