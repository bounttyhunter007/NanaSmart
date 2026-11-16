### Tópico 9: Mapeamento de Classes e Responsabilidades

Esta lista contém somente as classes de modelo/entidades de domínio encontradas nos `models.py` do backend. Serializers, views, DTOs, controllers, admin, serviços e infraestrutura foram excluídos.

| Nome da Classe | Responsabilidade Principal |
|---|---|
| `Empresa` | Representa a empresa cadastrada na plataforma e mantém seus dados de identificação, contato e localização. |
| `Usuario` | Representa um usuário, combinando autenticação herdada do Django com perfil e vínculo opcional a uma empresa. |
| `Equipamento` | Representa uma máquina ou ativo pertencente a uma empresa, com identificação, estado e informações de funcionamento. |
| `EquipamentoLocalizacao` | Representa o setor associado a um equipamento. |
| `PlanoManutencao` | Define um serviço de manutenção recorrente associado a um equipamento e a um intervalo de horímetro. |
| `OrdemServico` | Representa uma atividade de manutenção, seu tipo, prioridade, estado, datas e responsável. |
| `HistoricoManutencao` | Registra a execução e os custos de uma ordem de serviço. |
| `Alerta` | Representa uma situação que exige atenção, associada a um equipamento e classificada por nível e estado. |
| `Sensor` | Representa um sensor associado a um equipamento, com unidade e limites para gerar alertas. |
| `Telemetria` | Representa uma leitura coletada por um sensor, incluindo seu valor e momento de registro. |
| `TrendConfig` | Armazena parâmetros usados na análise de tendência de um sensor ou na configuração global. |
| `PromptConfig` | Armazena o texto original e o texto personalizado de cada configuração de prompt. |
| `KpiService` | Calcula indicadores MTTR, MTBF, disponibilidade, quantidade de manutenções e custos por equipamento. |
| `GeminiBaseView` | View base que centraliza validação, contexto, montagem de prompt e chamada do Gemini. |
| `GeminiChatView` | Processa o chat geral de manutenção usando o fluxo comum da view Gemini. |
| `GeminiOsAnalysisView` | Analisa ordens de serviço e sugere ações práticas. É a classe real mais próxima de `GeminiUsAnalysisView`. |
| `GeminiUnassignedOrdersView` | Analisa ordens de serviço sem responsável. É a classe real mais próxima da descrição `GeminiUsageAndOrdersView`, mas não tem esse nome. |
| `GeminiFinanceView` | Solicita análise de custos e gestão financeira e bloqueia usuários técnicos. |
| `GeminiTrendAnalysisView` | Solicita análise de tendência de um sensor. |
| `Prompt` | Armazena o texto produzido pelo builder e oferece acesso textual. |
| `PromptBuilder` | Define o contrato abstrato para construir um prompt em etapas. |
| `PromptBuilderConcreto` | Acumula e formata blocos, limita linhas e produz um `Prompt`. |
| `PromptDirector` | Coordena a sequência de construção de prompts para quatro finalidades. |
| `BasePermissionPolicy` | Define o contrato `can_access` para políticas de autorização. |
| `GestorPolicy` | Permite acesso a gestor/admin autenticado ou superusuário. |
| `TecnicoPolicy` | Permite acesso a usuário autenticado de perfil técnico. |
| `GestorOrReadOnlyPolicy` | Permite leitura a usuários autenticados e escrita a gestor/admin ou superusuário. Corresponde ao nome pedido `GestorReadOnlyPolicy`, que não existe literalmente. |
| `AuthenticatedNoDeleteForTecnicoPolicy` | Permite leitura a autenticados; técnicos não podem excluir e outros métodos de escrita ficam restritos a gestor/admin ou superusuário. Corresponde ao nome pedido `AuthenticateAndDeleteForTecnicoPolicy`, que não existe literalmente. |
| `PermissionPolicyFactory` | Registra e fornece instâncias de políticas pelo nome. |
| `Exportador` | Define o contrato comum de exportação para resposta HTTP. |
| `ExportadorCSV` | Produz arquivo CSV. |
| `ExportadorExcel` | Produz arquivo Excel XLSX. |
| `ExportadorPDF` | Produz arquivo PDF com orientação configurável. |
| `ExportadorFactory` | Registra classes de exportadores e cria o exportador solicitado pelo formato. |

**Nomes não encontrados literalmente no código:** `GeminiUsageAndOrdersView`, `GeminiUsAnalysisView`, `GestorReadOnlyPolicy` e `AuthenticateAndDeleteForTecnicoPolicy`. As descrições acima indicam as classes reais correspondentes ou mais próximas. `GeminiFinanceView`, `GeminiTrendAnalysisView`, `GeminiChatView` e demais views citadas são classes de aplicação, não modelos ORM.

### Tópico 10: Detalhamento dos Atributos (por Classe)

**Como ler a visibilidade:** a visibilidade abaixo representa um modelo conceitual encapsulado para uma possível implementação futura, não as restrições atuais do Django. Campos que guardam estado são privados (`-`); constantes de domínio e propriedades de leitura são públicas (`+`). Python não impõe controle de acesso estrito, e a visibilidade UML não substitui permissões ou validações. `blank=True` permite valor em branco em validação/formulários; `null=True` permite NULL no banco.

Todo modelo possui a chave primária automática `id`, configurada como `BigAutoField` neste projeto.

