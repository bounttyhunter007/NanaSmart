# 📡 Documentação da API

## 📌 Visão Geral

Esta é uma **API REST** desenvolvida em Django, com autenticação JWT, operações CRUD completas, telemetria IoT e dashboards. A estrutura segue boas práticas de organização por apps (`accounts`, `ativos`, etc.).

**Base da API:** Todos os endpoints estão sob o prefixo `/api/`.

---

## 🔐 Autenticação (AUTH)

| Método | Endpoint                        | Descrição                                      |
|--------|----------------------------------|------------------------------------------------|
| POST   | `/api/auth/token/`              | Gerar token JWT (login)                        |
| POST   | `/api/auth/token/refresh/`      | Renovar token JWT                              |
| GET    | `/api/auth/me/`                 | Retornar dados do usuário autenticado          |

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
| status           | String         | -                   | Status (ativo, manutencao, inativo)            | Obrigatório (default: ativo)   |

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

## 🚨 Alertas (CRUD)

**Endpoints:**
- `GET /api/alertas/`
- `POST /api/alertas/`
- `GET /api/alertas/{id}/`
- `PUT /api/alertas/{id}/`
- `PATCH /api/alertas/{id}/`
- `DELETE /api/alertas/{id}/`

**Model:** `Alerta`

### Campos do modelo

| Campo        | Tipo        | PK / FK               | Descrição                                      | Observação                     |
|--------------|-------------|-----------------------|------------------------------------------------|--------------------------------|
| id           | Integer     | **PK**                | Identificador único                            | Auto-incrementado              |
| equipamento  | Integer     | **FK** → Equipamento.id | Equipamento relacionado                      | Obrigatório                    |
| tipo_alerta  | String(100) | -                     | Tipo do alerta                                 | Obrigatório                    |
| nivel        | String      | -                     | Nível (baixo, medio, critico)                  | Obrigatório (default: baixo)   |
| descricao    | Text        | -                     | Descrição do alerta                            | Obrigatório                    |
| data_alerta  | DateTime    | -                     | Data e hora do alerta                          | Auto (auto_now_add)            |
| status       | String      | -                     | Status (ativo, resolvido, ignorado)            | Obrigatório (default: ativo)   |

---

## 🛠️ Ordens de Serviço (CRUD)

**Endpoints:**
- `GET /api/ordens-servico/`
- `POST /api/ordens-servico/`
- `GET /api/ordens-servico/{id}/`
- `PUT /api/ordens-servico/{id}/`
- `PATCH /api/ordens-servico/{id}/`
- `DELETE /api/ordens-servico/{id}/`

**Model:** `OrdemServico`

### Campos do modelo

| Campo           | Tipo     | PK / FK                  | Descrição                                      | Observação                          |
|-----------------|----------|--------------------------|------------------------------------------------|-------------------------------------|
| id              | Integer  | **PK**                   | Identificador único                            | Auto-incrementado                   |
| equipamento     | Integer  | **FK** → Equipamento.id  | Equipamento                                    | Obrigatório                         |
| responsavel     | Integer  | **FK** → Usuario.id      | Responsável técnico/gestor                     | Opcional (SET_NULL)                 |
| titulo          | String(200) | -                     | Título da OS                                   | Obrigatório                         |
| descricao       | Text     | -                        | Descrição do problema/serviço                  | Obrigatório                         |
| status          | String   | -                        | Status (pendente, andamento, concluida, cancelada) | Obrigatório (default: pendente) |
| prioridade      | String   | -                        | Prioridade (baixa, media, alta, urgente)       | Obrigatório (default: media)        |
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

---

## 🔗 Principais Relacionamentos

- **Empresa** → **Equipamento** → **Sensor** → **Telemetria**
- **Equipamento** → **Alerta**
- **Equipamento** → **OrdemServico** → **HistoricoManutencao** (OneToOne)
- **Equipamento** → **EquipamentoLocalizacao** (OneToOne)
- **Usuario** → **OrdemServico** (responsavel)

---

## 🎯 Resumo

A API possui uma estrutura completa e bem normalizada para **gestão de ativos industriais**, com forte foco em manutenção preditiva e corretiva, monitoramento IoT em tempo real e controle de custos. Todos os relacionamentos importantes estão mapeados via ForeignKey e OneToOneField, com regras claras de cascade e campos calculados.

---