# Histórico de alertas

Especificação vigente desde 06/11/2026.

## Evolução dos níveis na O.S. — 11/11/2026

A listagem de ordens mostra a data e hora completas da abertura, com segundos, e a última elevação de nível do alerta. Expandir essa informação na própria linha ou cartão permite consultar todas as elevações conhecidas, identificadas pelo alerta, sem abrir a O.S. O detalhe da ordem reúne as ocorrências vinculadas, incluindo recorrências, com abertura, nível inicial, elevações e normalização conhecida. O motivo de cada evento pode ser expandido. Os horários da interface usam o fuso local do dispositivo.

`Alerta.historico_niveis` preserva cada aumento do maior nível do episódio, com `nivel_anterior`, `nivel`, `ocorrido_em`, `registrado_em` e `descricao`. O instante observado vem da leitura por limite ou da análise preditiva que elevou o nível; o registro no sistema é preservado separadamente. Uma alteração sem nova análise usa o instante do registro. Repetição, reprocessamento e retorno a um pico já atingido não acrescentam eventos. O contexto inicial permanece em `dados_deteccao`.

A API da O.S. acrescenta o campo somente leitura `historico_alertas`, com o resumo de cada ocorrência e suas elevações. A primeira ocorrência também é consultada pelo vínculo antigo, sem duplicá-la. O queryset carrega as relações antecipadamente. O isolamento de empresa e a visibilidade do técnico continuam os da própria ordem.

Ordens abertas recebem os mesmos eventos na descrição, com data, hora, fuso e transição de nível. A atualização preditiva acrescenta eventos e preserva o texto anterior. Uma recorrência registra suas próprias elevações mesmo quando seu nível é inferior ao pico de outra ocorrência da O.S. Ordens encerradas preservam a descrição e o estado; o histórico consultável continua exibindo a evolução do alerta vinculado, sem abrir outra ordem.

A interface mantém a prioridade da O.S. e destaca **Criticidade do equipamento na abertura**. A criticidade atual fica nas informações técnicas. Os campos “Origem da prioridade / Herdada” e “Gravidade da condição” foram retirados da apresentação e do formulário; os campos da API permanecem compatíveis. O risco de segurança informado continua visível. Aumentar o nível do alerta não altera automaticamente a prioridade ABC da ordem.

Aplicar `python manage.py migrate` para incluir `alertas.0004_historico_niveis`. A migração é aditiva e inicia o histórico de elevações vazio para registros existentes. Nenhum horário antigo é inferido da última análise ou da descrição. Quando a sequência conhecida não explica o pico preservado, a O.S. informa que parte do histórico não está disponível, inclusive após novas elevações comprovadas.

## Responsabilidades e uso

O alerta registra uma detecção automática. A O.S. organiza responsável, prioridade, execução e conclusão. Telemetria e Tendências mostram a condição atual. Problemas identificados por uma pessoa são registrados diretamente na O.S.

O histórico é somente consulta, inclusive no painel administrativo. A lista em tabela começa nas ocorrências de maior gravidade (crítico → médio → baixo); dentro de cada nível, as mais recentes aparecem primeiro e permite filtrar busca textual, equipamento, sensor, origem, maior nível atingido e período de abertura. As exportações CSV, Excel e PDF usam exatamente os mesmos filtros e incluem todos os resultados, não apenas a página visível.

Os detalhes mostram motivo, contexto inicial, gravidade inicial e máxima, data de normalização conhecida, gráfico e tabela das leituras preservadas. Os botões levam ao sensor e à ordem exata vinculada. Ações de atendimento ficam na O.S. Nos detalhes do equipamento, o acesso ao histórico de alertas é separado da lista de ordens; sua origem é identificada por relacionamento, nunca pelo título.

## Evidência e acompanhamento

- Na abertura por limite, `dados_deteccao` preserva até 50 leituras do sensor terminando na disparadora, em ordem cronológica, além de unidade, nomes, limite e percentuais utilizados.
- Na abertura por tendência, preserva a janela de amostras efetivamente analisada, configuração, indicadores e motivo da detecção.
- O acompanhamento escreve em `dados_analise`; a evidência inicial permanece intacta. `nivel` preserva o maior nível atingido tanto por limite quanto por tendência.
- Leituras repetidas mantêm o mesmo episódio. Duas leituras normais consecutivas confirmam recuperação por limite; tendências usam a análise válida existente. Ausência de dados ou desativação não comprovam normalização.
- `data_normalizacao` registra somente normalização conhecida. A troca para outro sentido anômalo encerra o episódio de tendência anterior, mas não registra uma normalização inexistente.
- Todos os níveis por limite acionam a corretiva. Tendência anômala confirmada registra alerta; a preditiva abre automaticamente apenas com previsão futura dentro da antecedência configurada. Limite e tendência continuam independentes.
- Uma recorrência posterior à recuperação cria outro alerta. Limites podem reutilizar a ordem aberta do mesmo sensor; tendências mantêm ordem por episódio. Concluir/cancelar uma ordem não resolve o alerta nem recria outra ordem durante a mesma ocorrência.