#### Classe: Empresa

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `nome` | CharField(255) | `-` (privado) | Nome da empresa cadastrada. |
| `cnpj` | CharField(18) | `-` (privado) | CNPJ único globalmente (`unique=True`). |
| `email` | EmailField | `-` (privado) | E-mail para contato com a empresa. |
| `telefone` | CharField(20), nullable | `-` (privado) | Telefone opcional (`blank=True`, `null=True`). |
| `cidade` | CharField(100), nullable | `-` (privado) | Cidade opcional. |
| `estado` | CharField(50), nullable | `-` (privado) | Estado opcional. |
| `endereco` | TextField, nullable | `-` (privado) | Endereço da empresa; opcional. |
| `data_cadastro` | DateTimeField | `-` (privado) | Data e hora preenchidas automaticamente na criação. |

#### Classe: Usuario

Campos próprios do projeto:

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário herdado do modelo de usuário Django. |
| `empresa` | ForeignKey(Empresa), nullable | `-` (privado) | Empresa do usuário; vínculo opcional, `CASCADE`, related name `usuarios`. |
| `tipo_usuario` | CharField(20) | `-` (privado) | Perfil: `admin`, `gestor` ou `tecnico`; padrão `tecnico`. |
| `cargo` | CharField(100), nullable | `-` (privado) | Cargo do usuário na empresa; opcional. |
| `telefone` | CharField(20), nullable | `-` (privado) | Telefone de contato; opcional. |
| `foto_perfil` | ImageField, nullable | `-` (privado) | Imagem opcional armazenada sob `perfil_fotos/`; não é uma string comum. |

Campos relevantes herdados de `AbstractUser` (Django):

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `username` | CharField | `-` (privado) | Nome de login; único no modelo padrão. |
| `first_name` | CharField | `-` (privado) | Primeiro nome; permite vazio no modelo padrão. |
| `last_name` | CharField | `-` (privado) | Sobrenome; permite vazio no modelo padrão. |
| `email` | EmailField | `-` (privado) | E-mail herdado do usuário Django. |
| `password` | CharField | `-` (privado) | Hash da senha, não senha em texto claro; dado sensível. |
| `last_login` | DateTimeField, nullable | `-` (privado) | Data e hora do último login. |
| `is_superuser` | BooleanField | `-` (privado) | Indica privilégios de superusuário no Django. |
| `is_staff` | BooleanField | `-` (privado) | Indica acesso ao site administrativo Django. |
| `is_active` | BooleanField | `-` (privado) | Indica se a conta está ativa. |
| `date_joined` | DateTimeField | `-` (privado) | Data de ingresso da conta. |
| `groups` | ManyToManyField(Group) | `-` (privado) | Grupos de autorização herdados. |
| `user_permissions` | ManyToManyField(Permission) | `-` (privado) | Permissões diretas herdadas. |

Os campos de autenticação e privilégio são considerados privados no desenho conceitual; isso não significa que o runtime Django os proteja por visibilidade UML. O acesso real deve ser controlado por autorização e validação.

#### Classe: Equipamento

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `empresa` | ForeignKey(Empresa) | `-` (privado) | Empresa proprietária; obrigatória, `CASCADE`, related name `equipamentos`. |
| `nome` | CharField(255) | `-` (privado) | Nome do equipamento. |
| `tipo` | CharField(100), nullable | `-` (privado) | Tipo opcional. `TIPO_EQUIPAMENTO_CHOICES` existe, mas não está associado ao campo. |
| `fabricante` | CharField(100), nullable | `-` (privado) | Fabricante opcional. |
| `modelo` | CharField(100), nullable | `-` (privado) | Modelo opcional. |
| `numero_serie` | CharField(100) | `-` (privado) | Número de série único globalmente, não por empresa. |
| `descricao` | TextField, nullable | `-` (privado) | Descrição opcional. Não existe atributo `capacidade`. |
| `data_instalacao` | DateField, nullable | `-` (privado) | Data de instalação opcional. |
| `horimetro` | FloatField | `-` (privado) | Horas acumuladas; padrão `0`; sem validador positivo declarado. |
| `status` | CharField(20) | `-` (privado) | Choices `ativo`, `manutencao`, `inativo`; padrão `ativo`. |
| `criticidade` | CharField(20) | `-` (privado) | Choices `normal`, `alta`; padrão `normal`. |
| `TIPO_EQUIPAMENTO_CHOICES` | Tupla de tuplas | `+` (público) | Constante com opções sugeridas para tipo; atualmente não vinculada ao campo `tipo`. |
| `STATUS_CHOICES` | Tupla de tuplas | `+` (público) | Constante de opções para status. |
| `CRITICIDADE_CHOICES` | Tupla de tuplas | `+` (público) | Constante de opções para criticidade. |

#### Classe: EquipamentoLocalizacao

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `equipamento` | OneToOneField(Equipamento) | `-` (privado) | Equipamento localizado; obrigatório, `CASCADE`, related name `localizacao`. |
| `setor` | CharField(100) | `-` (privado) | Setor onde o equipamento está localizado. |

#### Classe: PlanoManutencao

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `equipamento` | ForeignKey(Equipamento) | `-` (privado) | Equipamento atendido; obrigatório, `CASCADE`, related name `planos_manutencao`. |
| `nome_servico` | CharField(200) | `-` (privado) | Nome do serviço recorrente. |
| `descricao` | TextField | `-` (privado) | Detalhes do serviço planejado. |
| `intervalo_horas` | FloatField | `-` (privado) | Intervalo entre manutenções; não há validador positivo declarado. |
| `prioridade` | CharField(20) | `-` (privado) | Choices `baixa`, `media`, `alta`, `critica`; padrão `media`. |
| `ativo` | BooleanField | `-` (privado) | Indica se o plano está ativo; padrão `True`. |
| `horimetro_ultima_os` | FloatField | `-` (privado) | Horímetro da última OS gerada; padrão `0`, inicializado com o horímetro atual na criação. |
| `PRIORIDADE_CHOICES` | Tupla de tuplas | `+` (público) | Constante com opções de prioridade. |

