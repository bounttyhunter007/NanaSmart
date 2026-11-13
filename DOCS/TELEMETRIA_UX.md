# Telemetria: organização da interface e tendências

## Revisão vigente de Tendências — 13/11/2026

A página de Tendências agora usa lista compacta com busca sem distinção de acentos, filtro de equipamento pesquisável e filtros por condição. O sensor de maior risco é selecionado inicialmente; clicar em outro item atualiza um único painel. Atualizações preservam a escolha. Em telas pequenas, a lista é recolhível. A seleção não altera os filtros de Telemetria.

O gráfico abre em **Ao vivo · 5 min**. A aba **Análise operacional** mostra a amostra usada pelo servidor. Prévia gráfica não confirma O.S. e permanece disponível com histórico incompleto. As explicações extensas, cards grandes e detalhe duplicado foram substituídos por situação, previsão, vínculo da O.S. e seções expansíveis de fórmula/critérios. Escala e ajuste no histórico ficam em Opções do gráfico. O teste administrativo continua em Demonstração de tendências.

**Ajustar análise** destaca histórico mínimo e antecedência da O.S., com sugestões de tempo e resumo da regra. Defaults novos: 2 h e 2 h; valores salvos são preservados. Critérios técnicos ficam em opções avançadas, com R² e persistência em percentuais.

A O.S. mostra Previsão na abertura, com evidência fixa da análise elegível, separada do acompanhamento atual. Abertura exige previsão confirmada dentro da antecedência; uma anomalia distante pode ter alerta sem O.S. As descrições de Tendências nas seções históricas abaixo foram substituídas por esta revisão. Regras completas: [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md).


Revisão: 06/11/2026.

**Organização vigente:** Tendências é uma página própria no menu lateral. Telemetria contém somente Leituras e Sensores. As decisões anteriores abaixo registram a evolução inicial; a seção “Página independente de Tendências” ao final substitui a proposta de três abas e o compartilhamento de filtros. Complementa [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md). Não modifica o algoritmo de detecção ou a regra de geração automática de OS.

## Diagnóstico e decisões

| Problema anterior | Alteração |
|---|---|
| Cadastro de sensores e histórico de medições em colunas concorrentes | Abas internas Leituras, Sensores e Tendências, sem novo item lateral |
| Tabela mostrava apenas 30 itens mesmo recebendo uma página maior | Exibe a página inteira, com total real, intervalo e seletor de 20/50/100 |
| Busca de sensores prometia buscar nomes mas usava só descrição | Busca no servidor por nome, descrição e equipamento |
| Filtros por valor e data expostos numa faixa muito densa | Equipamento e sensor em primeiro plano; período e valores em seção expansível |
| Atualização silenciosa substituía leituras ignorando data e página | Leituras e Sensores têm atualização manual; Tendências atualiza silenciosamente a cada 30 segundos, preservando contexto e página |
| Identificação de sensor/equipamento dependia de listas parciais carregadas por outras telas | Nomes e unidade retornados na própria API de leituras; cadastro informa equipamento |
| Controles técnicos apareciam para quem não podia salvar | Técnico consulta; gestor/admin recebem ações de escrita; global exclusiva de admin |
| Direção estável aparecia como decrescente no dashboard | Rótulo com três direções; painel resumido mostra apenas anomalias confirmadas |
| Detalhe do equipamento não buscava a tendência ao trocar sensor | Consulta na seleção e junto da atualização periódica desse detalhe |

## Navegação e comportamento

**Leituras** é a entrada padrão. Tabela cronológica, mais recentes primeiro, com equipamento/sensor, valor com unidade e data/hora. IDs internos saem da visualização principal. Registrar/editar é restrito a gestor/admin; exclusão continua exclusiva de admin. Filtros adicionais aceitam mínimo zero e convertem datas locais para ISO com fuso. Intervalos invertidos são explicados antes da requisição.

