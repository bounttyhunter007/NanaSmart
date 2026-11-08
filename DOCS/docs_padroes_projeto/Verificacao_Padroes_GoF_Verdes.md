# Padrões GoF destacados em verde: situação no NanaSmart

**Revisado em:** 7 de novembro de 2026  
**Escopo:** somente os dez padrões verdes da imagem enviada.

A imagem é a lista do que deve ser verificado; ela não é uma ordem para implementar todos os padrões. A decisão de aplicação considera o pedido do usuário e a necessidade real do projeto.

## Resumo

| Grupo | Padrões | Resultado |
|---|---|---|
| Implementados e usados | Builder, Strategy, Observer, Factory Method, Adapter, Facade | Os seis participam de fluxos atuais; manter. |
| Recursos compartilhados pelo Django | Singleton como conceito semelhante | O framework centraliza configurações e gerencia conexões; isso não comprova um Singleton GoF para cada recurso. |
| Não usados e sem necessidade atual | Abstract Factory, Composite, Decorator | Não adicionar sem um caso de uso que justifique a complexidade. |

O código e seus pontos de uso são a evidência principal. Documentos antigos divergem entre si e estão desatualizados; não foram usados para determinar o estado atual. O histórico Git foi consultado para descrever mudanças anteriores quando permite confirmá-las. Onde não há evidência suficiente, o relatório não presume como era o código.

## Guia rápido para apresentar os padrões

Um padrão de projeto é uma solução conhecida para um problema recorrente de organização do código. Ele descreve como distribuir responsabilidades entre objetos ou componentes. Abaixo estão a ideia, uma maneira de lembrá-la e sua relação com o NanaSmart.

### Padrões usados no projeto

**Builder — montar em etapas.** Serve para construir um resultado que pode ter várias partes e combinações. Cada etapa acrescenta uma parte, e ao final o construtor entrega o resultado completo. É como montar um sanduíche escolhendo seus ingredientes. No NanaSmart, o Builder monta prompts para a IA com blocos como contexto, alertas, ordens e pergunta. Isso facilita criar prompts diferentes sem repetir toda a montagem.

**Strategy — escolher uma regra.** Serve quando há maneiras diferentes de realizar uma tarefa e todas podem ser chamadas pelo mesmo contrato. Imagine escolher uma rota de carro, a pé ou de bicicleta: o destino é o mesmo, mas a regra para chegar muda. No NanaSmart, políticas de permissão usam o mesmo método para avaliar acesso, com regras diferentes para gestores, técnicos e outros casos.

**Observer — reagir a um acontecimento.** Serve para avisar componentes interessados quando um evento ocorre, permitindo que eles executem suas próprias ações. É parecido com uma inscrição em notificações: quando há uma novidade, os inscritos são avisados. No NanaSmart, sinais do Django acionam verificações quando uma leitura de telemetria, um alerta ou outro registro é salvo.

**Factory Method — deixar um criador decidir o que produzir.** Serve para separar o código que precisa de um objeto do código que sabe construir o tipo concreto. Pense em uma oficina com criadores especializados: cada um sabe produzir seu tipo de peça. No NanaSmart, criadores de exportadores produzem o objeto adequado para CSV, Excel ou PDF; a view usa a interface comum para gerar o arquivo.

**Adapter — traduzir entre interfaces.** Serve para conectar dois componentes que esperam formatos ou formas de chamada diferentes. É como um adaptador de tomada: ele permite ligar um aparelho a uma tomada com outro encaixe. No NanaSmart, o adapter recebe instruções e histórico no formato da aplicação, converte esses dados para o formato do SDK Gemini e entrega a resposta ao sistema. Isso concentra a tradução para o serviço externo em um lugar.

**Facade — oferecer uma entrada mais simples.** Serve para apresentar uma operação de alto nível que coordena serviços ou partes de um sistema. Pense em uma recepção: você faz uma solicitação em um único lugar, e ela encaminha as etapas necessárias. No NanaSmart, a fachada prepara o contexto para a IA, reunindo os dados comuns e incluindo o resumo financeiro quando solicitado pela view.

**Singleton — controlar uma única instância.** Serve quando uma classe precisa garantir uma única instância dentro de um processo e fornecer acesso a ela. O Django já oferece pontos centralizados para recursos usados pelo projeto, como configurações e gerenciamento de conexões. A ideia de acesso compartilhado lembra Singleton, mas cada recurso tem suas próprias regras: isso não significa que exista uma única conexão com o banco para toda a aplicação. Veja os exemplos na seção 7.

### Padrões sem uso necessário no projeto