#### Classe: OrdemServico

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `equipamento` | ForeignKey(Equipamento) | `-` (privado) | Equipamento atendido; obrigatório, `CASCADE`, related name `ordens_servico`. |
| `responsavel` | ForeignKey(Usuario), nullable | `-` (privado) | Responsável opcional; `SET_NULL`, related name `minhas_os`. |
| `tipo_os` | CharField(20) | `-` (privado) | Choices `corretiva`, `preditiva`, `preventiva`; padrão `preventiva`. |
| `titulo` | CharField(200) | `-` (privado) | Título resumido da ordem. |
| `descricao` | TextField | `-` (privado) | Problema ou serviço a realizar. |
| `status` | CharField(20) | `-` (privado) | Choices `pendente`, `andamento`, `concluida`, `cancelada`; padrão `pendente`. |
| `prioridade` | CharField(20) | `-` (privado) | Choices `baixa`, `media`, `alta`, `critica`; padrão `baixa`. |
| `data_abertura` | DateTimeField | `-` (privado) | Data de abertura; padrão `timezone.now`. |
| `data_conclusao` | DateTimeField, nullable | `-` (privado) | Preenchido por `save()` quando concluída e ainda vazio. |
| `TIPO_OS_CHOICES` | Tupla de tuplas | `+` (público) | Constante com tipos de OS. |
| `STATUS_CHOICES` | Tupla de tuplas | `+` (público) | Constante com estados da OS. |
| `PRIORIDADE_CHOICES` | Tupla de tuplas | `+` (público) | Constante com prioridades da OS. |

#### Classe: HistoricoManutencao

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `ordem_servico` | OneToOneField(OrdemServico) | `-` (privado) | OS associada; obrigatória, `CASCADE`, related name `historico`. |
| `descricao_servico` | TextField | `-` (privado) | Descrição do serviço executado. |
| `data_execucao` | DateField | `-` (privado) | Data da execução. |
| `custo_pecas` | DecimalField(10, 2) | `-` (privado) | Custo de peças; padrão `0.00`. |
| `custo_mao_de_obra` | DecimalField(10, 2) | `-` (privado) | Custo de mão de obra; padrão `0.00`. |
| `custo_total` | Decimal calculado (property) | `+` (público) | Soma dos custos; propriedade calculada, não coluna persistida. |

#### Classe: Alerta

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `equipamento` | ForeignKey(Equipamento) | `-` (privado) | Equipamento relacionado; obrigatório, `CASCADE`, related name `alertas`. |
| `tipo_alerta` | CharField(100) | `-` (privado) | Tipo da condição que originou o alerta. |
| `nivel` | CharField(20) | `-` (privado) | Choices `baixo`, `medio`, `critico`; padrão `baixo`. |
| `descricao` | TextField | `-` (privado) | Descrição da situação. |
| `data_alerta` | DateTimeField | `-` (privado) | Data e hora preenchidas automaticamente. |
| `status` | CharField(20) | `-` (privado) | Choices `ativo`, `resolvido`, `ignorado`; padrão `ativo`. |
| `NIVEL_CHOICES` | Tupla de tuplas | `+` (público) | Constante com níveis possíveis. |
| `STATUS_CHOICES` | Tupla de tuplas | `+` (público) | Constante com estados possíveis. |

#### Classe: Sensor

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `equipamento` | ForeignKey(Equipamento) | `-` (privado) | Equipamento monitorado; obrigatório, `CASCADE`, related name `sensores`. |
| `nome` | CharField(100) | `-` (privado) | Nome identificador do sensor. |
| `tipo` | CharField(50) | `-` (privado) | Tipo medido: temperatura, vibração, pressão, corrente ou umidade. |
| `unidade_medida` | CharField(20) | `-` (privado) | Unidade utilizada nas leituras. |
| `limite_alerta` | FloatField | `-` (privado) | Limite de referência; não há validador de positividade declarado. |
| `limite_alerta_baixo_pct` | FloatField, nullable | `-` (privado) | Opcional, sem default persistido; fallback de validação 70.0. |
| `limite_alerta_medio_pct` | FloatField, nullable | `-` (privado) | Opcional, sem default persistido; fallback de validação 85.0. |
| `limite_alerta_critico_pct` | FloatField, nullable | `-` (privado) | Opcional, sem default persistido; fallback de validação 100.0. |
| `descricao` | TextField, nullable | `-` (privado) | Descrição opcional. |
| `ativo` | BooleanField | `-` (privado) | Indica se o sensor está ativo; padrão `True`. |
| `TIPO_SENSOR_CHOICES` | Tupla de tuplas | `+` (público) | Constante com tipos de sensor disponíveis. |

Regra de validação: os percentuais devem estar entre 0 e 100 e seguir `baixo < médio < crítico`. Os fallbacks são utilizados na validação, mas não são gravados automaticamente nos campos quando estes permanecem NULL.

#### Classe: Telemetria

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `sensor` | ForeignKey(Sensor) | `-` (privado) | Sensor da leitura; obrigatório, `CASCADE`, related name `leituras`. Equipamento é acessado via sensor. |
| `valor` | FloatField | `-` (privado) | Valor medido. |
| `timestamp` | DateTimeField | `-` (privado) | Data/hora automática da leitura; ordenação padrão decrescente. |

