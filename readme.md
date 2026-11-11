# NanaSmart

Plataforma web para gestão de ativos e manutenção industrial. O projeto reúne uma API Django REST Framework e um frontend Vue 3 servido como arquivos estáticos, sem etapa de build.

## Funcionalidades

- Cadastro de empresas, usuários, equipamentos, tipos de equipamento e planos de manutenção.
- Separação de dados por empresa e permissões por perfil: administrador, gestor e técnico.
- Telemetria por sensor, alertas por limites configuráveis e análise de tendências.
- Ordens de serviço preventivas, corretivas e preditivas, com prioridade ABC herdada na abertura e histórico de revisões justificadas.
- Painéis com indicadores de manutenção, exportações CSV/Excel/PDF e integração opcional com Google Gemini.
- Frontend em `FrontATT/`, incluindo dashboard, gestão operacional e chat de IA.

A fila de O.S. mostra abertura e última elevação de nível com data e hora completas. Expanda a elevação para consultar os demais horários na própria lista. O detalhe da O.S. reúne o histórico dos alertas e suas recorrências, mantendo a criticidade do equipamento na abertura. Após atualizar, execute `python manage.py migrate` para incluir o registro de elevações. Regras e tratamento de horários antigos: [Histórico de alertas](DOCS/HISTORICO_ALERTAS.md#evolução-dos-níveis-na-os--11112026).

As regras de tendências, configurações de persistência, geração antecipada de OS e critérios de aceitação estão em [Identificação de tendências](DOCS/IDENTIFICACAO_TENDENCIAS.md). Após atualizar o código, execute `python manage.py migrate` para incluir os novos critérios de configuração.

A área **Telemetria** possui abas **Leituras** e **Sensores**. **Tendências** tem uma página própria no menu lateral, com seleção independente de equipamento/sensor, paginação e configuração de análise. O administrador também pode editar a configuração global. A página inclui um gráfico para o sensor selecionado e uma demonstração guiada de aproximadamente um minuto, exclusiva de admin. Consulte o [roteiro de demonstração de tendências](DOCS/DEMONSTRACAO_TENDENCIAS.md). Decisões de UX, compatibilidade da API e validações: [Telemetria e tendências no frontend](DOCS/TELEMETRIA_UX.md).

## Requisitos

- Python compatível com Django 5.2: 3.10 a 3.14; para novas instalações, prefira 3.13. Python 3.15 não é suportado por esta versão do Django.
- PostgreSQL acessível localmente.
- Node.js somente para a validação opcional de sintaxe JavaScript; o frontend não precisa de build.
- Uma chave do Google Gemini somente para usar os recursos de IA.

## Configuração local no Windows

No PowerShell, na pasta do projeto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

O comando de criação pressupõe Python 3.13 instalado. Um `.venv` já existente com Python compatível pode ser reutilizado sem recriação. Confira `python --version` e `python -c "import sys; print(sys.executable)"` após ativar. Use `python -m pip` para instalar no mesmo interpretador da aplicação. A matriz de versões está na [documentação oficial do Django](https://docs.djangoproject.com/en/5.2/faq/install/#what-python-version-can-i-use-with-django).

Se estiver no ambiente `venv` com Python 3.15 e já existir `.venv` compatível neste projeto, execute `deactivate` e depois `.\.venv\Scripts\Activate.ps1`. O ponto no nome distingue os dois ambientes. Não recrie um ambiente existente usando outra versão do Python; crie uma pasta nova ou reutilize a compatível.

O `requirements.txt` mantém os pacotes usados diretamente pelo projeto e deixa o pip resolver suas dependências. O SDK Gemini usado é `google-genai`; a pilha legada `google-generativeai`/gRPC foi removida. O driver PostgreSQL é apenas `psycopg2-binary`, evitando a instalação simultânea de dois pacotes que fornecem o mesmo módulo. `FrontATT/requirements.txt` referencia a lista principal. Diagnóstico de instalação e validações: [Ambiente Python e dependências](DOCS/AMBIENTE_PYTHON.md).

Configure um banco PostgreSQL chamado `manutencao`. As credenciais e o host do banco são definidos em `app/settings.py`; ajuste-os para o seu ambiente antes de executar o projeto.

Para recursos Gemini, defina `GEMINI_API_KEY` no ambiente antes de iniciar o servidor. Sem a chave, os endpoints que dependem do Gemini não estarão disponíveis.

Prepare o banco e crie um administrador:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Opcionalmente, gere dados de demonstração usando o seed descrito abaixo.

## Iniciar a aplicação

O frontend está configurado para acessar a API em `http://127.0.0.1:9000`. Inicie o backend nessa porta:

```powershell
python manage.py runserver 127.0.0.1:9000
```

Abra `FrontATT/index.html` no navegador. A API e as interfaces de documentação ficam disponíveis em:

| Recurso | Endereço |
|---|---|
| API | `http://127.0.0.1:9000/api/` |
| Swagger UI | `http://127.0.0.1:9000/api/schema/swagger-ui/` |
| ReDoc | `http://127.0.0.1:9000/api/schema/redoc/` |
| Administração Django | `http://127.0.0.1:9000/admin/` |

Para validar a documentação OpenAPI e detectar erros ou avisos na geração:

```powershell
python manage.py spectacular --settings=app.test_settings --validate --fail-on-warn --file .venv/openapi.yml
python manage.py test app.test_schema --settings=app.test_settings
```

A demonstração de tendências documenta separadamente a criação (HTTP 201), a consulta e as ações de avanço/parada/troca de fase (HTTP 200). Os formatos de entrada e saída, tipos dos campos calculados e nomes compartilhados das opções de prioridade e criticidade são verificados pelos testes do schema.

Se mudar a porta do backend, atualize também a constante `BASE` em `FrontATT/app.js`.

## Dados de demonstração

O script `scripts/seed_db.py` cria empresas, usuários, tipos de equipamento, ativos, sensores, leituras históricas, ordens, alertas, configurações de tendência e prompts Gemini.

**Atenção:** o seed começa apagando dados de várias tabelas, incluindo empresas e usuários que não sejam superusuários. Não execute contra um banco que contenha dados que queira preservar. O modo `--clean-only` também apaga dados; ele apenas não repovoa o banco.

```powershell
# Padrão: 2 empresas, 10 equipamentos por empresa e 120 dias de histórico
python scripts/seed_db.py

# Exemplo com parâmetros personalizados
python scripts/seed_db.py --empresas 5 --equipamentos 30 --days 60

# Apaga os dados gerenciados pelo seed, sem repopular
python scripts/seed_db.py --clean-only
```

| Opção | Padrão | Efeito |
|---|---:|---|
| `--empresas` | `2` | Quantidade de empresas criadas |
| `--equipamentos` | `10` | Equipamentos criados por empresa |
| `--days` | `120` | Dias de histórico de telemetria |
| `--clean-only` | desativada | Limpa os dados gerenciados pelo seed e encerra |

Em uma base limpa, o seed cria `admin` com senha `admin` caso esse usuário ainda não exista. Usuários de demonstração recebem a senha `123`. Em bases existentes, não presuma que a senha do superusuário seja `admin`.

## Simulação de telemetria

O simulador `scripts/simulador_realtime.py` grava leituras para sensores ativos. Por padrão, executa continuamente com intervalos aleatórios entre 1 e 3 segundos; encerre com `Ctrl+C`.

```powershell
python scripts/simulador_realtime.py
python scripts/simulador_realtime.py --cycles 50 --interval-min 0.5 --interval-max 1.0
python scripts/simulador_realtime.py --sensor 1 2 --dry-run --debug
python scripts/simulador_realtime.py --equipamento 4 5 --seed 42
```

`--dry-run` não grava leituras. `--sensor` e `--equipamento` limitam quais sensores serão simulados. Consulte `python scripts/simulador_realtime.py --help` para todas as opções.

O script `scripts/stress_telemetry.py` envia leituras em paralelo para testar a API. Ele precisa do servidor rodando e de um token válido:

```powershell
python scripts/stress_telemetry.py --help
```

## Testes e verificações

Para validar o projeto sem acessar o PostgreSQL de desenvolvimento, use o banco descartável configurado para testes:

```powershell
python manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests --settings=app.test_settings --noinput
python manage.py check --settings=app.test_settings
python manage.py makemigrations --check --dry-run --settings=app.test_settings
node --check FrontATT/app.js
node --test FrontATT/telemetria.test.cjs
```

As migrações do banco são versionadas. Antes de atualizar uma base já existente, consulte o procedimento de compatibilidade na [especificação de alertas e O.S.](DOCS/FLUXO_ALERTAS_ORDENS_SERVICO.md#atualização-do-banco-e-compatibilidade). A descoberta padrão de testes pode omitir `gemini_api.tests`; o comando acima o inclui explicitamente.

```powershell
python manage.py check
python manage.py test
```

Para executar um conjunto específico, informe o app ou módulo, por exemplo `python manage.py test telemetria.test_trend_analysis`. O Django cria um banco de teste separado. Se informar que esse banco já existe, não o apague sem confirmar que não está sendo usado.

## Autenticação e acesso

O login da API recebe usuário e senha e retorna tokens JWT:

```http
POST /api/auth/login/
Content-Type: application/json
```

```json
{"username": "seu_usuario", "password": "sua_senha"}
```

Envie o token de acesso nas chamadas autenticadas:

```http
Authorization: Bearer SEU_TOKEN
```

Os perfis têm escopos diferentes. Administradores têm acesso global; gestores administram os dados da própria empresa; técnicos acessam os recursos operacionais permitidos e suas ordens atribuídas ou sem responsável. A API aplica isolamento por empresa nos conjuntos de dados.

## Fluxos automáticos

- Leituras de telemetria podem criar ou atualizar alertas de acordo com os limites configurados no sensor.
- Alertas operacionais podem ser associados a ordens de serviço; alertas gerados pela análise de tendência usam um fluxo preditivo próprio.
- A análise de tendências pode recomendar intervenção, gerar alerta e criar ou atualizar a ordem preditiva correspondente.
- Alterações de horímetro são comparadas com os planos ativos do equipamento para avaliar a necessidade de manutenção.
- A prioridade ABC de novas ordens copia a criticidade do equipamento na abertura. Alterações posteriores só afetam novas OS; gestor/admin pode ajustar ordens abertas com justificativa e histórico. Critérios são validados por empresa. Consulte [Priorização ABC](DOCS/PRIORIZACAO_ABC.md).

Alertas são um histórico automático de ocorrências, sem cadastro, edição, exclusão ou baixa manual na API/interface. Cada registro preserva as evidências da abertura e permite consultar suas leituras e a O.S. vinculada. Problemas identificados por pessoas entram diretamente em uma O.S. O dashboard mostra novas ocorrências das últimas 24 horas, inclusive já normalizadas.

Alertas por limite são separados por sensor, preservam o maior nível do episódio e registram a normalização após duas novas leituras normais consecutivas, sem encerrar a O.S. Recorrências podem reutilizar uma ordem ainda aberta do mesmo sensor. Tendências preservam sua janela inicial de análise e maior gravidade. Uma ordem concluída ou cancelada não é recriada durante a mesma ocorrência.

Funcionamento, filtros, compatibilidade e migração estão em [Histórico de alertas](DOCS/HISTORICO_ALERTAS.md). O [diagnóstico anterior](DOCS/FLUXO_ALERTAS_ORDENS_SERVICO.md) permanece como referência histórica.

Os detalhes de parâmetros e respostas estão documentados no Swagger e nos serializers da API.

## Principais rotas

Use o Swagger para consultar a lista completa, filtros, permissões e formatos. Os principais grupos de endpoints são:

| Grupo | Prefixo |
|---|---|
| Autenticação e perfil | `/api/auth/` |
| Empresas e usuários | `/api/empresas/`, `/api/usuarios/` |
| Equipamentos, tipos e criticidade | `/api/equipamentos/`, `/api/tipos-equipamento/`, `/api/historico-criticidade/`, `/api/criterios-criticidade/` |
| Planos e ordens de serviço | `/api/planos-manutencao/`, `/api/ordens-servico/`, `/api/historico/` |
| Sensores, leituras e tendências | `/api/telemetria/` |
| Alertas e dashboards | `/api/alertas/`, `/api/dashboards/` |
| Gemini e prompts | `/api/gemini/` |
| Exportações | `/api/exportar/` |

## Estrutura do repositório

| Caminho | Responsabilidade |
|---|---|
| `app/` | Configurações e roteamento do Django |
| `accounts/`, `authentication/` | Empresas, usuários, autenticação e permissões |
| `ativos/` | Equipamentos, tipos, criticidade, localização e planos |
| `manutencao/` | Ordens, histórico, prioridades e dashboards |
| `telemetria/`, `alertas/` | Sensores, leituras, tendências e alertas |
| `gemini_api/` | Integração com Gemini e configurações de prompts |
| `exportacao/` | Relatórios CSV, Excel e PDF |
| `scripts/` | Seed, simulador e teste de carga |
| `FrontATT/` | Interface web Vue 3, HTML e CSS |
| `DOCS/` | Documentação complementar do projeto |

## Solução de problemas

- **`Failed to fetch` no login:** confirme que `manage.py runserver 127.0.0.1:9000` está rodando e que `BASE` em `FrontATT/app.js` aponta para a mesma porta.
- **Erro de conexão com PostgreSQL:** confira se o serviço está ativo, se o banco `manutencao` existe e se os dados em `app/settings.py` estão corretos.
- **Erro `401`:** confira usuário e senha ou faça login novamente para obter um token válido.
- **Erro `403`:** a conta autenticada não tem permissão para a operação ou para os dados solicitados.
- **Respostas de IA indisponíveis:** configure `GEMINI_API_KEY` no ambiente do processo que executa o Django.
- **Nenhum sensor para simular:** confirme se há sensores ativos no banco; use o seed somente se puder substituir os dados atuais.

## Segurança

As configurações atuais são de desenvolvimento. Antes de publicar o sistema, mova segredos e credenciais para variáveis de ambiente, defina `DEBUG=False`, configure `ALLOWED_HOSTS`, restrinja CORS e aplique as recomendações de implantação segura do Django. Não use as senhas de demonstração em produção.
