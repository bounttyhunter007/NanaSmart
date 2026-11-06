# Telemetria: organização da interface e tendências

Revisão: 06/11/2026. Complementa [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md). Não modifica o algoritmo de detecção ou a regra de geração automática de OS.

## Diagnóstico e decisões

| Problema anterior | Alteração |
|---|---|
| Cadastro de sensores e histórico de medições em colunas concorrentes | Abas internas Leituras, Sensores e Tendências, sem novo item lateral |
| Tabela mostrava apenas 30 itens mesmo recebendo uma página maior | Exibe a página inteira, com total real, intervalo e seletor de 20/50/100 |
| Busca de sensores prometia buscar nomes mas usava só descrição | Busca no servidor por nome, descrição e equipamento |
| Filtros por valor e data expostos numa faixa muito densa | Equipamento e sensor em primeiro plano; período e valores em seção expansível |
| Atualização silenciosa substituía leituras ignorando data e página | Atualização manual explícita, preservando o contexto e mostrando horário da consulta |
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
- Não há marcador de tempo real na nova área: a atualização é manual. O detalhe antigo do equipamento mantém seu polling existente, agora também consultando a tendência.
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