#### Classe: TrendConfig

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `sensor` | OneToOneField(Sensor), nullable | `-` (privado) | Sensor opcional; `CASCADE`, related name `trend_config`; NULL representa configuração global. |
| `periodo_horas` | IntegerField | `-` (privado) | Período analisado; padrão 24; sem validador positivo declarado. |
| `num_leituras` | IntegerField | `-` (privado) | Número máximo de leituras; padrão 50. Não é `min_leituras`. |
| `sensibilidade` | CharField(20) | `-` (privado) | Choices `baixa`, `media`, `alta`; padrão `media`. |
| `ativo` | BooleanField | `-` (privado) | Indica se a configuração está ativa; padrão `True`. |
| `SENSIBILIDADE_CHOICES` | Tupla de tuplas | `+` (público) | Constante com níveis de sensibilidade. |

Um OneToOne limita a uma configuração não nula por sensor, mas pode haver mais de uma configuração com `sensor=NULL`; o modelo não garante uma única configuração global.

#### Classe: PromptConfig

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `id` | BigAutoField | `-` (privado) | Identificador primário automático. |
| `key` | CharField(50) | `-` (privado) | Chave entre as opções declaradas; `unique=True`. |
| `label` | CharField(120) | `-` (privado) | Nome de exibição; pode ficar vazio. |
| `custom_text` | TextField | `-` (privado) | Texto personalizado; padrão vazio. |
| `original_text` | TextField | `-` (privado) | Texto original de referência; padrão vazio. |
| `updated_at` | DateTimeField | `-` (privado) | Atualizado automaticamente a cada gravação. |
| `PROMPT_KEYS` | Lista de tuplas | `+` (público) | Constante com chaves e rótulos permitidos. |
| `is_customized` | bool (property) | `+` (público) | Indica se existe texto personalizado não vazio. |
| `effective_text` | string (property) | `+` (público) | Retorna texto personalizado quando existe; senão, o texto original. |

O modelo não tem atributo `active`; a unicidade é por chave, não por estado de ativação.

#### Classe: KpiService

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | A classe atua como namespace de método estático e não mantém estado de instância. |

#### Classe: GeminiBaseView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `permission_classes` | tupla/lista de permissões DRF | `-` (privado conceitual) | Configuração herdada/definida da classe para exigir autenticação. A proteção efetiva é aplicada pelo DRF, não pela visibilidade. |
| `serializer_class` | classe serializer | `-` (privado conceitual) | Serializer de entrada, padrão `GeminiMessageSerializer`. |
| `response_serializer_class` | classe serializer | `-` (privado conceitual) | Serializer de resposta documentada, padrão `GeminiResponseSerializer`. |
| `system_purpose` | string | `-` (privado conceitual) | Finalidade padrão para a instrução de sistema. |
| `prompt_builder` | função ou `None` | `-` (privado conceitual) | Função de alto nível que monta o prompt; subclasses podem definir outra. |
| `temperature` | float | `-` (privado conceitual) | Temperatura padrão da chamada, `0.35`. |
| `missing_api_suffix` | string | `-` (privado conceitual) | Complemento textual quando a chave Gemini não está configurada. |
| `forbidden_message` | string ou `None` | `-` (privado conceitual) | Mensagem de bloqueio opcional; padrão `None`. |
| `requires_financial_summary` | bool | `-` (privado conceitual) | Define se o contexto deve incluir resumo financeiro; padrão `False`. |

#### Classe: GeminiChatView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `system_purpose` | string | `-` (privado conceitual) | Define a finalidade como responder perguntas gerais sobre ativos e manutenção. |
| `prompt_builder` | função | `-` (privado conceitual) | Aponta para `build_chat_prompt`. |
| `temperature` | float | `-` (privado conceitual) | Sobrescreve o padrão com `0.4`. |
| `missing_api_suffix` | string | `-` (privado conceitual) | Mensagem específica para configuração do chat. |

#### Classe: GeminiOsAnalysisView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `system_purpose` | string | `-` (privado conceitual) | Finalidade de analisar OS e sugerir ações. |
| `prompt_builder` | função | `-` (privado conceitual) | Aponta para `build_os_analysis_prompt`. |

#### Classe: GeminiUnassignedOrdersView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `system_purpose` | string | `-` (privado conceitual) | Finalidade de avaliar OS sem atribuição. |
| `prompt_builder` | — | — | Não define atributo; sobrescreve `get_prompt()` diretamente. |

#### Classe: GeminiFinanceView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `system_purpose` | string | `-` (privado conceitual) | Finalidade de analisar custos e gestão financeira. |
| `requires_financial_summary` | bool | `-` (privado conceitual) | `True`; solicita que a base acrescente resumo financeiro ao contexto. |
| `forbidden_message` | string | `-` (privado conceitual) | Mensagem de bloqueio para perfil técnico. |

#### Classe: GeminiTrendAnalysisView

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `system_purpose` | string | `-` (privado conceitual) | Finalidade de diagnosticar tendências de sensores. |
| `missing_api_suffix` | string | `-` (privado conceitual) | Mensagem específica de configuração para análise de tendência. |
| `prompt_builder` | — | — | Não define atributo; sobrescreve `get_prompt()` diretamente. |

#### Classe: Prompt

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `_texto` | string | `#` (protegido por convenção) | Texto final do prompt. É acessível por `obter_texto()` e `__str__()`. |

#### Classe: PromptBuilder

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Classe abstrata que define operações; o estado `_blocos` existe somente no builder concreto. |

#### Classe: PromptBuilderConcreto

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `_blocos` | list[string] | `#` (protegido por convenção) | Lista mutável de blocos durante a construção. |
| `_max_linhas` | int | `#` (protegido por convenção) | Máximo de linhas exibidas em listas; inicializado com 5. |

