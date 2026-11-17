# Banco de dados do NanaSmart

**Revisão:** 17/11/2026. Inventário obtido das classes de modelo registradas pelo Django no código local, sem consultar registros nem modificar bancos. PostgreSQL é o banco de desenvolvimento configurado; os testes desta revisão usaram SQLite em memória.

## Como entender os relacionamentos

Uma empresa possui usuários e equipamentos. Equipamentos possuem sensores, planos e ordens; cada sensor possui leituras. Alertas guardam ocorrências e evidências, e podem apontar para a OS que atende o episódio. Uma OS pode atender várias ocorrências, mas tem no máximo um histórico de manutenção.

`FK` liga vários registros a um registro de outra tabela. `OneToOne` permite no máximo um registro relacionado por origem. `null` indica se o banco admite ausência de valor; isso não determina sozinho se um campo pode ser omitido ou alterado na API. Os serializers e permissões definem o contrato de escrita.

## Regras que não podem ser inferidas só pelos campos

- Equipamento e OS usam classes A/B/C. A OS copia o contexto da criticidade na abertura; ajustes posteriores precisam de ação explícita e justificativa. Veja [Priorização ABC](PRIORIZACAO_ABC.md).
- `OrdemServico.alerta_origem` preserva a ocorrência inicial. `Alerta.ordem_servico` associa cada ocorrência à ordem que a atende, inclusive recorrências. Não são relacionamentos intercambiáveis.
- Concluir uma OS registra a conclusão e garante um histórico; normalizar um sensor não conclui manutenção. Veja [Histórico de alertas e compatibilidade](HISTORICO_ALERTAS.md#atualização-do-banco-e-compatibilidade).
- `Sensor.tipo` e `Telemetria.timestamp` são os nomes atuais. A prioridade legada de `PlanoManutencao` ainda existe no modelo, mas é somente leitura na API e não determina a prioridade ABC de novas ordens.
- `dados_deteccao`, `historico_niveis`, `data_normalizacao` e `evidencia_preditiva` preservam aspectos diferentes da ocorrência e da abertura. Não se deve transformar o último valor conhecido em uma evidência inicial inventada.
- `on_delete` descreve o comportamento da relação no modelo. A API pode aplicar restrições adicionais, como impedir exclusão de equipamento com histórico de alertas.

## Inventário dos modelos

Os campos abaixo usam seus nomes no modelo; relações também têm uma coluna física com sufixo `_id`. Os campos herdados de `AbstractUser` estão incluídos. As tabelas internas dos pacotes Django não foram enumeradas como modelos próprios do NanaSmart.

| Modelo | Tabela | Arquivo fonte |
|---|---|---|
| `accounts.Empresa` | `accounts_empresa` | [accounts/models.py](../accounts/models.py) |
| `accounts.Usuario` | `accounts_usuario` | [accounts/models.py](../accounts/models.py) |
| `ativos.CriteriosCriticidade` | `ativos_criterioscriticidade` | [ativos/models.py](../ativos/models.py) |
| `ativos.TipoEquipamento` | `ativos_tipoequipamento` | [ativos/models.py](../ativos/models.py) |
| `ativos.Equipamento` | `ativos_equipamento` | [ativos/models.py](../ativos/models.py) |
| `ativos.HistoricoCriticidadeEquipamento` | `ativos_historicocriticidadeequipamento` | [ativos/models.py](../ativos/models.py) |
| `ativos.EquipamentoLocalizacao` | `ativos_equipamentolocalizacao` | [ativos/models.py](../ativos/models.py) |
| `ativos.PlanoManutencao` | `ativos_planomanutencao` | [ativos/models.py](../ativos/models.py) |
| `telemetria.Sensor` | `telemetria_sensor` | [telemetria/models.py](../telemetria/models.py) |
| `telemetria.Telemetria` | `telemetria_telemetria` | [telemetria/models.py](../telemetria/models.py) |
| `telemetria.TrendConfig` | `telemetria_trendconfig` | [telemetria/models.py](../telemetria/models.py) |
| `telemetria.TrendDemo` | `telemetria_trenddemo` | [telemetria/models.py](../telemetria/models.py) |
| `alertas.Alerta` | `alertas_alerta` | [alertas/models.py](../alertas/models.py) |
| `manutencao.OrdemServico` | `manutencao_ordemservico` | [manutencao/models.py](../manutencao/models.py) |
| `manutencao.HistoricoPrioridadeOS` | `manutencao_historicoprioridadeos` | [manutencao/models.py](../manutencao/models.py) |
| `manutencao.HistoricoManutencao` | `manutencao_historicomanutencao` | [manutencao/models.py](../manutencao/models.py) |
| `gemini_api.PromptAnaliseOS` | `gemini_api_promptanaliseos` | [gemini_api/models.py](../gemini_api/models.py) |
| `gemini_api.PromptConfig` | `gemini_api_promptconfig` | [gemini_api/models.py](../gemini_api/models.py) |

### accounts.Empresa

Tabela: `accounts_empresa`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `nome` | CharField(255) | não | — |
| `cnpj` | CharField(18) | não | único |
| `email` | CharField(254) | não | — |
| `telefone` | CharField(20) | sim | — |
| `cidade` | CharField(100) | sim | — |
| `estado` | CharField(50) | sim | — |
| `endereco` | TextField | sim | — |
| `data_cadastro` | DateTimeField | não | horário/data da criação; não editável no modelo |

### accounts.Usuario

Tabela: `accounts_usuario`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `password` | CharField(128) | não | — |
| `last_login` | DateTimeField | sim | — |
| `is_superuser` | BooleanField | não | — |
| `username` | CharField(150) | não | único |
| `first_name` | CharField(150) | não | — |
| `last_name` | CharField(150) | não | — |
| `email` | CharField(254) | não | — |
| `is_staff` | BooleanField | não | — |
| `is_active` | BooleanField | não | — |
| `date_joined` | DateTimeField | não | — |
| `empresa` | FK → accounts.Empresa | sim | coluna empresa_id; on_delete=CASCADE |
| `tipo_usuario` | CharField(20) | não | valores: admin, gestor, tecnico, operador; padrão: operador |
| `cargo` | CharField(100) | sim | — |
| `telefone` | CharField(20) | sim | — |
| `foto_perfil` | FileField(100) | sim | — |

Relação N:N `groups` → `auth.Group`, pela tabela `accounts_usuario_groups`.

Relação N:N `user_permissions` → `auth.Permission`, pela tabela `accounts_usuario_user_permissions`.

### ativos.CriteriosCriticidade

Tabela: `ativos_criterioscriticidade`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `empresa` | FK → accounts.Empresa | não | coluna empresa_id; on_delete=CASCADE |
| `revisao` | PositiveIntegerField | não | — |
| `criterio_a` | TextField | não | — |
| `criterio_b` | TextField | não | — |
| `criterio_c` | TextField | não | — |
| `representante_manutencao` | CharField(200) | não | — |
| `data_validacao` | DateField | não | — |
| `criado_por` | FK → accounts.Usuario | sim | coluna criado_por_id; on_delete=SET_NULL |
| `criado_em` | DateTimeField | não | horário/data da criação; não editável no modelo |

Restrição `criterios_empresa_revisao_unica`: `UniqueConstraint`, campos `empresa, revisao`.

### ativos.TipoEquipamento

Tabela: `ativos_tipoequipamento`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `empresa` | FK → accounts.Empresa | não | coluna empresa_id; on_delete=CASCADE |
| `nome` | CharField(100) | não | — |
| `criticidade_padrao` | CharField(1) | sim | valores: A, B, C |
| `criticidade_padrao_legada` | CharField(20) | sim | não editável no modelo |
| `descricao_criterios` | TextField | não | — |

Restrição `tipo_equipamento_por_empresa_unico`: `UniqueConstraint`, campos `empresa, nome`.

### ativos.Equipamento

Tabela: `ativos_equipamento`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `empresa` | FK → accounts.Empresa | não | coluna empresa_id; on_delete=CASCADE |
| `nome` | CharField(255) | não | — |
| `tipo` | CharField(100) | sim | — |
| `tipo_equipamento` | FK → ativos.TipoEquipamento | sim | coluna tipo_equipamento_id; on_delete=SET_NULL |
| `fabricante` | CharField(100) | sim | — |
| `modelo` | CharField(100) | sim | — |
| `numero_serie` | CharField(100) | não | único |
| `descricao` | TextField | sim | — |
| `data_instalacao` | DateField | sim | — |
| `horimetro` | FloatField | não | — |
| `status` | CharField(20) | não | valores: ativo, manutencao, inativo |
| `criticidade` | CharField(1) | sim | valores: A, B, C |
| `criticidade_origem` | CharField(20) | não | valores: nao_avaliada, tipo, individual, migracao |
| `justificativa_criticidade` | TextField | não | — |
| `criterios_criticidade` | FK → ativos.CriteriosCriticidade | sim | coluna criterios_criticidade_id; on_delete=PROTECT |

### ativos.HistoricoCriticidadeEquipamento

Tabela: `ativos_historicocriticidadeequipamento`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | FK → ativos.Equipamento | não | coluna equipamento_id; on_delete=CASCADE |
| `criticidade_anterior` | CharField(1) | sim | — |
| `criticidade_nova` | CharField(1) | sim | valores: A, B, C |
| `justificativa` | TextField | não | — |
| `alterado_por` | FK → accounts.Usuario | sim | coluna alterado_por_id; on_delete=SET_NULL |
| `criado_em` | DateTimeField | não | horário/data da criação; não editável no modelo |
| `criterios_criticidade` | FK → ativos.CriteriosCriticidade | sim | coluna criterios_criticidade_id; on_delete=PROTECT |
| `origem` | CharField(20) | não | — |
| `dados_anteriores` | JSONField | não | — |

### ativos.EquipamentoLocalizacao

Tabela: `ativos_equipamentolocalizacao`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | OneToOne → ativos.Equipamento | não | coluna equipamento_id; on_delete=CASCADE; único |
| `setor` | CharField(100) | não | — |

### ativos.PlanoManutencao

Tabela: `ativos_planomanutencao`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | FK → ativos.Equipamento | não | coluna equipamento_id; on_delete=CASCADE |
| `nome_servico` | CharField(200) | não | — |
| `descricao` | TextField | não | — |
| `intervalo_horas` | FloatField | não | — |
| `prioridade` | CharField(20) | não | valores: baixa, media, alta, critica |
| `ativo` | BooleanField | não | — |
| `horimetro_ultima_os` | FloatField | não | — |

### telemetria.Sensor

Tabela: `telemetria_sensor`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | FK → ativos.Equipamento | não | coluna equipamento_id; on_delete=CASCADE |
| `nome` | CharField(100) | não | — |
| `tipo` | CharField(50) | não | valores: temperatura, vibracao, pressao, corrente, umidade |
| `unidade_medida` | CharField(20) | não | — |
| `limite_alerta` | FloatField | não | — |
| `limite_alerta_baixo_pct` | FloatField | sim | — |
| `limite_alerta_medio_pct` | FloatField | sim | — |
| `limite_alerta_critico_pct` | FloatField | sim | — |
| `descricao` | TextField | sim | — |
| `ativo` | BooleanField | não | — |

### telemetria.Telemetria

Tabela: `telemetria_telemetria`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `sensor` | FK → telemetria.Sensor | não | coluna sensor_id; on_delete=CASCADE |
| `valor` | FloatField | não | — |
| `timestamp` | DateTimeField | não | horário/data da criação; não editável no modelo |

### telemetria.TrendConfig

Tabela: `telemetria_trendconfig`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `sensor` | OneToOne → telemetria.Sensor | sim | coluna sensor_id; on_delete=CASCADE; único |
| `periodo_horas` | IntegerField | não | — |
| `num_leituras` | IntegerField | não | — |
| `minimo_leituras` | IntegerField | não | — |
| `duracao_minima_minutos` | IntegerField | não | — |
| `antecedencia_os_minutos` | PositiveIntegerField | não | — |
| `persistencia_minima` | FloatField | não | — |
| `r2_minimo` | FloatField | não | — |
| `direcao_alerta` | CharField(20) | não | valores: crescente, decrescente, ambas |
| `sensibilidade` | CharField(20) | não | valores: baixa, media, alta |
| `ativo` | BooleanField | não | — |

### telemetria.TrendDemo

Tabela: `telemetria_trenddemo`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | UUIDField(32) | não | PK; não editável no modelo |
| `owner` | FK → accounts.Usuario | não | coluna owner_id; on_delete=CASCADE |
| `sensor` | OneToOne → telemetria.Sensor | não | coluna sensor_id; on_delete=CASCADE; único |
| `cenario` | CharField(20) | não | valores: aumento, limite, recuperacao, estavel, pico |
| `status` | CharField(20) | não | valores: executando, concluido, parado |
| `passo` | PositiveSmallIntegerField | não | — |
| `criado_em` | DateTimeField | não | horário/data da criação; não editável no modelo |
| `ultima_leitura_em` | DateTimeField | não | — |

### alertas.Alerta

Tabela: `alertas_alerta`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | FK → ativos.Equipamento | não | coluna equipamento_id; on_delete=PROTECT |
| `sensor` | FK → telemetria.Sensor | sim | coluna sensor_id; on_delete=SET_NULL |
| `tipo_alerta` | CharField(100) | não | — |
| `origem` | CharField(20) | não | valores: limite, tendencia, manual |
| `ordem_servico` | FK → manutencao.OrdemServico | sim | coluna ordem_servico_id; on_delete=SET_NULL |
| `evento_chave` | CharField(160) | não | — |
| `dados_analise` | JSONField | não | — |
| `dados_deteccao` | JSONField | não | não editável no modelo |
| `historico_niveis` | JSONField | não | não editável no modelo |
| `data_normalizacao` | DateTimeField | sim | não editável no modelo |
| `analise_ia` | TextField | não | — |
| `data_ultima_analise` | DateTimeField | sim | — |
| `nivel` | CharField(20) | não | valores: baixo, medio, critico |
| `descricao` | TextField | não | — |
| `data_alerta` | DateTimeField | não | horário/data da criação; não editável no modelo |
| `status` | CharField(20) | não | valores: ativo, resolvido, ignorado |

Restrição `alerta_evento_ativo_unico`: `UniqueConstraint`, campos `evento_chave`, condição `(AND: ('status', 'ativo'), (NOT (AND: ('evento_chave', ''))))`.

### manutencao.OrdemServico

Tabela: `manutencao_ordemservico`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `equipamento` | FK → ativos.Equipamento | não | coluna equipamento_id; on_delete=CASCADE |
| `responsavel` | FK → accounts.Usuario | sim | coluna responsavel_id; on_delete=SET_NULL |
| `alerta_origem` | OneToOne → alertas.Alerta | sim | coluna alerta_origem_id; on_delete=SET_NULL; único |
| `sensor_origem` | FK → telemetria.Sensor | sim | coluna sensor_origem_id; on_delete=SET_NULL |
| `tipo_os` | CharField(20) | não | valores: corretiva, preditiva, preventiva |
| `titulo` | CharField(200) | não | — |
| `descricao` | TextField | não | — |
| `evidencia_preditiva` | JSONField | não | não editável no modelo |
| `status` | CharField(20) | não | valores: pendente, andamento, concluida, cancelada |
| `prioridade` | CharField(20) | sim | valores: A, B, C |
| `gravidade_condicao` | CharField(20) | não | valores: ausente, baixa, moderada, alta, critica |
| `risco_seguranca` | BooleanField | não | — |
| `prioridade_manual` | BooleanField | não | — |
| `prioridade_automatica` | CharField(20) | sim | valores: A, B, C |
| `prioridade_origem` | CharField(20) | não | valores: herdada, ajustada, convertida |
| `prioridade_herdada_conhecida` | BooleanField | não | — |
| `justificativa_prioridade` | TextField | não | — |
| `criticidade_na_abertura` | CharField(1) | sim | — |
| `justificativa_criticidade_na_abertura` | TextField | não | — |
| `criterios_criticidade_na_abertura` | FK → ativos.CriteriosCriticidade | sim | coluna criterios_criticidade_na_abertura_id; on_delete=PROTECT |
| `data_abertura` | DateTimeField | não | — |
| `data_conclusao` | DateTimeField | sim | — |

### manutencao.HistoricoPrioridadeOS

Tabela: `manutencao_historicoprioridadeos`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `ordem_servico` | FK → manutencao.OrdemServico | não | coluna ordem_servico_id; on_delete=CASCADE |
| `prioridade_anterior` | CharField(20) | sim | — |
| `prioridade_nova` | CharField(20) | sim | — |
| `justificativa` | TextField | não | — |
| `origem` | CharField(20) | não | — |
| `alterado_por` | FK → accounts.Usuario | sim | coluna alterado_por_id; on_delete=SET_NULL |
| `criado_em` | DateTimeField | não | horário/data da criação; não editável no modelo |
| `dados_anteriores` | JSONField | não | — |

### manutencao.HistoricoManutencao

Tabela: `manutencao_historicomanutencao`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `ordem_servico` | OneToOne → manutencao.OrdemServico | não | coluna ordem_servico_id; on_delete=CASCADE; único |
| `descricao_servico` | TextField | não | — |
| `data_execucao` | DateField | não | — |
| `custo_pecas` | DecimalField(10,2) | não | — |
| `custo_mao_de_obra` | DecimalField(10,2) | não | — |

### gemini_api.PromptAnaliseOS

Tabela: `gemini_api_promptanaliseos`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `empresa` | OneToOne → accounts.Empresa | não | coluna empresa_id; on_delete=CASCADE; único |
| `custom_text` | TextField | não | — |
| `updated_at` | DateTimeField | não | atualizado automaticamente; não editável no modelo |

### gemini_api.PromptConfig

Tabela: `gemini_api_promptconfig`.

| Campo | Tipo / relação | Aceita null? | Restrições e opções |
|---|---|---|---|
| `id` | BigAutoField | não | PK |
| `key` | CharField(50) | não | único; valores: system_instruction_tecnico, system_instruction_gestor, system_instruction_admin, chat_context, os_analysis, unassigned_orders, finance, trend_analysis |
| `label` | CharField(120) | não | — |
| `custom_text` | TextField | não | — |
| `original_text` | TextField | não | — |
| `updated_at` | DateTimeField | não | atualizado automaticamente; não editável no modelo |

## Modelos e migrações

Este inventário descreve o estado dos modelos no código, não comprova que uma base existente já recebeu todas as migrações. Consulte `python manage.py showmigrations --plan` e o [procedimento de compatibilidade](HISTORICO_ALERTAS.md#atualização-do-banco-e-compatibilidade).

A migração `accounts.0002_alter_usuario_managers_alter_usuario_tipo_usuario` inclui `operador` nas opções e o define como padrão de novos usuários; não altera os perfis já existentes. O `UsuarioManager` mantém `createsuperuser` com perfil `admin`. Execute `python manage.py migrate` antes de usar a versão atual. O seed passa a incluir um operador por empresa (cinco funcionários por padrão, mínimo três). Não execute o seed para atualizar uma base operacional. As permissões são aplicadas pela API, não por restrições SQL no campo de perfil. A O.S. manual do operador usa a tabela existente, sem novos campos: `tipo_os=corretiva`, `status=pendente`, `responsavel=NULL` e prioridade calculada na abertura. Veja [perfis e permissões](PERFIS_E_PERMISSOES.md). Modelos sem tabela própria, como views, builders, criadores de exportador, políticas e adapters, estão explicados no [guia oficial de padrões](docs_padroes_projeto/Verificacao_Padroes.md).