**Abstract Factory — criar uma família de objetos relacionados.** Serve quando vários objetos precisam ser criados juntos e pertencer à mesma família. Por exemplo, uma fábrica de tema claro poderia criar botão, menu e janela claros, enquanto outra criaria os mesmos componentes em tema escuro. No NanaSmart, cada exportação escolhe apenas um formato; não há uma família de produtos que precise ser criada em conjunto.

**Composite — tratar itens e grupos de forma parecida.** Serve para organizar objetos em uma árvore, permitindo que uma operação trabalhe tanto com um item individual quanto com um grupo que contém outros itens ou grupos. Uma pasta com arquivos e subpastas é uma forma simples de imaginar essa estrutura. O domínio analisado do NanaSmart não exige esse tratamento recursivo.

**Decorator — acrescentar comportamento envolvendo um objeto.** Serve para adicionar responsabilidades a um objeto por meio de outro objeto que mantém a mesma interface. Por exemplo, um serviço de envio poderia ser envolvido por um componente que registra cada envio e por outro que acrescenta criptografia. O uso de `@` em Python, por si só, não comprova esse padrão GoF. No NanaSmart, não foi encontrada uma necessidade atual dessa composição de objetos.

## Implementados e usados

### 1. Builder — construção dos prompts da IA

**Onde está:**