#### Classe: PromptDirector

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Seus métodos são estáticos e recebem o builder e os dados por parâmetro. |

#### Classe: BasePermissionPolicy

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Abstração sem estado; define o contrato de autorização. |

#### Classe: GestorPolicy

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | A decisão é calculada a partir do usuário recebido. |

#### Classe: TecnicoPolicy

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | A decisão é calculada a partir do usuário recebido. |

#### Classe: GestorOrReadOnlyPolicy

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | A decisão depende do usuário e método HTTP. |

#### Classe: AuthenticatedNoDeleteForTecnicoPolicy

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | A decisão depende do usuário e método HTTP. |

#### Classe: PermissionPolicyFactory

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `_policies` | dict[string, BasePermissionPolicy] | `#` (protegido por convenção) | Registro de instâncias de política. Compartilhado no nível da classe. |

#### Classe: Exportador

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Classe abstrata que define o contrato de exportação. |

#### Classe: ExportadorCSV

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Cria a resposta CSV durante a chamada de exportação. |

#### Classe: ExportadorExcel

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| Não possui atributos próprios | — | — | Cria workbook e estilos localmente durante a exportação. |

#### Classe: ExportadorPDF

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `_orientacao` | string | `#` (protegido por convenção) | Orientação do documento; padrão `landscape`. |

#### Classe: ExportadorFactory

| Atributo | Tipo | Visibilidade | Descrição / Regra de Negócio |
|---|---|:---:|---|
| `_registro` | dict[string, type] | `#` (protegido por convenção) | Mapeia formato às classes concretas de exportador. |

### Tópico 11: Detalhamento dos Métodos (por Classe)

As tabelas abaixo documentam métodos próprios dos modelos e operações herdadas relevantes. O código não declara type hints para vários métodos Django, então os parâmetros são descritos de forma legível, sem sugerir anotações inexistentes. Na visibilidade conceitual, `save()` e `clean()` são protegidos (`#`), `__str__()` e propriedades são públicas (`+`).

#### Classe: Empresa

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna o nome da empresa. Método especial público do Python. |

#### Classe: Usuario

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Formata username, tipo de usuário e empresa. |
| `+ set_password(raw_password)` (herdado) | `raw_password: str` | `None` | Gera e armazena o hash da senha, não o texto claro. |
| `+ check_password(raw_password)` (herdado) | `raw_password: str` | `bool` | Verifica a senha fornecida contra o hash armazenado. |

#### Classe: Equipamento

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna nome e número de série do equipamento. |

#### Classe: EquipamentoLocalizacao

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna setor e nome do equipamento. |

#### Classe: PlanoManutencao

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `# save(*args, **kwargs)` | Argumentos aceitos pelo `Model.save`; sem tipos declarados. | `None` | Na criação, define `horimetro_ultima_os` com o horímetro atual do equipamento e delega a persistência. |
| `+ __str__()` | `self` | `str` | Resume o serviço, intervalo e equipamento. |

#### Classe: OrdemServico

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `# save(*args, **kwargs)` | Argumentos aceitos pelo `Model.save`; sem tipos declarados. | `None` | Se status for concluída e a data estiver vazia, preenche `data_conclusao` antes de persistir. Não chama `full_clean()`. |
| `+ __str__()` | `self` | `str` | Resume ID, título e equipamento da OS. |

#### Classe: HistoricoManutencao

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ custo_total` (property) | `self` | `Decimal` | Soma custos de peças e mão de obra; acessada sem parênteses e não persistida como coluna. |
| `+ __str__()` | `self` | `str` | Resume OS associada e data de execução. |

#### Classe: Alerta

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna nível, tipo de alerta e equipamento. |

#### Classe: Sensor

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `# clean()` | `self` | `None` ou `ValidationError` | Usa fallbacks 70/85/100 para percentuais ausentes e valida faixa 0–100 e ordem baixo < médio < crítico. Não valida positividade de `limite_alerta`. |
| `# save(*args, **kwargs)` | Argumentos aceitos pelo `Model.save`; sem tipos declarados. | `None` | Executa `full_clean()` antes de salvar. Operações bulk podem não chamar esse método. |
| `+ __str__()` | `self` | `str` | Retorna tipo formatado, nome e equipamento. |

#### Classe: Telemetria

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna tipo, valor, unidade e timestamp da leitura. |

#### Classe: TrendConfig

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Identifica configuração por sensor/equipamento ou como configuração global. |

#### Classe: PromptConfig

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __str__()` | `self` | `str` | Retorna rótulo da chave e a chave. |
| `+ is_customized` (property) | `self` | `bool` | Indica se `custom_text.strip()` não está vazio. |
| `+ effective_text` (property) | `self` | `str` | Retorna o texto personalizado quando preenchido; caso contrário, `original_text`. |

#### Classe: KpiService

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ calcular_kpi(equipamento, os_queryset)` (static) | `equipamento`; queryset de OS | `dict` | Calcula MTTR, MTBF, disponibilidade, total de manutenções e custo. O nome real é singular `calcular_kpi`, não `calcular_kpis`. |