**Sensores** mostra cards com nome, equipamento, tipo legível, estado ativo/inativo e limite superior com unidade. Busca por texto é aplicada pelo botão/Enter; seletores aplicam seus filtros imediatamente. Cada card acessa equipamento e, se ativo, a tendência. Edição e exclusão respeitam os perfis existentes. A tela não inventa última leitura nem condição de risco no cadastro.

**Tendências** consulta todos os sensores ativos visíveis (`all=true`) e permite filtrar por equipamento, sensor e condição. Cards de resumo clicáveis representam:

- Anomalia confirmada: `is_anomalous=true`, com análise ativa e dados suficientes.
- Sem tendência anormal: análise válida sem anomalia configurada; não significa equipamento livre de risco por limite.
- Aguardando dados: falta quantidade ou duração mínima.
- Análise desativada: configuração efetiva inativa.

Os cards resumem o equipamento/sensor selecionado, antes do filtro de condição. Durante a carga/erro mostram traços em vez de zero. A lista apresenta risco somente para anomalias confirmadas e não confunde movimentos em sentidos não configurados com alertas operacionais. Sensores com cadastro inativo ficam fora do endpoint de tendências e continuam na aba Sensores.

**Ver análise** abre um painel na própria página, com rolagem até ele. Mostra explicação da condição, gráfico de toda a amostra (posições horizontais por tempo real), valor mínimo/máximo, horários inicial/final, direção, quantidade/duração observadas versus mínimas, projeção e vínculos com alerta/OS. R², persistência, inclinação e origem da configuração ficam em seção expansível. O gráfico representa leituras observadas, sem desenhar uma previsão como se fosse medição. Não há projeção inferior e a projeção superior não promete data de quebra.

A consulta não cria alertas nem OS: os efeitos continuam na ingestão ou no comando periódico. Caso haja anomalia calculada sem alerta ativo vinculado, a interface informa essa diferença. O painel acessa o equipamento e suas ordens. O resumo do dashboard abre Tendências no contexto do sensor clicado.

## Configurações

Gestor/admin abrem **Configurar** na lista ou **Configurar análise** no detalhe. A mesma integração existente salva os critérios por sensor; quando herdados, os valores efetivos vêm do backend e o formulário avisa que salvar cria uma específica. Consistência, persistência e sensibilidade foram agrupadas em configurações avançadas. Após salvar, a aba atual e o detalhe aberto são atualizados.

Administrador dispõe de **Configuração global** na aba Tendências. O formulário avisa expressamente que a alteração afeta sensores de todas as empresas que a herdam, mesmo com uma empresa selecionada no filtro. O CRUD consulta configurações globais em ordem decrescente de id e edita a mais recente; se não houver global, permite criá-la com os defaults do modelo. Não foram removidas configurações globais legadas. Respostas atrasadas de abertura de configuração não substituem o sensor selecionado mais recentemente.

## Filtros, paginação e estados

- Equipamento é contexto compartilhado das abas. Sensor aplica-se a Leituras/Tendências. Ao trocar equipamento, limpar sensor; ao filtrar ou mudar de aba, voltar à primeira página e fechar detalhe anterior.
- Leituras e Sensores usam paginação do servidor (`limit`, `offset`, `count`). Tendências mantém o contrato de array existente e pagina localmente o resultado completo. As contagens consideram todos os resultados correspondentes, não só a página visível.
- Cada aba busca apenas sua coleção. Atualizar também recarrega opções de filtro; opções percorrem todas as páginas da API em vez de supor que `limit=999` sempre devolve tudo.
- A mudança de empresa limpa equipamento/sensor, opções, resultados e detalhe anteriores. Empresa é filtrada no servidor, sempre intersectando as permissões do usuário. Respostas antigas de resultados/opções são descartadas por identificador de requisição.
- Carregamento, falha e ausência de resultados têm mensagens distintas. Erro de opções é separado do erro da coleção. Exclusão do último item de uma página retorna à última página válida.
- Leituras e Sensores têm atualização manual. Tendências informa atualização automática a cada 30 segundos e horário da consulta. O detalhe antigo do equipamento mantém seu polling existente, também consultando a tendência.
- Estilos usam as cores existentes, grade de cards adaptável e tabela com rolagem horizontal em telas estreitas. Controles têm rótulos, foco visível e botões com estado pressionado nas abas/cards. Escape fecha primeiro configuração, depois o detalhe da análise.

