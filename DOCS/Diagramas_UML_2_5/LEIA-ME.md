# Diagramas arquiteturais NanaSmart - UML 2.5

Esta pasta contém os itens **3, 4 e 5** do modelo de entrega anexado, separados por diagrama e baseados no código do projeto em 11/11/2026.

| Item | Arquivo PDF | Conteúdo complementar |
| --- | --- | --- |
| 3 | [Diagrama de Pacotes](03_Diagrama_de_Pacotes.pdf) | 3.2. Memória descritiva com 15 linhas, organização lógica, dependências e visibilidade. |
| 4 | [Diagrama de Componentes](04_Diagrama_de_Componentes.pdf) | 4.2. Mapeamento das interfaces fornecidas e requeridas e suas finalidades. |
| 5 | [Diagrama de Implantação](05_Diagrama_de_Implantacao.pdf) | 5.2. Nós, ambientes de execução, protocolos e artefatos implantados. |

Cada diagrama possui três formatos com o mesmo nome-base:

- **PDF:** duas páginas; diagrama vetorial em A3 horizontal e complemento em A4 vertical. Permite ampliar sem perder a definição das linhas e do texto.
- **PNG:** imagem do diagrama com 3600 pixels de largura, para inserir no modelo de entrega.
- **DRAWIO:** versão editável no diagrams.net. Abra o arquivo pelo menu **Arquivo > Abrir de > Dispositivo**. As formas, textos e linhas são elementos editáveis. Para mover conjuntos, selecione e agrupe os elementos correspondentes.

## Decisões de modelagem

- Os pacotes Acesso, Operação e Integrações e saídas são agrupamentos lógicos para explicar a arquitetura; não são novas pastas do projeto. Os pacotes internos usam os nomes reais do código. As setas mostram as dependências principais, incluindo dependências recíprocas existentes.
- Os componentes de negócio fazem parte de um único backend Django. Os nomes de interfaces iniciados por `I` descrevem os contratos das rotas, serviços e bibliotecas; não afirmam a existência de classes Python com esses nomes. As esferas indicam interfaces fornecidas e as cavidades, interfaces requeridas.
- A implantação representa a configuração local descrita no README e em `app/settings.py`: frontend aberto no navegador, Django em `127.0.0.1:9000` e PostgreSQL em `localhost:5432`, banco `manutencao`.
- O simulador usa o ambiente Django e grava pelo ORM. A API Gemini é uma integração opcional do backend. A CDN fornece bibliotecas JavaScript ao navegador.
- O repositório não especifica infraestrutura de produção nem protocolo de integração com sensores físicos. Esses elementos não foram inventados no diagrama.
- Os desenhos foram gerados localmente; os arquivos editáveis são do diagrams.net. O modelo anexado menciona Lucidchart como ferramenta de exportação.

## Fontes consultadas no projeto

`readme.md`, `requirements.txt`, `app/settings.py`, `app/urls.py`, `FrontATT/index.html`, `FrontATT/app.js`, módulos de `accounts/` e `authentication/`, modelos e serviços de `ativos/` e `manutencao/`, `manutencao/dashboards/`, signals e serviços de `telemetria/` e `alertas/`, `gemini_api/adapters.py`, `gemini_api/context_service.py`, `exportacao/views.py`, `scripts/simulador_realtime.py` e o comando `analisar_tendencias`.

## Regenerar os arquivos

O código de geração está em [fontes/gerar_diagramas.py](fontes/gerar_diagramas.py). Ele usa Python, ReportLab, as fontes Arial do Windows e `pdftoppm` do Poppler disponível no PATH. Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe DOCS/Diagramas_UML_2_5/fontes/gerar_diagramas.py
```

A geração não inicia o sistema nem consulta ou modifica seu banco de dados.