#### Classe: GeminiBaseView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ get_missing_api_response()` | `self` | `dict` | Monta resposta informando ausência da configuração da API. |
| `+ check_access(user)` | `user` | `bool` | Hook de autorização; a implementação base permite acesso. |
| `+ get_prompt(user, context, message)` | usuário, contexto e mensagem | `str` | Chama função de prompt configurada ou retorna a mensagem sem alteração. |
| `+ run_gemini(system_instruction, user_prompt, history)` | instrução, prompt e histórico | tupla `(str, str)` | Chama a função `generate_content()` com a temperatura definida na classe. |
| `+ post(request)` | requisição HTTP | Response | Valida mensagem, verifica acesso e disponibilidade, coleta contexto, monta instrução/prompt e consulta Gemini. Captura exceções e as inclui no corpo da resposta. |

#### Classe: GeminiChatView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ post(request)` | requisição HTTP | Response | Delega à implementação de `GeminiBaseView.post()`; adiciona documentação do endpoint. |

#### Classe: GeminiOsAnalysisView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ post(request)` | requisição HTTP | Response | Delega à view base para analisar ordens abertas. |

#### Classe: GeminiUnassignedOrdersView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ get_prompt(user, context, message)` | usuário, contexto e mensagem | `str` | Chama o builder de prompt de ordens sem atribuição. |
| `+ post(request)` | requisição HTTP | Response | Delega à view base. Esta classe é mais próxima da descrição “GeminiUsageAndOrdersView”, mas seu nome real é diferente. |

#### Classe: GeminiFinanceView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ check_access(user)` | usuário | `bool` | Retorna falso para perfil técnico. |
| `+ get_prompt(user, context, message)` | usuário, contexto e mensagem | `str` | Monta o prompt financeiro. |
| `+ post(request)` | requisição HTTP | Response | Delega à view base, que inclui o resumo financeiro quando configurado. |

#### Classe: GeminiTrendAnalysisView

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ get_prompt(user, context, message)` | usuário, contexto e mensagem | `str` | Obtém `sensor_id`, analisa tendência e monta prompt; levanta ValueError se o ID/dados forem inválidos. |
| `+ post(request)` | requisição HTTP | Response | Delega à view base para executar a análise. |

#### Classe: Prompt

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __init__(texto: str)` | texto final | `None` | Armazena o texto no atributo interno `_texto`. |
| `+ obter_texto()` | `self` | `str` | Retorna o texto armazenado. |
| `+ __str__()` | `self` | `str` | Retorna o texto armazenado. |

#### Classe: PromptBuilder

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ com_contexto(context_str)` | string de contexto | `PromptBuilder` | Operação abstrata para adicionar contexto. |
| `+ com_alertas(alertas)` | lista de alertas | `PromptBuilder` | Operação abstrata para adicionar alertas. |
| `+ com_ordens(ordens, titulo)` | lista e título | `PromptBuilder` | Operação abstrata para adicionar ordens ou dados tabulares. |
| `+ com_telemetria(dados)` | lista de dados | `PromptBuilder` | Operação abstrata para adicionar telemetria. |
| `+ com_financeiro(dados)` | lista de dados | `PromptBuilder` | Operação abstrata para adicionar resumo financeiro. |
| `+ com_instrucoes(texto)` | texto | `PromptBuilder` | Operação abstrata para adicionar instruções. |
| `+ com_pergunta(texto)` | texto | `PromptBuilder` | Operação abstrata para adicionar pergunta. |
| `+ build()` | `self` | `Prompt` | Contrato abstrato para produzir o produto final. |
| `+ reset()` | `self` | `None` | Contrato abstrato para limpar estado do builder. |

#### Classe: PromptBuilderConcreto

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __init__()` | nenhum | `None` | Inicializa lista de blocos e limite de cinco linhas. |
| `+ reset()` | `self` | `None` | Limpa os blocos acumulados. |
| `# _truncar(linhas, max_linhas)` | lista de linhas e limite | lista | Mantém até o limite e acrescenta quantidade omitida. Método interno por convenção. |
| `+ com_contexto(context_str)` | string | `PromptBuilder` | Adiciona contexto se não estiver vazio e retorna `self`. |
| `+ com_alertas(alertas)` | lista | `PromptBuilder` | Formata e trunca alertas; retorna `self`. |
| `+ com_ordens(ordens, titulo)` | lista e título | `PromptBuilder` | Formata e trunca ordens; retorna `self`. |
| `+ com_telemetria(dados)` | lista | `PromptBuilder` | Formata e trunca leituras; retorna `self`. |
| `+ com_financeiro(blocos_financeiros)` | lista | `PromptBuilder` | Junta blocos financeiros; retorna `self`. |
| `+ com_instrucoes(texto)` | string | `PromptBuilder` | Adiciona instruções se presentes; retorna `self`. |
| `+ com_pergunta(texto)` | string | `PromptBuilder` | Adiciona pergunta do usuário; retorna `self`. |
| `+ build()` | `self` | `Prompt` | Junta blocos e cria o objeto `Prompt`. |

#### Classe: PromptDirector

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ montar_chat(builder, context, context_str, message)` (static) | builder, contexto, texto contextual e mensagem | `Prompt` | Reseta builder e orquestra contexto, alertas, ordens/KPIs, telemetria e pergunta. |
| `+ montar_analise_os(builder, context, context_str, instruction, message)` (static) | builder, contexto, contexto textual, instrução e mensagem | `Prompt` | Monta prompt com ordens atribuídas e sem atribuição. |
| `+ montar_ordens_nao_atribuidas(...)` (static) | builder, contexto, contexto textual, instrução e mensagem | `Prompt` | Monta prompt específico para OS sem responsável. |
| `+ montar_financeiro(...)` (static) | builder, contexto, contexto textual, instrução e mensagem | `Prompt` | Monta prompt com dados financeiros e equipamentos de maior custo. |

#### Classe: BasePermissionPolicy

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ can_access(user, method, obj=None, request=None)` (abstract) | usuário, método HTTP, objeto opcional e request opcional | `bool` | Contrato para decidir se uma ação é permitida. |

