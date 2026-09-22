# Documentação do Banco de Dados - BugHunter AV

Este documento descreve a estrutura técnica do banco de dados (PostgreSQL) utilizado na plataforma de manutenção industrial.

## Visão Geral
O sistema utiliza uma arquitetura relacional focada em hierarquia industrial: **Empresa > Usuários/Ativos > Telemetria/Manutenção**.

---

## 1. App: Accounts (Gestão de Identidade)

### Tabela: `accounts_empresa`
Representa as unidades industriais clientes.
- `id`: Primary Key (BigInt)
- `nome`: Char(255)
- `cnpj`: Char(18) - **Unique**
- `email`: EmailField
- `telefone`: Char(20)
- `endereco`: TextField
- `data_cadastro`: DateTime

### Tabela: `accounts_usuario`
Usuário customizado (herda de AbstractUser).
- `id`: Primary Key (BigInt)
- `username`: Char(150) - **Unique**
- `email`: EmailField
- `password`: Char(128)
- `tipo_usuario`: Enum ('admin', 'gestor', 'tecnico')
- `cargo`: Char(100)
- `telefone`: Char(20)
- `empresa_id`: **Foreign Key** -> `accounts_empresa` (1:N)
- `is_staff`, `is_active`, `date_joined`: Campos padrão Django.

### Tabelas Muito para Muitos (N:N)
O modelo `Usuario` utiliza as tabelas auxiliares abaixo para gerenciar permissões e grupos:
- `accounts_usuario_groups`: Liga Usuários a Grupos de acesso.
- `accounts_usuario_user_permissions`: Liga Usuários a Permissões específicas.

---

## 2. App: Ativos (Gestão de Equipamentos)

### Tabela: `ativos_equipamento`
- `id`: Primary Key (BigInt)
- `empresa_id`: **Foreign Key** -> `accounts_empresa` (1:N)
- `nome`: Char(255)
- `tipo`: Char(100)
- `fabricante`: Char(100)
- `modelo`: Char(100)
- `numero_serie`: Char(100) - **Unique**
- `data_instalacao`: Date
- `horimetro`: Float (Total de horas trabalhadas)
- `status`: Enum ('ativo', 'manutencao', 'inativo')

### Tabela: `ativos_equipamentolocalizacao`
- `id`: Primary Key (BigInt)
- `equipamento_id`: **OneToOne** -> `ativos_equipamento` (1:1)
- `setor`: Char(100)

### Tabela: `ativos_planomanutencao`
Regras de manutenção preventiva baseada em horímetro.
- `id`: Primary Key (BigInt)
- `equipamento_id`: **Foreign Key** -> `ativos_equipamento` (1:N)
- `nome_servico`: Char(200)
- `descricao`: TextField
- `intervalo_horas`: Float (Ex: a cada 500h)
- `prioridade`: Enum ('baixo', 'medio', 'critico')
- `ativo`: Boolean
- `horimetro_ultima_os`: Float (Controla o próximo disparo)

---

## 3. App: Telemetria (Dados de Sensores)

### Tabela: `telemetria_sensor`
- `id`: Primary Key (BigInt)
- `equipamento_id`: **Foreign Key** -> `ativos_equipamento` (1:N)
- `tipo_sensor`: Enum ('temperatura', 'vibracao', 'pressao', 'corrente', 'umidade')
- `unidade_medida`: Char(20)
- `limite_alerta`: Float (Dispara alerta se ultrapassado)
- `ativo`: Boolean

### Tabela: `telemetria_telemetria`
Histórico massivo de leituras.
- `id`: Primary Key (BigInt)
- `sensor_id`: **Foreign Key** -> `telemetria_sensor` (1:N)
- `valor`: Float
- `data_hora`: DateTime (Auto)

---

## 4. App: Manutenção (Operação e Custos)

### Tabela: `manutencao_ordemservico`
- `id`: Primary Key (BigInt)
- `equipamento_id`: **Foreign Key** -> `ativos_equipamento` (1:N)
- `responsavel_id`: **Foreign Key** -> `accounts_usuario` (1:N)
- `tipo_os`: Enum ('corretiva', 'preditiva', 'preventiva')
- `titulo`: Char(200)
- `descricao`: TextField
- `status`: Enum ('pendente', 'andamento', 'concluida', 'cancelada')
- `prioridade`: Enum ('baixo', 'medio', 'critico')
- `data_abertura`: DateTime
- `data_conclusao`: DateTime

### Tabela: `manutencao_historicomanutencao`
Fechamento financeiro e técnico da OS.
- `id`: Primary Key (BigInt)
- `ordem_servico_id`: **OneToOne** -> `manutencao_ordemservico` (1:1)
- `descricao_servico`: TextField
- `data_execucao`: Date
- `custo_pecas`: Decimal(10,2)
- `custo_mao_de_obra`: Decimal(10,2)

---

## 5. App: Alertas (Eventos do Sistema)

### Tabela: `alertas_alerta`
- `id`: Primary Key (BigInt)
- `equipamento_id`: **Foreign Key** -> `ativos_equipamento` (1:N)
- `tipo_alerta`: Char(100)
- `nivel`: Enum ('baixo', 'medio', 'critico')
- `status`: Enum ('ativo', 'resolvido', 'ignorado')
- `descricao`: TextField
- `data_alerta`: DateTime (Auto)

---

## Resumo de Relacionamentos (ER)

| De (Tabela) | Para (Tabela) | Tipo | Cardinalidade |
| :--- | :--- | :--- | :--- |
| `accounts_usuario` | `accounts_empresa` | FK | N:1 |
| `ativos_equipamento` | `accounts_empresa` | FK | N:1 |
| `ativos_equipamentolocalizacao` | `ativos_equipamento` | OneToOne | 1:1 |
| `ativos_planomanutencao` | `ativos_equipamento` | FK | N:1 |
| `telemetria_sensor` | `ativos_equipamento` | FK | N:1 |
| `telemetria_telemetria` | `telemetria_sensor` | FK | N:1 |
| `manutencao_ordemservico` | `ativos_equipamento` | FK | N:1 |
| `manutencao_ordemservico` | `accounts_usuario` | FK | N:1 |
| `manutencao_historicomanutencao` | `manutencao_ordemservico` | OneToOne | 1:1 |
| `alertas_alerta` | `ativos_equipamento` | FK | N:1 |
| `accounts_usuario` | `auth_group` | N:N | N:N (via table `groups`) |
| `accounts_usuario` | `auth_permission` | N:N | N:N (via table `user_permissions`) |

---
**Nota:** As tabelas `django_*` e `auth_*` são tabelas de sistema do framework Django e não foram detalhadas aqui por serem padrão de mercado.
