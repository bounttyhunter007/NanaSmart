# Documentação vigente do NanaSmart

**Revisão de organização:** 16/11/2026. Comece pelo [README do projeto](../readme.md) para instalar e executar. Esta página indica a referência atual de cada assunto; versões anteriores ficam em [old](old/README.md).

## Padrões e arquitetura

| Assunto | Documento atual |
|---|---|
| Padrões em uso, mecanismos de Python/Django e resumo dos demais avaliados | [Verificação dos padrões GoF](docs_padroes_projeto/Verificacao_Padroes.md) |
| Pacotes, componentes e implantação; arquivos editáveis e entrega no template | [Diagramas UML 2.5](Diagramas_UML_2_5/LEIA-ME.md) |
| Modelos, campos e relacionamentos do backend | [Banco de dados](DOCUMENTACAO_BANCO.md) |

## Instalação, API e demonstração

| Assunto | Documento atual |
|---|---|
| Ambiente Python e dependências | [Ambiente Python](AMBIENTE_PYTHON.md) |
| Rotas, contratos e regras de acesso | [Estrutura da API](Estrutura_API.md) |
| Aprender a consultar e testar a API | [Postman para iniciantes](Guia_Postman_Iniciante.md) |
| Seed e dados de apresentação | [Apresentação dos dados](APRESENTACAO_DADOS.md) |
| Uso dos scripts e simulador | [Guia dos scripts](../scripts/ComoUsar.md) |
| Demonstração guiada de tendências | [Roteiro de demonstração](DEMONSTRACAO_TENDENCIAS.md) |

## Regras funcionais

| Assunto | Documento atual |
|---|---|
| Criticidade de equipamentos e prioridade herdada das OS | [Priorização ABC](PRIORIZACAO_ABC.md) |
| Detecções, evidências, normalização, vínculo de OS e atualização do banco | [Histórico de alertas](HISTORICO_ALERTAS.md) |
| Critérios matemáticos, janela, amostra e abertura de OS preditiva | [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md) |
| Análise individual de uma ordem pela IA | [Análise de OS por IA](ANALISE_OS_IA.md) |
| Dashboard e gráficos | [Dashboard e medições](DASHBOARD_UX.md) |
| Telas e contratos de telemetria/tendências | [Telemetria e tendências](TELEMETRIA_UX.md) |

## Referências e entregas acadêmicas

Os arquivos abaixo têm papéis próprios e foram preservados. Diagramas e PDFs históricos não substituem os modelos atuais, a API ou as regras funcionais indicadas acima.

- [Detalhamento - Engenharia.pdf](Detalhamento%20-%20Engenharia.pdf) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [BD PI.pdf](BD%20PI.pdf) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [BancoDeDados.png](BancoDeDados.png) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [Matriz Raci.pdf](Matriz%20Raci.pdf) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [Plano de comunicação e gerenciamento de risco (1).pdf](Plano%20de%20comunica%C3%A7%C3%A3o%20e%20gerenciamento%20de%20risco%20%281%29.pdf) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [Infra_S__nome.png](Infra_S__nome.png) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [Untitled diagram-2026-09-30-133907.png](Untitled%20diagram-2026-09-30-133907.png) — material de referência acadêmica preservado; não é a especificação vigente do código.
- [Vídeo de apresentação](https://drive.google.com/file/d/1HilY-0U0K76kJO-bX18bdr9ee6VXiPfm/view?usp=sharing) — link preservado do arquivo original; o conteúdo externo não foi revalidado nesta revisão.

## Histórico

Consulte [old/README.md](old/README.md) para origem, motivo do arquivamento e integridade dos arquivos anteriores. Materiais foram arquivados por sobreposição ou divergências comprovadas, não apenas pela data ou pelo nome. Não houve exclusão permanente de documentação.

## Verificação da revisão de 16/11/2026

- Estado do backend: restaurado ao commit `89db73e`, anterior às cinco implementações extras. Não há diferenças de código da aplicação em relação àquela referência.
- Padrões mantidos: Builder, Factory Method, Adapter, Facade, Observer, Strategy e Template Method. Iterator continua sendo utilizado por mecanismos de Django/Python.
- Os 12 padrões foram analisados; nenhum considerado necessário está pendente. O guia também explica os mecanismos fornecidos pelo Django/DRF, incluindo a árvore de condições do ORM como exemplo de Composite interno, sem acrescentar classes próprias ao backend.
- Decisão conforme a análise: não acrescentar Abstract Factory, Singleton próprio, Composite, Decorator GoF próprio ou um Iterator manual apenas para completar a lista.
- Backend após a reversão: 292 testes executados, 287 aprovados e cinco pulados no SQLite em memória. Os pulados exigem bloqueios de linha do PostgreSQL.
- Comando: `.\.venv\Scripts\python.exe manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests gemini_api.test_order_analysis app.test_schema --settings=app.test_settings --noinput --verbosity=1`, com `NANASMART_TEST_POSTGRES_PORT` vazio.
- Frontend: 147 testes aprovados na revisão anterior; JavaScript e contratos HTTP não foram modificados pela reversão.
- Checks: `manage.py check` sem problemas e `makemigrations --check --dry-run` sem alterações de modelos.
- Documentação: detalha os sete padrões aplicados e os usos de Iterator e Composite pelo framework, em ordem de criação, estrutura e comportamento. Os três padrões restantes ficam apenas na tabela final. Os exemplos e links foram conferidos na reorganização documental.
- Arquivamento: 28 arquivos preservados em `old`, com seus SHA-256 conferidos. A organização documental foi mantida.

O banco de desenvolvimento não foi utilizado nessa suíte. Não foram aplicadas migrações, executado o seed ou feitas chamadas reais ao provedor de IA para validar a reversão. Os 310 testes da implementação ampliada pertencem à versão retirada; os resultados atuais correspondem ao backend restaurado.