#### Classe: GestorPolicy

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ can_access(user, method, obj=None, request=None)` | mesmos parâmetros do contrato | `bool` | Permite gestor/admin autenticado ou superusuário. |

#### Classe: TecnicoPolicy

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ can_access(user, method, obj=None, request=None)` | mesmos parâmetros do contrato | `bool` | Permite usuário autenticado cujo perfil seja técnico. |

#### Classe: GestorOrReadOnlyPolicy

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ can_access(user, method, obj=None, request=None)` | mesmos parâmetros do contrato | `bool` | Permite leitura a autenticados; escrita a gestor/admin ou superusuário. Nome pedido anteriormente `GestorReadOnlyPolicy` não existe literalmente. |

#### Classe: AuthenticatedNoDeleteForTecnicoPolicy

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ can_access(user, method, obj=None, request=None)` | mesmos parâmetros do contrato | `bool` | Leitura permitida a autenticados; técnico não pode DELETE; outros métodos de escrita exigem gestor/admin ou superusuário. Nome pedido anteriormente `AuthenticateAndDeleteForTecnicoPolicy` não existe literalmente. |

#### Classe: PermissionPolicyFactory

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ create(policy_name)` (classmethod) | nome registrado | `BasePermissionPolicy` | Retorna instância registrada; nome desconhecido gera `ValueError`. |
| `+ register(policy_name, policy)` (classmethod) | nome e instância de política | `None` | Adiciona ou substitui entrada do registro. |

#### Classe: Exportador

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ exportar(nome, titulo, colunas, linhas)` (abstract) | nome do arquivo, título, colunas e linhas | `HttpResponse` | Contrato abstrato para gerar uma resposta com arquivo exportado. |

#### Classe: ExportadorCSV

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ exportar(nome, titulo, colunas, linhas)` | nome, título, colunas e linhas | `HttpResponse` | Gera CSV separado por ponto e vírgula, escreve cabeçalho e linhas e adiciona BOM UTF-8. |

#### Classe: ExportadorExcel

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ exportar(nome, titulo, colunas, linhas)` | nome, título, colunas e linhas | `HttpResponse` | Cria XLSX com cabeçalho, estilos, larguras ajustadas e painel congelado. |

