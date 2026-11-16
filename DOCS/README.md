# Documentação vigente do NanaSmart

**Revisão de organização:** 16/11/2026. Comece pelo [README do projeto](../readme.md) para instalar e executar. Esta página indica a referência atual de cada assunto; versões anteriores ficam em [old](old/README.md).

## Padrões e arquitetura

| Assunto | Documento atual |
|---|---|
| Os 12 padrões, código real, decisões e exemplos didáticos | [Verificação dos padrões GoF](docs_padroes_projeto/Verificacao_Padroes_GoF_Verdes.md) |
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

- Backend: **310 testes executados; 305 aprovados e cinco pulados** no SQLite em memória. Os pulados exigem bloqueios de linha do PostgreSQL.
- Comando: `.\.venv\Scripts\python.exe manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests gemini_api.test_order_analysis gemini_api.test_prompt_components app.test_schema --settings=app.test_settings --noinput --verbosity=1`, com `NANASMART_TEST_POSTGRES_PORT` vazio.
- Implementação: **os 12 padrões têm uso no backend**. Abstract Factory, Singleton, Composite, Decorator e Iterator receberam classes próprias e integração nesta etapa; os outros sete continuam em uso.
- Regressão: 18 testes novos cobrem as implementações, o formato dos arquivos, o texto exato dos prompts, permissões e isolamento por empresa. Os testes existentes de tendências exercitam o novo iterador.
- Frontend: 147 testes aprovados na execução anterior desta revisão; não houve mudança no JavaScript nem nos contratos HTTP nesta etapa.
- Checks: `manage.py check` sem problemas e `makemigrations --check --dry-run` sem alterações de modelos. Nenhuma migração foi gerada ou aplicada.
- Documentação: 12 padrões na ordem solicitada, 22 trechos Python correspondentes ao código e 219 links locais válidos nos 18 documentos/índices ativos conferidos após a implementação.
- Arquivamento: 28 arquivos movidos para `old`, com seus SHA-256 preservados. Os retratos históricos não são apresentados como especificação atual.

O banco de desenvolvimento não foi utilizado nessa suíte. Não foram executados o seed ou chamadas reais ao provedor de IA para validar estas implementações. Os resultados de 292 testes pertencem à etapa documental anterior, e os de 75 testes à revisão de 15/11. A implementação atual é descrita no documento oficial de padrões.
