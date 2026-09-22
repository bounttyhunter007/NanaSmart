# Implementação de Padrões de Projeto (Factory Method e Builder)

Este documento registra detalhadamente a implementação dos padrões de projeto arquiteturais no ecossistema do **NanaSmart**, focando na adoção do **Factory Method** no módulo de exportação de dados e do **Builder** na construção de prompts da integração com a IA Gemini.

O objetivo destas implementações é melhorar a manutenibilidade, testabilidade e expansão do código base, mantendo estrita compatibilidade (sem quebras) com o frontend e com as views já existentes.

---

## 1. Padrão Factory Method (Módulo de Exportação)

O módulo de exportação (`exportacao`) é responsável por gerar relatórios de ordens de serviço, equipamentos, alertas e telemetria em múltiplos formatos (CSV, Excel, PDF). 

### 🔴 Como Era (Antes)
Anteriormente, a decisão de qual formato exportar ocorria de maneira **fortemente acoplada** na função `_despachar_formato` dentro de `exportacao/views.py`. 

- O código utilizava uma longa cadeia de condições (estruturas de `if/elif/else`).
- Cada gerador (`exportar_csv`, `exportar_excel`, `exportar_pdf`) possuía assinaturas de funções diferentes, obrigando a `view` a conhecer os detalhes de implementação de cada formato. 
- Por exemplo, `exportar_excel` precisava do argumento `titulo_planilha`, enquanto o `exportar_csv` nem usava esse dado, e a `view` tinha que tratar todas essas variações manualmente.
- Adicionar um novo formato futuramente (ex: `.xml` ou `.json`) exigiria modificar o arquivo central de rotas (`views.py`), desrespeitando o princípio Open-Closed (Aberto para extensão, Fechado para modificação).

### 🟢 Como Ficou (Depois)
O módulo de exportação foi totalmente refatorado utilizando o Padrão **Factory Method**, que delega a criação do objeto de exportação para classes especializadas, garantindo uma interface única para todos os formatos.

- **Interface Única:** Criada a classe abstrata base `Exportador` (`exportacao/utils/base_exporter.py`), que impõe a assinatura única do método `.exportar(nome, titulo, colunas, linhas)`.
- **Especializações:** O código sujo solto foi encapsulado dentro de classes concretas que herdam e implementam a base `Exportador`:
  - `ExportadorCSV` (`exportacao/utils/csv_exporter.py`)
  - `ExportadorExcel` (`exportacao/utils/excel_exporter.py`)
  - `ExportadorPDF` (`exportacao/utils/pdf_exporter.py`)
- **Fábrica Dinâmica:** Criada a `ExportadorFactory` (`exportacao/utils/exporter_factory.py`), que possui um registro dinâmico mapeando o nome do formato para a respectiva classe.
- **Views Desacopladas:** A view de rotas (`exportacao/views.py`) não conhece mais nenhuma lógica de exportação em si. Ela apenas solicita um exportador para a fábrica em uma única linha, não importando o formato: `ExportadorFactory.criar(formato).exportar(...)`.
- **Benefício:** Agora, para adicionar uma exportação `JSON`, basta criar `ExportadorJSON`, herdar da base, e registrá-lo na Factory. A `view` não precisa sofrer uma linha sequer de alteração.

---

## 2. Padrão Builder (Módulo Gemini API)

O módulo `gemini_api` constrói prompts contextuais extensos para envio ao LLM (Google Gemini), baseando-se em dezenas de informações diferentes (status dos equipamentos, ordens em aberto, dados de telemetria, histórico financeiro e perguntas do usuário).

### 🔴 Como Era (Antes)
Anteriormente, o arquivo `gemini_api/prompt_builder.py` funcionava apenas como um aglomerado procedural de funções.

- As funções como `build_chat_prompt` e `build_os_analysis_prompt` criavam arrays (listas de strings) `blocks = []` manualmente.
- Existiam incontáveis `if`s espalhados para verificar se havia alertas ou telemetria para então injetar o texto puro na lista.
- A regra de truncar dados em 5 linhas para não estourar o limite de tokens da IA ficava jogada dentro do arquivo e se repetia sucessivamente dentro de cada método de construção de prompt.
- Faltava legibilidade e era fácil esquecer de adicionar uma seção de contexto essencial em requisições de novas funcionalidades futuras.

### 🟢 Como Ficou (Depois)
Adotamos a orquestração do padrão **Builder**, onde o processo complexo de montar uma requisição para a IA é dividida em passos lógicos e encadeáveis, abstraindo a concatenação para um diretor especializado.

- **Classe de Produto Final:** O artefato gerado agora é o objeto da classe `Prompt` (`gemini_api/prompt.py`), que encapsula com segurança o texto formatado para requisição da API.
- **O Construtor Lógico (Builder):** Foi criada a base de implementação concreta `PromptBuilderConcreto` (`gemini_api/prompt_builder_pattern.py`). Esse builder expõe um design fluente (encadeável): `builder.com_contexto().com_alertas().com_telemetria().com_pergunta()`. É responsabilidade do próprio builder saber como truncar linhas ou pular dados vazios (sem `if`s poluindo a `view`).
- **O Diretor (Director):** Criado o coordenador `PromptDirector` (`gemini_api/prompt_director.py`). Ele conhece *a receita* específica para cada tipo de contexto da IA (ex: Chat vs Relatório Financeiro) e diz ao Builder *qual deve ser a ordem* dos blocos e chamados.
- **Compatibilidade Segura (Sem Quebras):** Modificamos o antigo arquivo `prompt_builder.py` de forma que as suas funções não fazem mais lógicas soltas, mas apenas interagem com os novos Diretores delegando as chamadas, e retornando a string polida final. Com isso, os endpoints originais do projeto não sofreram quebra de contrato.

---

## Resultados Finais e Benefícios Técnicos

1. **Separação de Responsabilidades (SoC):** Cada classe agora possui um único motivo para mudar (Princípio de Responsabilidade Única - SRP). As *views* apenas recebem requisições web, os *builders* organizam e tratam textos lógicos, e as *factories* instanciam os objetos.
2. **Escalabilidade e Segurança:** Novos cenários (novos formatos de download ou novos fluxos de IA) podem ser inseridos de forma independente simplesmente criando novas instâncias seguindo o contrato, protegendo assim o ecossistema existente de regressões indesejadas (Open-Closed Principle).
3. **Validação e Integridade:** Todas as modificações arquiteturais e injecões de dependência foram certificadas via checagem estática no framework (comando Django: `python manage.py check`), provando um desacoplamento limpo (0 issues).