#### Classe: ExportadorPDF

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ __init__(orientacao='landscape')` | orientação opcional | `None` | Armazena orientação em `_orientacao`. |
| `+ exportar(nome, titulo, colunas, linhas)` | nome, título, colunas e linhas | `HttpResponse` | Gera PDF com tabela, título, data e total de registros. |

#### Classe: ExportadorFactory

| Método | Parâmetros | Retorno | Descrição |
|---|---|---|---|
| `+ registrar(formato, exportador_cls)` (classmethod) | formato e classe do exportador | `None` | Registra implementação para o formato. |
| `+ criar(formato)` (classmethod) | formato | `Exportador` | Instancia exportador registrado; formato desconhecido gera `ValueError`. |

### Tópico 12: Relacionamentos entre Classes

| Classe Origem | Tipo de Relacionamento | Classe Destino | Multiplicidade | Papel (role) | Justificativa |
|---|---|---|---|---|---|
| `Empresa` | Associação (`ForeignKey`, `CASCADE`) | `Usuario` | Empresa `1` → usuários `0..*`; usuário → empresa `0..1` | `Usuario.empresa` / `Empresa.usuarios` | O usuário pode não ter empresa. Ao excluir empresa, usuários relacionados são excluídos. |
| `Empresa` | Associação (`ForeignKey`, `CASCADE`) | `Equipamento` | Empresa `1` → equipamentos `0..*`; equipamento → empresa `1` | `Equipamento.empresa` / `Empresa.equipamentos` | Cada equipamento pertence obrigatoriamente a uma empresa; remoção da empresa propaga exclusão. |
| `Equipamento` | Associação (`OneToOneField`, `CASCADE`) | `EquipamentoLocalizacao` | Equipamento `1` → localização `0..1`; localização → equipamento `1` | `EquipamentoLocalizacao.equipamento` / `Equipamento.localizacao` | Um equipamento pode não ter localização cadastrada, mas não pode ter mais de uma. |
| `Equipamento` | Associação (`ForeignKey`, `CASCADE`) | `PlanoManutencao` | Equipamento `1` → planos `0..*`; plano → equipamento `1` | `PlanoManutencao.equipamento` / `Equipamento.planos_manutencao` | Um equipamento pode possuir vários planos; cada plano pertence a um equipamento. |
| `Equipamento` | Associação (`ForeignKey`, `CASCADE`) | `OrdemServico` | Equipamento `1` → OS `0..*`; OS → equipamento `1` | `OrdemServico.equipamento` / `Equipamento.ordens_servico` | Um equipamento pode ter várias ordens ao longo do tempo. |
| `Usuario` | Associação (`ForeignKey`, `SET_NULL`) | `OrdemServico` | Usuário `0..*` OS; OS → responsável `0..1` | `OrdemServico.responsavel` / `Usuario.minhas_os` | Responsável é opcional. Ao excluir usuário, a OS permanece sem responsável. |
| `Equipamento` | Associação (`ForeignKey`, `CASCADE`) | `Alerta` | Equipamento `1` → alertas `0..*`; alerta → equipamento `1` | `Alerta.equipamento` / `Equipamento.alertas` | Cada alerta pertence a um equipamento; remover o equipamento remove alertas relacionados. |
| `Equipamento` | Associação (`ForeignKey`, `CASCADE`) | `Sensor` | Equipamento `1` → sensores `0..*`; sensor → equipamento `1` | `Sensor.equipamento` / `Equipamento.sensores` | Um equipamento pode possuir vários sensores. |
| `Sensor` | Associação (`ForeignKey`, `CASCADE`) | `Telemetria` | Sensor `1` → leituras `0..*`; leitura → sensor `1` | `Telemetria.sensor` / `Sensor.leituras` | Cada leitura pertence a um sensor. Equipamento é alcançado indiretamente por `Telemetria.sensor.equipamento`. |
| `Sensor` | Associação (`OneToOneField` nullable, `CASCADE`) | `TrendConfig` | Sensor `1` → config específica `0..1`; config → sensor `0..1` | `TrendConfig.sensor` / `Sensor.trend_config` | A configuração pode ser por sensor ou global (`sensor=NULL`). NULL pode ocorrer em múltiplas linhas, portanto não há garantia de configuração global única. |
| `OrdemServico` | Associação (`OneToOneField`, `CASCADE`) | `HistoricoManutencao` | OS `1` → histórico `0..1`; histórico → OS `1` | `HistoricoManutencao.ordem_servico` / `OrdemServico.historico` | O OneToOne permite no máximo um histórico por OS; o registro pode ainda não existir. |
| `AbstractUser` (Django) | Herança | `Usuario` | Não aplicável | Classe base | `Usuario` herda campos e comportamento de autenticação do Django. `AbstractUser` não é um modelo de domínio criado pelo projeto. |
| `PromptBuilder` | Herança/implementação | `PromptBuilderConcreto` | Uma classe concreta no código | `PromptBuilderConcreto(PromptBuilder)` | O builder concreto implementa os métodos abstratos de construção. |
| `PromptBuilder` | Dependência de tipo | `PromptDirector` | Um builder por chamada | Parâmetro `builder` | Os métodos estáticos do Director recebem um builder e orquestram a sequência de operações. Não é relação ORM. |
| `PromptBuilderConcreto` | Dependência de criação | `Prompt` | Um produto por chamada `build()` | retorno de `build()` | O builder constrói e devolve um objeto `Prompt`; não é relação persistida. |
| `BasePermissionPolicy` | Herança | `GestorPolicy`, `TecnicoPolicy`, `GestorOrReadOnlyPolicy`, `AuthenticatedNoDeleteForTecnicoPolicy` | Uma subclasse por implementação | classe base abstrata | As políticas concretas implementam `can_access()`. |
| Políticas concretas | Registro/uso | `PermissionPolicyFactory` | Várias políticas registradas | `_policies`; `create()` | A factory mantém instâncias por chave e retorna a correspondente; não é relação ORM. |
| `Exportador` | Herança/implementação | `ExportadorCSV`, `ExportadorExcel`, `ExportadorPDF` | Uma implementação por formato | classe base abstrata | Cada exportador concreto implementa `exportar()`. |
| Exportadores concretos | Registro/uso | `ExportadorFactory` | Vários formatos registrados | `_registro`; `registrar()`/`criar()` | A factory mapeia formato para classe e instancia a classe solicitada; registro feito no pacote `exportacao.utils`. |
| `GeminiBaseView` | Herança | `GeminiChatView`, `GeminiOsAnalysisView`, `GeminiUnassignedOrdersView`, `GeminiFinanceView`, `GeminiTrendAnalysisView` | Uma view base para várias views concretas | classe base | As subclasses especializam finalidade, prompt, temperatura ou autorização. São classes de aplicação, não entidades ORM. |
| `GeminiBaseView` | Dependência de uso | `PromptConfig`, funções de contexto, funções de prompt e cliente Gemini | Uma chamada por requisição | chamadas em `post()`/`get_prompt()`/`run_gemini()` | A view obtém configuração/contexto, monta instrução e prompt e chama as funções do provedor; não há FKs entre esses componentes. |
| `GeminiBaseView` | Dependência de uso | `KpiService` | indireta, via serviços de contexto | contexto de KPIs | O contexto de IA inclui KPIs calculados com o serviço, conforme o caminho de contexto; é dependência de código, não relação persistida. |
| `KpiService` | Dependência de dados | `Equipamento`, `OrdemServico`, `HistoricoManutencao` | várias OS/históricos por cálculo | parâmetros/querysets e consultas ORM | O serviço lê entidades para calcular indicadores; a relação entre serviço e modelos não é FK. |
| `ExportadorFactory` | Dependência de criação | `ExportadorCSV`, `ExportadorExcel`, `ExportadorPDF` | formato seleciona uma classe | `_registro` | A factory instancia o exportador solicitado. |
| `ExportadorCSV`, `ExportadorExcel`, `ExportadorPDF` | Dependência de uso | dados fornecidos pelo chamador | muitos registros por exportação | parâmetros `colunas` e `linhas` | Os exportadores recebem dados já selecionados pela camada chamadora e devolvem arquivo HTTP; não representam associação de domínio persistida. |

**Observações importantes:** `Telemetria` não possui relação direta com `Equipamento`; a navegação é feita por `Sensor`. `HistoricoManutencao` é OneToOne com OS, não um-para-muitos. `on_delete=CASCADE` pode apagar dados históricos relacionados, enquanto `SET_NULL` preserva a OS sem o usuário responsável.

As relações de herança e dependência listadas acima descrevem colaboração no código. Não devem ser interpretadas como relacionamentos de banco: somente as relações explicitamente identificadas por `ForeignKey`, `OneToOneField` ou `ManyToManyField` persistem como relações ORM.