## API e compatibilidade

Alterações aditivas, sem migração de banco:

- Sensor retorna `equipamento_nome` somente leitura; busca textual passa a incluir nome e equipamento; ordenação estável por nome/id.
- Leitura retorna `sensor_nome`, `equipamento_nome`, `unidade_medida` somente leitura. Novo filtro `sensor__equipamento__empresa`; ordenação por timestamp/id decrescentes.
- Tendências aceita `empresa_id` para limitar os sensores antes dos cálculos. Continua limitado à empresa do gestor/técnico, mesmo se pedirem outra empresa. Mantém array e consulta individual existentes.
- Configurações aceitam `sensor__isnull=true` e são listadas por id decrescente. Visibilidade global continua exclusiva de admin.

A aba possui estado próprio e não substitui listas compartilhadas usadas por dashboard, formulários e exportações. Endpoints e permissões de escrita existentes foram preservados.

## Validação

- Sete testes de frontend executam o `setup` real com Vue/HTTP simulados: filtros de empresa/equipamento/sensor, mínimo zero, paginação completa, validação de intervalos, resposta atrasada, quatro condições e paginação local, busca de cadastro, opções em múltiplas páginas e retorno após exclusão da última linha.
- Cinco cenários adicionais de API verificam busca por nome/equipamento, nomes/unidade na leitura, filtros entre empresas, escolha da global mais recente e bloqueio de edição por técnico.
- Suíte explícita Django: 124 testes descobertos, 121 aprovados, três testes de concorrência ignorados no SQLite. A lógica de bloqueios não foi alterada e a suíte PostgreSQL não foi repetida nesta entrega.
- Sintaxe JavaScript válida; template completo compilado com o compilador oficial Vue 3.4.21, sem erros; modelos e migrações sem divergências; diff sem erros de whitespace.
- Validação visual pendente: o navegador recusou a abertura do arquivo local por política de URLs. Não foram feitas capturas nem afirmada aprovação visual. O compilador Vue foi instalado apenas em `.venv/frontend-validation`, fora dos arquivos versionados e sem alterar dependências de produção.

Comandos na raiz:

```powershell
node --test FrontATT/telemetria.test.cjs
node --check FrontATT/app.js
python manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests --settings=app.test_settings --noinput
python manage.py makemigrations --check --dry-run --settings=app.test_settings
```

Conferência manual restante: abrir o frontend com a API atualizada; navegar pelas três abas como gestor/admin e técnico; testar tema claro/escuro, largura de celular, mais de uma página, limpeza de filtros, ausência de dados e edição de configuração. Não executar geração de dados destrutiva para essa conferência.

Limitação conhecida: tendências ainda calcula e devolve todas as análises visíveis antes da paginação local; para volumes elevados, a evolução adequada é paginação/cálculo em lote no backend. Esta entrega não introduz processamento em background ou dados simulados.

## Acompanhamento recente e escala (10/11/2026)

Dashboard, Telemetria e o gráfico principal do sensor em Tendências usam o componente `LiveChart`. Na página Tendências, equipamento/sensor ficam fixados pela seleção da página, sem repetir os seletores dentro do gráfico. Leituras e ajuste visual são atualizados por consulta a cada 5 segundos, sem cache. A lista e as evidências operacionais mantêm o monitoramento de 30 segundos; a amostra usada pelo servidor continua disponível nos detalhes do cálculo.