- [`PromptBuilder`](../../gemini_api/prompt_builder_pattern.py#L4) define os passos de construção, e [`PromptBuilderConcreto`](../../gemini_api/prompt_builder_pattern.py#L42) acumula e formata os blocos do prompt.
- [`PromptDirector`](../../gemini_api/prompt_director.py#L4) define a ordem dos passos para cada tipo de solicitação.
- As funções públicas de [`prompt_builder.py`](../../gemini_api/prompt_builder.py#L119) criam o builder e pedem ao diretor que monte o prompt.

**Como é usado:**

1. A view Gemini seleciona uma função de construção, como `build_chat_prompt`.
2. Essa função cria um `PromptBuilderConcreto`.
3. O `PromptDirector` escolhe e ordena as partes: contexto, alertas, ordens, telemetria, instruções ou pergunta.
4. O builder produz um objeto `Prompt`; a função devolve seu texto para a chamada ao Gemini.

O fluxo aparece em `build_chat_prompt`, `build_os_analysis_prompt`, `build_unassigned_orders_prompt` e `build_finance_prompt`. A view base invoca a função configurada por cada endpoint Gemini.

**Antes e agora:** no pai do commit `3b4712d` (16/09/2026), as funções montavam listas e blocos de texto diretamente. Agora, a construção incremental está separada do diretor e do produto `Prompt`.

**Decisão:** aplicado e usado; manter.

### 2. Strategy — regras de permissão intercambiáveis

**Onde está:**

- [`BasePermissionPolicy`](../../accounts/permission_policies.py#L4) define o contrato `can_access`.
- `GestorPolicy`, `TecnicoPolicy`, `GestorOrReadOnlyPolicy` e `AuthenticatedNoDeleteForTecnicoPolicy` implementam regras diferentes no mesmo arquivo.
- [`PermissionPolicyFactory`](../../accounts/permission_policies.py#L51) seleciona a política pelo nome.
- [`accounts/permissions.py`](../../accounts/permissions.py#L1) chama a fábrica dentro das permissões do Django REST Framework.

**Como é usado:** por exemplo, `IsTecnico.has_permission` pede a política `tecnico` e delega a avaliação de usuário e método HTTP para `can_access`. As outras permissões seguem o mesmo formato com políticas distintas. Assim, as regras ficam em estratégias separadas, em vez de estarem todas dentro das classes do DRF.

**Antes e agora:** no pai do commit `14fe3da` (21/09/2026), as condições de perfil e método HTTP ficavam diretamente nas permissões. Agora, as regras estão em classes com contrato comum, selecionadas pela fábrica. O commit `93156c9` registra a centralização do uso das políticas.

**Decisão:** aplicado e usado; manter.

### 3. Observer — reações a eventos de persistência

**Onde está e o que observa:**

- [`alertas/signals.py`](../../alertas/signals.py#L6): ao salvar um alerta ativo, solicita a criação/vinculação de uma ordem de serviço conforme a origem do alerta.
- [`ativos/signals.py`](../../ativos/signals.py#L13): ao salvar um equipamento, verifica se o horímetro atingiu o próximo plano e pode criar uma O.S. preditiva. O mesmo arquivo observa o pré-salvamento de O.S. sem descrição.
- [`telemetria/signals.py`](../../telemetria/signals.py#L9): após uma nova leitura de telemetria, aciona a sincronização da tendência e dos limites.

**Como é usado:** o Django emite `post_save` ou `pre_save`; funções inscritas recebem o objeto salvo e executam a reação correspondente. Os `AppConfig.ready()` registram os módulos de sinais, por exemplo [`AlertasConfig`](../../alertas/apps.py#L4), [`AtivosConfig`](../../ativos/apps.py#L4) e [`TelemetriaConfig`](../../telemetria/apps.py#L4).

**Antes e agora:** o histórico registra fluxos acionados por sinais desde maio de 2026. O estado atual mantém e amplia essas reações para alertas, equipamentos, ordens de serviço e telemetria. Não foi necessário presumir um estado anterior mais detalhado.

**Decisão:** aplicado e usado; manter. Não adicionar uma segunda implementação de Observer sobre os sinais existentes.

## Implementados nesta revisão e em uso

### 4. Factory Method — criação de exportadores por criadores concretos

**Onde está:** [`CriadorExportador`](../../exportacao/utils/creators.py#L9) declara o método abstrato `criar_exportador`. `CriadorExportadorCSV`, `CriadorExportadorExcel` e `CriadorExportadorPDF` o sobrescrevem para criar cada produto concreto. [`ExportadorFactory`](../../exportacao/utils/exporter_factory.py#L4) resolve o criador pelo formato, e os exportadores implementam a interface [`Exportador`](../../exportacao/utils/base_exporter.py#L4). A view chama a fábrica em [`exportacao/views.py`](../../exportacao/views.py#L50).

**Como é usado:** a requisição informa `csv`, `excel` ou `pdf`; o registro localiza o criador concreto, e o método sobrescrito `criar_exportador` instancia o produto. A view recebe um `Exportador` e chama o mesmo método `exportar`, independentemente do formato. O registro apenas escolhe o criador; a criação do produto ocorre pelo Factory Method sobrescrito.

**Antes e agora:** no pai do commit `3b4712d`, a view despachava para funções separadas por uma cadeia `if/elif`. Agora, ela seleciona uma classe de criador registrada, e o criador concreto decide qual exportador instanciar.

**Decisão:** Factory Method aplicado e usado; manter.

### 5. Adapter — adaptação do contrato da aplicação para o SDK Gemini

**Onde está:** [`AssistenteAdapter`](../../gemini_api/adapters.py#L8) define o contrato esperado pela aplicação; [`GeminiAdapter`](../../gemini_api/adapters.py#L29) implementa esse contrato usando o SDK Google Gemini. [`get_ai_adapter`](../../gemini_api/adapters.py#L112) fornece o adapter concreto. As funções de compatibilidade em [`cliente.py`](../../gemini_api/cliente.py#L10) delegam ao contrato, e as views continuam usando esse ponto de entrada sem importar os tipos do SDK.

**Como é usado:** a view chama `generate_content` com instrução, prompt e histórico da aplicação. O `GeminiAdapter` converte o histórico e a configuração para os tipos do SDK, executa a chamada e devolve texto e modelo usado. A view depende do contrato da aplicação; a tradução específica do Gemini fica no adapter.

**Antes e agora:** antes, as funções em `cliente.py` construíam diretamente os objetos `google.genai` e chamavam o SDK. Agora, essa tradução pertence a `GeminiAdapter`, atrás do contrato `AssistenteAdapter`; os nomes de função antigos permanecem como delegadores para preservar os pontos de uso existentes.

**Decisão:** Adapter aplicado e usado; manter. Um segundo adapter só será necessário quando houver outro provedor ou protocolo.

### 6. Facade — entrada única para montar o contexto Gemini

**Onde está:** [`GeminiContextFacade`](../../gemini_api/facades.py#L4) expõe `build_context`. Internamente, delega aos serviços [`build_base_context`](../../gemini_api/context_service.py#L151) e `get_financial_summary`. [`GeminiBaseView`](../../gemini_api/views.py#L140) usa a fachada.

**Como é usado:** cada view Gemini chama `self.build_context(user)`. A view base delega à fachada e informa se o endpoint precisa do resumo financeiro. A fachada reúne o contexto comum e, quando solicitado, acrescenta os dados financeiros. A view não precisa coordenar diretamente as consultas dos vários subsistemas.

**Antes e agora:** o histórico confirma a introdução do serviço de contexto no commit `c2115d0` (25/05/2026). Antes da fachada, a view chamava os serviços de contexto diretamente e adicionava o resumo financeiro por condição. Agora, essa coordenação está concentrada em `GeminiContextFacade`.

**Decisão:** Facade aplicado e usado; manter.

## Recurso compartilhado pelo Django

### 7. Singleton — conceito relacionado aos recursos gerenciados pelo framework

**O que é:** um Singleton GoF controla a criação de uma classe para fornecer uma única instância em determinado processo. O Django oferece alguns objetos e pontos de acesso compartilhados que lembram essa ideia. Eles têm implementações e ciclos de vida próprios, por isso não se deve chamar todo recurso do Django de Singleton GoF.

**Exemplo 1 — configurações:** ao importar `django.conf.settings`, componentes acessam um objeto de configurações disponibilizado pelo Django. Ele carrega as configurações quando necessário e serve como ponto central de acesso dentro do processo. No NanaSmart, as configurações do projeto estão em [`app/settings.py`](../../app/settings.py). Esse acesso compartilhado é semelhante à ideia de Singleton; o objeto do Django é implementado como um proxy de carregamento sob demanda.

**Exemplo 2 — banco de dados:** `django.db.connections` é um gerenciador compartilhado de conexões por nome, e `django.db.connection` é um proxy para a conexão padrão. O gerenciador cria e mantém conexões conforme o contexto de execução. Portanto, usar um ponto central de acesso **não significa uma única conexão física global**: podem existir conexões distintas por thread, contexto, nome de banco ou processo.

No NanaSmart, [`DATABASES`](../../app/settings.py#L103) configura PostgreSQL e `CONN_MAX_AGE = 60`. Isso permite ao Django manter uma conexão utilizável para reutilização por até 60 segundos, sujeita ao ciclo de vida e à verificação da conexão. Não é uma garantia de que toda requisição compartilhará a mesma conexão nem, por si só, um pool de conexões.

**Exemplo 3 — registro de aplicações e modelos:** o Django mantém um registro central, acessível por `django.apps.apps`, com as aplicações carregadas e seus modelos. A configuração [`INSTALLED_APPS`](../../app/settings.py#L33) informa quais aplicações o NanaSmart utiliza. O registro permite ao framework consultar esses componentes sem que cada parte precise construir seu próprio catálogo.

**Exemplo 4 — resolução de URLs:** o Django mantém em cache resolvedores usados para relacionar caminhos HTTP às views. Assim, o trabalho de construir o resolvedor pode ser reaproveitado dentro do processo. Esse cache é um mecanismo de reutilização, e não uma garantia de uma única instância compartilhada entre todos os servidores.

**Exemplo 5 — acesso ao cache:** o Django disponibiliza `django.core.cache.caches`, um gerenciador de caches por nome, e `cache`, um acesso ao cache padrão. São pontos centralizados de acesso; a existência dessas ferramentas no framework não demonstra, por si só, que o NanaSmart utilize cache explicitamente em algum fluxo específico. Os objetos e dados disponíveis dependem do backend e do contexto configurados.

**Onde é usado:** as consultas por `objects` e QuerySets dos modelos passam pelo ORM e pelo gerenciamento de conexões do Django. Por exemplo, [`get_user_equipment_queryset`](../../gemini_api/context_service.py#L11) consulta equipamentos por meio do ORM; as views não precisam criar uma conexão PostgreSQL manualmente a cada consulta.

**Antes e agora:** o projeto já usava esses recursos do Django. Esta revisão documenta seu funcionamento e não acrescenta uma classe Singleton própria. Uma instância por processo também não seria automaticamente única entre vários processos ou servidores.

**Como explicar na apresentação:** “O Django oferece pontos centralizados para configurações, aplicações, conexões e cache. Isso se relaciona à ideia de compartilhar recursos; cada recurso tem seu próprio ciclo de vida, e o banco pode ter várias conexões. Não precisamos criar um Singleton manual para gerenciá-los.”

## Não usados e por que não aplicar agora

### 8. Abstract Factory

Não aplicado. A fábrica atual escolhe um exportador de cada vez; CSV, Excel e PDF são formatos alternativos do mesmo tipo de produto, não famílias de objetos que precisem ser criadas em conjunto. Não criar famílias artificiais de fábricas/exportadores.

### 9. Composite

Não aplicado. As relações entre modelos encontradas não formam uma árvore recursiva em que objetos folha e composições compartilhem a mesma interface. Não há operação atual que precise tratar grupos hierárquicos e itens individuais da mesma forma.

### 10. Decorator

Não aplicado no sentido GoF. O uso de `@receiver` e de decoradores do Python/Django registra ou envolve funções; isso não demonstra uma cadeia de objetos com a mesma interface, combinados para acrescentar responsabilidades dinamicamente. Não criar wrappers de objetos sem esse requisito.

## Conclusão

Builder, Strategy, Observer, Factory Method, Adapter e Facade estão implementados e participam diretamente de fluxos do NanaSmart. O projeto também usa recursos compartilhados gerenciados pelo Django, relacionados à ideia de Singleton, sem uma implementação Singleton GoF própria para o banco. Abstract Factory, Composite e Decorator não estão aplicados, e não há necessidade atual para adicioná-los.

Esta verificação atualiza as classificações antigas com base no código vigente: distingue os seis padrões implementados no projeto, os recursos compartilhados do Django relacionados ao Singleton e os três padrões sem necessidade identificada no escopo atual.
