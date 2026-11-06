# Ambiente Python e dependências

Revisão: 06/11/2026.

## Problema observado

O `pip install -r requirements.txt` terminava em `ResolutionImpossible`; em seguida, `python manage.py migrate` falhava com `ModuleNotFoundError: No module named django`.

O segundo erro era consequência da instalação interrompida. O ambiente ativado, `venv`, usava Python 3.15.0; o `.venv` existente no mesmo repositório usava Python 3.10.8 e era o ambiente empregado nas validações anteriores. São pastas e interpretadores diferentes.

A lista antiga incluía o SDK efetivamente importado (`google-genai`) e também a pilha antiga `google-generativeai`, `google-ai-generativelanguage`, `google-api-core`, `grpcio-status` e protobuf. O log do pip mostrava que `google-api-core[grpc]==2.30.3` exigia `grpcio-status>=1.75.1` para Python >=3.14, enquanto a lista fixava `grpcio-status==1.71.2`. Outros pacotes fixados também estavam sendo baixados como código-fonte nesse Python.

Django 5.2 suporta Python 3.10 a 3.14 (3.14 desde Django 5.2.8), não Python 3.15. Ver [matriz oficial do Django](https://docs.djangoproject.com/en/5.2/faq/install/#what-python-version-can-i-use-with-django). Para novas instalações, este projeto recomenda Python 3.13. A correção local reutilizou o Python 3.10 já existente; não instalou outro Python nem recriou o `venv`.

## Correção no repositório

- `requirements.txt` declara os 13 pacotes usados diretamente pela aplicação: Django, seus componentes REST/autenticação/documentação, Faker, google-genai, openpyxl, psycopg2-binary, python-dotenv e ReportLab. As versões diretas já fixadas foram mantidas; dependências indiretas passam a ser resolvidas pelo pip.
- Removidos SDKs Google legados sem imports no projeto, seus pins transitivos de gRPC/protobuf e ferramentas sem uso na aplicação, como WeasyPrint. A exportação PDF usa ReportLab.
- Mantido apenas `psycopg2-binary`; removido `psycopg2`, que duplicava o mesmo módulo e exigia compilação.
- `FrontATT/requirements.txt` passa a referenciar `../requirements.txt`, eliminando a cópia divergente. O frontend continua estático.
- README orienta criar/ativar `.venv` com versão explícita de Python e instalar com `python -m pip`.

A lista de dependências diretas não é um lock completo: versões indiretas podem variar entre instalações e versões do Python. Não se deve regenerar esse arquivo com um `pip freeze` de um ambiente que contenha bibliotecas não usadas pelo projeto.

## Usar o ambiente local já corrigido

Na raiz do repositório, para sair do `venv` atual e ativar o `.venv`:

```powershell
deactivate
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
python -m pip check
python manage.py migrate
python manage.py runserver 127.0.0.1:9000
```

Execute `deactivate` somente quando houver um ambiente ativo. Se a execução do script de ativação estiver bloqueada, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` na sessão atual, ou chame o interpretador diretamente, sem ativar:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:9000
```

## Criar ambiente em outra máquina

Instalar Python 3.13 primeiro. Se `.venv` ainda não existir:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python manage.py migrate
```

Uma venv criada com Python 3.15 não muda de interpretador após instalar pacotes. É preciso ativar um ambiente compatível ou criar outro em pasta nova, preservando a anterior.

## Validação realizada

- Resolução completa com `--dry-run --ignore-installed --only-binary=:all:` em Python 3.10: sem conflitos e com distribuições binárias disponíveis para todos os pacotes. Relatório local gerado em `.venv/requirements-resolution.json` (não versionado).
- Instalação real da lista corrigida no `.venv`: concluída.
- `python -m pip check`: nenhuma dependência quebrada.
- `python manage.py check --settings=app.test_settings`: sem problemas.
- Suíte explícita incluindo `gemini_api.tests`: 119 testes descobertos, 116 aprovados e três casos concorrentes ignorados no SQLite por exigirem bloqueios de linha. Não foi repetida a suíte PostgreSQL nesta correção de dependências.
- O `venv` com Python 3.15 foi preservado. A instalação foi feita no `.venv` com Python 3.10; o terminal do usuário precisa ativar esse ambiente para que `python` aponte para ele.

A verificação do banco local encontrou somente `telemetria.0002_trendconfig_direcao_alerta_and_more` pendente. O resultado da aplicação está registrado abaixo.

Migração aplicada com sucesso ao PostgreSQL local: `Applying telemetria.0002_trendconfig_direcao_alerta_and_more... OK`. A consulta `showmigrations telemetria` confirmou `[X]` para `0001` e `0002`. Foram adicionados os cinco campos de configuração, sem exclusão de dados. Não há necessidade de repetir a migração para essa atualização; o comando `migrate` continua seguro para conferir pendências futuras.

A referência `FrontATT/requirements.txt` também foi verificada com `pip install --dry-run --no-index`; todos os requisitos já estavam satisfeitos. `git diff --check` não apontou erros.