O modo inicial “Ao vivo” exibe até 60 leituras dentro dos últimos 5 minutos em relação à última medição. Ao receber novas leituras, a janela descarta as antigas e recalcula a inclinação da amostra exibida. Isso evita misturar meses/horas do seed com poucos segundos de coleta recente. O horário e a contagem de novas medições distinguem consulta sem novidade de chegada de dados. Pausar, ocultar a página, trocar sensor/empresa e desmontar continuam interrompendo ou invalidando consultas conforme o contexto. Não se fabricam pontos nem horários ao esperar novas medições.

A escala padrão “Acompanhar variação” considera dados e projeção, com margem e precisão decimal adaptadas. Limites fora do intervalo visível aparecem identificados abaixo, sem linhas posicionadas artificialmente na borda. “Incluir todos os limites” oferece a escala geral. No modo focado, o desktop usa mais largura para as curvas; os valores dos limites ficam nas legendas abaixo. As janelas maiores continuam disponíveis para consultar histórico.

Dois rótulos discretos junto às curvas mostram a última leitura em azul e o valor no fim da projeção em roxo, com “≈” e o tempo à frente (por exemplo, “+30 s”). A precisão acompanha a escala. Os rótulos se afastam quando necessário em telas estreitas ou curvas horizontais; os demais pontos mantêm os valores disponíveis ao passar o mouse ou selecionar. Sem projeção, aparece apenas a última leitura.

## Ajuda expansível na aba Tendências

Adicionada uma caixa informativa **Como funcionam as tendências?**, antes dos cards de resumo. Usa `details`/`summary` nativos: inicia fechada, abre/fecha por clique ou teclado e volta fechada ao sair e retornar à aba. O conteúdo é estático e sua abertura não consulta a API nem altera configurações.

O guia cobre o fluxo automático, seleção de amostra, quantidade e duração mínimas, sensibilidade com limiares reais, persistência, R², sentidos anormais, todos os campos de configuração e seus defaults, prioridade entre específica/global/padrão e permissões. Explica os quatro estados, projeção e risco, vínculos e ciclo do episódio/OS, e apresenta quatro exemplos: aumento consistente, redução configurada, amostra curta e pico isolado. Diferencia consulta de processamento operacional e tendência de alerta por limite.

A caixa usa cores do tema existente, tabela com rolagem horizontal, exemplos em duas colunas no desktop e uma em telas menores, foco visível e sinal de expandir/recolher. Nesta alteração não foram modificados algoritmo, API ou dados. Verificação: compilação do template completo com Vue 3.4.21 e checagem de whitespace; sem nova validação visual em navegador.


## Atualização automática e visibilidade de novas anomalias

Revisão adicional de 06/11/2026:

- Um único timer de 30 segundos acompanha tendências enquanto houver sessão autenticada. O ciclo não consulta com a página oculta nem sobrepõe outra consulta de monitoramento; ao voltar à página, tenta atualizar imediatamente. Timer é encerrado no logout/desmontagem e reiniciado, sem acumular, no login.
- Com Telemetria → Tendências aberta, consulta `all=true` e atualiza lista, resumo e detalhe silenciosamente. Preserva equipamento, sensor, condição, tamanho e página. Se o número de resultados diminuir e invalidar a página, usa a última página existente. Não fecha a ajuda, não dispara loading da lista e não reabre o detalhe.
- Nas outras telas, consulta apenas a lista de tendências atípicas e extrai anomalias confirmadas para o resumo do dashboard e contador da navegação. O contador representa a empresa selecionada inteira, independentemente do filtro de equipamento/sensor dentro de Telemetria. Também fica disponível para técnicos, com a mesma visibilidade de dados da API.
- A primeira consulta de uma sessão/empresa é a referência e não dispara aviso retroativo. Novos sensores/sentidos anormais ou um novo episódio identificado por outro alerta ativo geram um aviso discreto na área de conteúdo. Leituras repetidas da mesma condição não repetem o aviso; a passagem de uma análise ainda sem alerta para o mesmo episódio já vinculado não é uma nova condição.
- O aviso acumula novas condições observadas desde a referência/última dispensa, podendo incluir condições que já recuperaram. O texto identifica esse período. **Ver anomalias** é uma ação explícita: abre Tendências, limpa filtros de equipamento/sensor, filtra anomalias atuais e dispensa o aviso. **Dispensar** apenas esconde o aviso. Não existe navegação automática, modal espontâneo, som ou notificação do sistema.
- Falhas de atualização preservam a última lista, contador e horário, com aviso de que a informação pode estar desatualizada, botão de nova tentativa e repetição no próximo ciclo. Sucesso limpa esse erro.
- Logout e troca de empresa limpam referência/aviso/contador. Respostas antigas são rejeitadas por contexto de sessão/empresa e versão da requisição. Uma consulta manual mais recente prevalece sobre polling pendente. Resultado de polling não substitui resultados de uma aba para a qual o usuário acabou de navegar.
- O backend não foi alterado: a detecção e os efeitos operacionais continuam automáticos na ingestão/rotina; o timer só consulta resultados. O intervalo é de até 30 segundos em condições normais, acrescido do tempo de resposta; não é streaming nem garantia de atualização em segundo plano.

Validação adicional: 14 testes de frontend aprovados (sete anteriores e sete novos), incluindo cadência/limpeza de timers, preservação de página e detalhe, deduplicação de avisos, falha e recuperação, sobreposição e página oculta, logout, troca de empresa e corrida com atualização manual. Template completo compilado com Vue 3.4.21; sintaxe JavaScript e whitespace verificados. Sem mudanças de banco ou API e sem nova conferência visual no navegador.


## Informativo em linguagem simples e fórmulas explicadas

Revisão de 06/11/2026: reescrito o guia expansível para pessoas sem conhecimento de estatística, mantendo-o fechado por padrão. O texto começa pela diferença entre valor atual e direção da mudança. Explica alerta, ordem de inspeção, sensibilidade, persistência e R² com palavras do cotidiano. A descrição inicial da aba e as explicações dos estados no detalhe também foram simplificadas.

O exemplo central usa temperatura de 60 °C às 13h, 70 °C às 14h e 80 °C às 15h, com limite ilustrativo de 100 °C. Mostra as contas `(80 − 60) ÷ 2 = 10 °C/h` e `(100 − 80) ÷ 10 = 2 h`, chegando à estimativa condicional de 17h. O texto distingue a conta intuitiva entre extremos, válida para esse exemplo regular, da regressão real sobre todas as leituras. Explica que 2 horas recebe risco crítico pela regra vigente, sem afirmar certeza ou probabilidade de falha.

Exemplos adicionais mostram temperatura constante, perda de pressão, pico com persistência de 25% e três leituras em somente dois minutos. A configuração sugere um exemplo coerente de 7 leituras a cada 10 minutos cobrindo uma hora. As fórmulas exatas da inclinação/regressão, projeção e R² ficam em uma segunda seção expansível, com legenda para tempo, valor, médias e símbolo de soma. Não são necessários MathJax, imagens ou serviços externos. R² de 0,8 é explicitamente diferenciado de 80% de chance de quebra.

Mantidos os critérios reais: suficiência por quantidade e duração, limiar por sensibilidade, persistência, ajuste e sentido configurado; projeção só para limite superior em crescimento; efeitos automáticos na ingestão/rotina; consultas automáticas da tela a cada 30 segundos. A alteração é de conteúdo/apresentação, sem mudar algoritmo, API ou banco. Validação: template completo compilado com Vue 3.4.21 e `git diff --check`, sem erros; sem nova validação visual no navegador.


## Página independente de Tendências

Revisão solicitada em 06/11/2026. A organização vigente substitui a incorporação de Tendências à Telemetria:

- Menu lateral **Telemetria** abre apenas Leituras/Sensores. Menu lateral **Tendências** abre a nova página, com título e contexto próprios. O contador de anomalias foi movido para Tendências.
- Estado `trendPage` separado de `telemetry`: equipamento, sensor, condição, tamanho/página, resultados, carga, erros, horário e detalhe não são compartilhados. O seletor de equipamento da Telemetria não restringe nem inicializa a página de Tendências; a seleção da nova página também não altera a Telemetria. Cada uma preserva seus próprios filtros ao navegar.
- No topo de Tendências, uma caixa compacta concentra **Equipamento**, **Sensor** e **Limpar seleção**. O padrão é acompanhar todos, sem exigir seleção. Ao escolher equipamento, limpar apenas o sensor da página e restringir suas opções aos sensores ativos desse equipamento. Opções são derivadas da resposta completa de tendências e ordenadas pelo nome, sem requisições adicionais de cadastro. Se uma seleção deixar de existir nos dados, ela continua explicitamente identificada como indisponível, sem parecer que “Todos” está selecionado.
- Os quatro cards já existentes filtram condição, evitando um terceiro seletor redundante. O card ativo informa como removê-lo e há botão **Mostrar todas as condições**. A lista mantém paginação própria de 20/50/100 itens.
- Gráfico, evidências, configurações por sensor/global e guia expansível em linguagem simples foram movidos integralmente para a nova página. A ajuda fica após a lista/detalhe, fechada por padrão, deixando a seleção e os resultados em primeiro plano.
- Atualização automática de 30 segundos passou a consultar todos os resultados quando `view=tendencias` e atualizar apenas o estado dessa página. O resumo do dashboard e avisos continuam funcionando em outras telas. Uma consulta de Telemetria em andamento não substitui ou bloqueia a consulta da página de Tendências. A atualização preserva seus filtros, página e detalhe.
- Atalhos explícitos (card do dashboard e botão Tendência do sensor) abrem a página já no equipamento/sensor clicado. Esse contexto só é transferido pela ação explícita, sem alterar os filtros salvos em Telemetria. **Ver anomalias** no aviso abre a página com equipamento/sensor livres e condição anormal selecionada.
- Trocar empresa limpa os contextos das duas páginas e invalida suas consultas pendentes separadamente. Logout limpa os dois estados. A configuração global continua exclusiva de administrador e o técnico continua somente consultando.

Sem mudança de API, algoritmo ou banco. Não é necessária nova migração. Validação: **18 testes de frontend aprovados**, incluindo quatro regressões adicionais para independência entre páginas, opções de sensor por equipamento, atalhos intencionais e acesso pelo menu sem a antiga aba. Template completo compilado com Vue 3.4.21, sintaxe JavaScript e whitespace sem erros. Sem nova validação visual no navegador.


## Gráfico e apresentação guiada

Implementados gráfico de um único sensor selecionado, linha de limite superior, verificações de critérios calculadas no backend e ajuste rápido de duração no formulário. Todos os equipamentos mantém a visão geral sem múltiplos gráficos. A seleção de equipamento com um único sensor passa a selecioná-lo automaticamente; com vários, continua exigindo escolha explícita.

A área expansível **Apresentação guiada · teste de tendência**, exclusiva de admin, cria dados identificados como [DEMO] em equipamento/sensor próprios e usa a ingestão real. A primeira fase usa sete leituras a cada dez segundos, mínimo de um minuto e acompanha alerta/OS. Também há fases de ultrapassagem/recuperação e cenários de estabilidade/pico. O gráfico é consultado a cada dois segundos durante a demonstração; a lista geral mantém seu monitor de trinta segundos. Critérios, fórmulas, diferenças entre observação e consulta, permissões, API, migração, limitações e roteiro estão em [Demonstração de tendências](DEMONSTRACAO_TENDENCIAS.md).
