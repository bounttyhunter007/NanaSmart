# 📘 Manual Mestre: Especificação Técnica e Funcional da API (Master Edition)

Este manual é o coração doutrinário do seu projeto. Ele não apenas lista endpoints, mas explica a **filosofia da arquitetura**, a **mecânica do banco de dados** e os **protocolos de comunicação** entre os serviços.

---

## 🏗️ 1. Filosofia de Arquitetura: Por que é assim?
Nosso sistema utiliza uma **Arquitetura Baseada em Domínios**. Cada "App" Django (accounts, ativos, telemetria, alertas, manutencao, dashboards) funciona como um microserviço dentro de um monólito. Isso permite que a lógica de "Sensor" não se misture com a lógica de "Financeiro/Custos".

### O Fluxo de Comunicação:
A comunicação entre apps acontece de duas formas:
1.  **Síncrona (Foreign Keys)**: Quando um dado precisa do outro para existir (ex: Uma Telemetria **precisa** de um Sensor).
2.  **Assíncrona/Reativa (Signals)**: Quando uma ação em um app deve disparar algo em outro sem que eles estejam "grudados" (ex: Uma Telemetria dispara um Alerta). 

---

## 👥 2. App `accounts` (Segurança e Contexto de Negócio)
Este app define **quem** está usando o sistema. No ambiente industrial, as ações devem ter "Dono" para auditoria técnica.

- **Fluxo de Dados**:
  1. Cadastro de `Empresa`: Define o "container" de dados.
  2. Cadastro de `Usuario`: Vincula pessoas a esse container de empresa.
- **Lógica Profunda**: Ao usar o `AbstractUser`, garantimos que o Django use nossa tabela customizada para autenticação. No Passo 5, isso será vital para o **JWT (JSON Web Token)**.
- **Regras do Banco (Constraints)**:
  - `unique=True` em `username` e `email`.
  - `on_delete=models.CASCADE` na Empresa: Se a empresa sair do sistema, seus usuários perdem o acesso automaticamente por segurança.

### 🛠️ Manual de API `accounts`:
| Funcionalidade | Método | URL | Body JSON | Retorno |
|---|---|---|---|---|
| **Lista Empresas** | `GET` | `/api/empresas/` | — | `[{"id": 1, "nome": "Planta A"}]` |
| **Cria Usuário** | `POST` | `/api/usuarios/` | `{"username": "jpedro", "tipo_usuario": "tecnico"}` | Novo usuário com ID |

---

## 📦 3. App `ativos` (O Inventário Industrial)
Sem Ativos, o sistema é vazio. Ativos são a âncora de todo o histórico da planta.

- **Fluxo de Dados**:
  1. Criação de `Equipamento` (Máquina).
  2. Definição de `Localizacao` (Setor industrial).
- **Lógica Profunda**: O modelo `Equipamento` possui um `status`. Esse status é um **Enumarado (`ChoiceField`)**. Isso impede que o front-end envie status que não existem, garantindo integridade total dos dados.
- **Regras do Banco (Constraints)**:
  - `numero_serie` é o identificador único físico (Indexado no banco para buscas rápidas).
  - `OneToOneField` em localização garante que um Setor industrial seja exclusivo de uma única máquina.

### 🛠️ Manual de API `ativos`:
| Funcionalidade | Método | URL | Body (Exemplo) | Dica de Uso |
|---|---|---|---|---|
| **Listar Ativos** | `GET` | `/api/equipamentos/` | — | Use `?status=ativo` para filtrar |
| **Mudar Local** | `POST` | `/api/localizacao/` | `{"equipamento": 5, "setor": "Linha 02"}` | Para quando o ativo é móvel |

---

## 📡 4. App `telemetria` (O Sistema Nervoso / IoT)
Onde o mundo físico das máquinas toca o mundo digital da API.

- **Fluxo de Dados**: Ingestão de bit -> Validação DRF -> Persistência de Banco -> Gatilho de Alerta.
- **Lógica Profunda (Performance)**: O `TelemetriaSerializer` é projetado para ser "lean". Ele valida o `valor` (float) e se o `sensor_id` existe antes de sequer tentar gravar, economizando ciclos de CPU em alta carga.
- **Regras do Banco (Constraints)**:
  - Índices em `data_leitura`: Essencial para que o Chart.js possa carregar um histórico de 30 dias em milissegundos.

