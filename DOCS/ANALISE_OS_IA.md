# Análise individual de OS por IA

No detalhe de uma ordem de serviço, o botão **Analisar OS** solicita uma avaliação ao Gemini. Abrir a consulta não gera análise. A resposta aparece no próprio detalhe e pode ser solicitada novamente. Fechar, trocar ou atualizar a OS descarta o resultado; nenhuma análise é gravada no banco.

## Instruções por empresa

Em **Instruções da IA**, administradores e gestores encontram um único editor já preenchido com o texto padrão. **Salvar** personaliza as próximas análises da empresa; **Restaurar padrão** remove a personalização. Um campo vazio também utiliza o padrão atual do código.

O gestor configura somente sua empresa. O administrador seleciona a empresa no filtro superior. Técnicos não acessam essa configuração. Os prompts globais anteriores continuam restritos ao administrador, em **Outras configurações da IA**, e não afetam a análise individual.

## Dados e permissões

O backend busca a OS e verifica as mesmas permissões da consulta: administrador vê todas; gestor vê sua empresa; técnico vê suas OS e as sem responsável da própria empresa.

O contexto contém os dados operacionais da OS e do equipamento, o serviço realizado quando registrado, o alerta de origem, até cinco OS anteriores autorizadas do mesmo equipamento e a última leitura disponível de até cinco sensores. O sensor de origem tem preferência. Datas, ausências e limites do contexto são informados. Custos e dados pessoais dos responsáveis não são enviados por esse recurso.

Regras fixas orientam a IA a separar fatos de hipóteses, tratar descrições como dados e preservar as classificações existentes. A análise não altera a OS, a prioridade, a criticidade ou o equipamento.

## API

| Método e rota | Comportamento |
| --- | --- |
| `POST /api/ordens-servico/{id}/analise-ia/` | Sem corpo obrigatório. Retorna `response` e `model_used`; 404 para OS fora do escopo, 503 se a IA estiver indisponível e 502 para falha do provedor ou resposta vazia. Respostas válidas usam `Cache-Control: no-store`. |
| `GET /api/gemini/prompts/analise-os/` | Retorna `empresa`, `custom_text`, `original_text`, `effective_text`, `is_customized` e `updated_at`. Consultar o padrão não cria registros. |
| `PATCH /api/gemini/prompts/analise-os/` | Recebe `custom_text` (até 12.000 caracteres). O padrão é somente leitura. |
| `POST /api/gemini/prompts/analise-os/reset/` | Restaura o padrão somente da empresa selecionada. |

Nas rotas de configuração, `?empresa={id}` é obrigatório para administrador e opcional para gestor. Uma tentativa do gestor de selecionar outra empresa recebe 403.

## Instalação e validação

Aplicar a migração aditiva com `python manage.py migrate` e configurar `GEMINI_API_KEY` no backend conforme a integração já existente. A chave nunca é enviada ao navegador.

```powershell
.\.venv\Scripts\python.exe manage.py test gemini_api.test_order_analysis gemini_api.tests manutencao.tests --settings=app.test_settings --noinput
node --test FrontATT/order-analysis.test.cjs FrontATT/abc.test.cjs FrontATT/live-chart.test.cjs
```

Esses testes simulam o Gemini e verificam permissões, isolamento de empresas e histórico, padrão e restauração, falhas, acionamento manual e descarte de respostas atrasadas. Não fazem chamadas reais ao provedor.