## Dashboard e IA

“Alertas nas últimas 24h” conta aberturas na janela móvel inclusiva `[agora − 24h, agora]`, inclusive ocorrências normalizadas. Atualizar uma ocorrência antiga não a faz entrar novamente no contador. A lista mostra até seis registros, enquanto o contador usa o total no servidor. Os escopos de empresa e perfil do dashboard permanecem os existentes.

O resumo acrescenta `alertas_24h` e `alertas_recentes`; `alertas_ativos` conserva temporariamente seu significado anterior. A IA recebe ocorrências recentes identificadas como históricas e consulta as leituras para distinguir a condição atual do trabalho pendente. Não orienta resolver ou ignorar alertas.

## API e compatibilidade

`GET /api/alertas/` e `GET /api/alertas/{id}/` exigem autenticação e mantêm isolamento por empresa. Operações `POST`, `PUT`, `PATCH` e `DELETE` respondem `405` para todos os perfis. `status` continua no contrato de consulta como controle interno, sem ações de edição.

Filtros compartilhados pela lista e `/api/exportar/alertas/{formato}/`: `search`, `equipamento`, `sensor`, `origem`, `nivel`, `data_de`, `data_ate`, `equipamento__empresa` e o alias `empresa`. O filtro `status` permanece por compatibilidade. Datas usam ISO 8601; a interface converte datas locais. A ordenação usa maior gravidade primeiro (`critico`, `medio`, `baixo`), seguida por `-data_alerta, -id`. Ela é aplicada no banco antes da paginação e também nas exportações. A gravidade considera o pico histórico, inclusive em ocorrências já normalizadas. A opção `ordenacao=recentes` ordena por `-data_alerta, -id`; `ordenacao=gravidade` explicita o padrão. O histórico recolhido de Tendências usa a opção cronológica e consulta somente o sensor selecionado, sem filtro pelo período do gráfico. O campo somente leitura `ordem_servico_acessivel` informa a visibilidade da ordem vinculada conforme o perfil, sem incluir detalhes dessa ordem.

`dados_deteccao` e `data_normalizacao` são somente leitura. Registros antigos recebem `dados_deteccao.legado=true`; a migração não transforma a última análise em suposta evidência inicial. Apenas uma data `recuperado_em` já registrada é aproveitada. Alertas manuais/ignorados e vínculos existentes são preservados. A interface explica evidências indisponíveis sem inventar leituras ou horários.

Equipamentos com alertas não podem ser excluídos em cascata; a API orienta desativá-los. Excluir um sensor mantém as evidências copiadas na abertura e desabilita o acesso ao cadastro removido.

## Atualização e validação

Aplicar `python manage.py migrate` para executar `alertas.0003_historico_evidencias`. Não executar o seed para migrar uma base existente: ele continua sendo uma ferramenta destrutiva de dados de exemplo. Os novos exemplos geram alertas pela ingestão real das leituras.

```powershell
python manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests --settings=app.test_settings --noinput
python manage.py makemigrations --check --dry-run --settings=app.test_settings
node --test FrontATT/telemetria.test.cjs
node --check FrontATT/app.js
```

Os testes cobrem evidências, recuperação, recorrência, ordens, filtros/exportação, paginação, migração legada, permissões, escopo entre empresas, dashboard de 24 horas e navegação da interface. Concorrência com bloqueios de linha exige o PostgreSQL exclusivo de testes descrito no diagnóstico anterior.

Resultados desta implementação: **146 testes de backend aprovados no PostgreSQL**, sem testes pulados, e **34 testes de interface aprovados**. O template Vue 3.4.21 foi compilado e renderizado em validação de código nos cenários de limite, tendência e legado sem sensor. Os gráficos usam os intervalos reais entre amostras e as faixas preservadas na abertura. Exportações reais CSV, Excel e PDF foram testadas, incluindo motivos longos e caracteres literais; o PDF permite dividir uma linha longa entre páginas sem truncar o motivo.

A migração `alertas.0003_historico_evidencias` foi aplicada ao banco local. O PostgreSQL temporário usado pelos testes foi encerrado. A conferência visual no Chrome não foi realizada porque a ferramenta não recebeu autorização de acesso ao navegador; a validação de código não equivale a uma aprovação visual do layout.