### 🛠️ Manual de API `telemetria`:
| Funcionalidade | Método | URL | Body (Exemplo) | Retorno |
|---|---|---|---|---|
| **Enviar Leitura** | `POST` | `/api/telemetria/leituras/` | `{"sensor": 10, "valor": 95.2}` | `201 Created` |
| **Puxar Histórico**| `GET` | `/api/telemetria/leituras/` | — | Use `?ordering=-data_leitura` |

---

## 🚨 5. App `alertas` (A Inteligência Reativa / Engine)
Este app é o "Juiz" que decide se a máquina está em perigo.

- **Mecânica do Signal**: No arquivo `apps.py`, carregamos o módulo de `signals`.
- **A Lógica Interna**:
  - `post_save`: O gatilho que avisa que a Telemetria foi salva.
  - `created`: Garante que só disparemos o alerta em novos dados (New Input Only).
  - Alerta é gerado com `severidade='critico'` se valor > limite.
- **Regras do Banco**: O modelo `Alerta` possui o campo `resolvido_em`. Se estiver nulo, o sinalizador no Vue brilhará em vermelho.

### 🛠️ Manual de API `alertas`:
| Funcionalidade | Método | URL | Retorno | Quando usar? |
|---|---|---|---|---|
| **Listar Alertas** | `GET` | `/api/alertas/` | `[{"descricao": "Crítico", ...}]` | Na home do Técnico |
| **Resolver Alerta** | `PATCH` | `/api/alertas/{id}/` | `{ "status": "resolvido" }` | Logo após abrir a OS |

---

## 🔧 6. App `manutencao` (O Fluxo de Gestão Humana)
Onde o problema técnico vira solução técnica com histórico.

- **Fluxo de Estados (Workflow Industrial)**:
  `Aberta` (Pending) -> `Em Andamento` (Working) -> `Concluída` (Solucionado).
- **Lógica Profunda**: Ao concluir uma OS, o campo `data_conclusao` é preenchido via `timezone.now()`, fixando o marco final do reparo.
- **Auditoria**: O `HistoricoManutencao` guarda `custo_pecas` e `custo_maao_de_obra` via `DecimalField`, o único tipo de dado seguro para cálculos financeiros no Django.

### 🛠️ Manual de API `manutencao`:
| Funcionalidade | Método | URL | Body (Exemplo) | Dica |
|---|---|---|---|---|
| **Criar OS** | `POST` | `/api/ordens-servico/` | `{"titulo": "Motor Superaquecido"}` | Pode vincular a um Alerta |
| **Finalizar OS** | `PATCH` | `/api/ordens-servico/{id}/` | `{"status": "concluida"}` | Passo crucial para os KPIs |
| **Registrar Custo**| `POST` | `/api/manutencao/historico/`| `{"custo_pecas": 500.00}` | Alimenta o Dash Financeiro |

---

## 📊 7. App `dashboards` (Visão Estratégica / BI)
Transforma a "bagunça" das tabelas em indicadores de performance (KPIs).

- **Matemática do MTTR (Média de Tempo de Reparo)**:
  O Banco faz: `Média(Data_Conclusão - Data_Abertura)`. Se for baixo, sua equipe é eficiente. Se for alto, faltam ferramentas.
- **Matemática do MTBF (Média entre Falhas)**:
  O código mede o tempo de "céu limpo" (sem quebra). Quanto maior o MTBF, maior a Confiabilidade da sua planta.
- **Lógica de Performance**: A view processa os números sob demanda (`On-the-fly`), sem salvar lixo no banco.

### 🛠️ Manual de API `dashboards`:
| Funcionalidade | Método | URL | Retorno |
|---|---|---|---|
| **Ver KPIs** | `GET` | `/api/dashboards/kpis/` | `[{"mttr_hours": 2.5, "mtbf_hours": 120, ...}]` |

---

## 🧬 Conclusão do Ciclo de Vida:
O dado nasce no sensor (Telemetria), vira um sinal de alerta (Alertas), vira uma tarefa humana (Manutenção), termina como um custo de reparo (Histórico) e, por fim, vira inteligência de decisão (Dashboard).


