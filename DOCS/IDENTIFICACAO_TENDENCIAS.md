# Identificação de tendências e O.S. por previsão de alcance do limite

Revisão: 13/11/2026. Esta revisão substitui a abertura de O.S. para toda anomalia confirmada.

## Comportamento operacional

O servidor confirma tendências anormais usando regressão linear, duração observada, quantidade de leituras, sensibilidade, R² e persistência. Uma anomalia confirmada registra um alerta de tendência. A O.S. preditiva de inspeção só é criada quando a projeção confirmada estima alcançar o limite superior dentro da antecedência configurada.

O novo padrão exige **120 minutos de histórico** e prevê alcance do limite em **até 120 minutos**. São dois tempos independentes. Centenas de leituras em poucos minutos não substituem o histórico mínimo. O gráfico continua disponível enquanto a análise aguarda dados.

Configurações salvas mantêm sua duração e os demais critérios. A migração acrescenta antecedência de 120 minutos a elas; o novo default de duração não sobrescreve valores existentes. Configuração específica do sensor prevalece sobre a global mais recente por id; sem ambas, valem os defaults do modelo. Uma configuração inativa não é ignorada.

## Cálculo

Com t em horas desde a primeira leitura, y como valor medido e médias t̄ e ȳ:

```text
b = Σ[(t − t̄)(y − ȳ)] / Σ[(t − t̄)²]
a = ȳ − b·t̄
Reta ajustada: ŷ(t) = a + b·t
Projeção: último valor medido + b·horas futuras
Horas até o limite superior: (limite − último valor medido) / b
R² = 1 − Σ(y − ŷ)² / Σ(y − ȳ)²
Persistência = intervalos no sentido de b / total de intervalos
```

O cálculo usa somas centradas para reduzir cancelamento numérico. R² é limitado a [0, 1]; série constante recebe R²=1, mas não confirma tendência por ter ritmo zero. R² não representa chance de quebra. A projeção estima alcance do limite se o ritmo continuar, não um horário de falha.

A busca exclui datas futuras e valores não finitos. Empates de horário usam a leitura válida de maior id. Preferem-se as últimas N leituras; quando não cobrem a duração mínima e há histórico suficiente, selecionam-se até N leituras reais distribuídas no tempo, preservando os extremos. A consistência também é verificada contra todos os dados originais percorridos, para não esconder picos ou oscilações.

O máximo selecionado é 50 por padrão, configurável de 3 a 500. A API distingue `readings_count` de `source_readings_count`. O número de leituras não define o horizonte futuro. Os detalhes mostram o período efetivamente observado, que pode superar o mínimo com coleta espaçada.

## Configuração

| Campo | Default | Regra |
|---|---:|---|
| `ativo` | true | Habilita a análise efetiva |
| `periodo_horas` | 24 | Busca histórica máxima; inteiro >= 1 |
| `num_leituras` | 50 | Máximo selecionado; 3 a 500 |
| `minimo_leituras` | 3 | Horários distintos; 3 até o máximo |
| `duracao_minima_minutos` | 120 | Duração real da amostra; 1 até a busca máxima |
| `antecedencia_os_minutos` | 120 | Prazo positivo previsto até o limite para abrir O.S. |
| `r2_minimo` | 0,8 | Ajuste mínimo; 0,5 a 1 |
| `persistencia_minima` | 0,7 | Persistência mínima; 0,5 a 1 |
| `sensibilidade` | media | Alta=0,005, média=0,02, baixa=0,05 |
| `direcao_alerta` | crescente | crescente, decrescente ou ambas |

O limiar de inclinação é o fator de sensibilidade multiplicado pelo valor absoluto do limite, por hora; com limite zero, usa-se o próprio fator. É necessário ultrapassá-lo estritamente. R² e persistência precisam alcançar seus mínimos, inclusive nos dados originais quando a amostra é distribuída. Modelo e API validam configurações completas e alterações parciais.

## Elegibilidade, episódios e O.S.

`is_anomalous` indica uma direção confirmada configurada como anormal. `intervention_recommended` exige adicionalmente projeção positiva de até `antecedencia_os_minutos` e um horário de alcance ainda futuro. A decisão compara valores sem arredondamento. A previsão parte da última medição, nunca do instante da consulta.

`intervention_reason` informa: `disabled`, `insufficient_data`, `no_anomaly`, `no_upper_limit_projection`, `expired_projection`, `limit_reached`, `outside_horizon` ou `within_horizon`.

- Anomalia distante cria/atualiza o alerta, mas não abre O.S. Ao entrar no prazo, usa o mesmo alerta e cria sua única O.S.
- Novas leituras e execuções repetidas não duplicam O.S. Concorrência usa bloqueios do sensor e do alerta, unicidade de episódio e relação única de origem.
- Afastar a projeção do prazo não resolve o alerta enquanto a anomalia continuar confirmada. Amostra suficiente sem a condição anormal resolve o episódio, sem encerrar a O.S.
- O.S. concluída ou cancelada não é recriada enquanto o episódio permanece ativo. Recorrência após recuperação é outro episódio.
- Dados insuficientes, histórico expirado e desativação não provam recuperação e não encerram alertas/ordens.
- O cadastro possui apenas limite superior. Quedas configuradas como anormais geram acompanhamento/alerta, sem O.S. por previsão de limite inferior.
- Leitura real no limite não cria uma nova O.S. por previsão; o fluxo por limites permanece independente, com seu próprio alerta e O.S. corretiva. As faixas de alarme podem agir antes do limite superior.
- Prioridade da O.S. continua herdando a criticidade ABC do equipamento. O risco da condição permanece informação distinta.

A análise ocorre na ingestão e pelo comando `python manage.py analisar_tendencias`, inclusive com a tela fechada. Consultas GET e mudanças de janela visual não criam alertas nem ordens. Salvar critérios passa a valer nas próximas execuções. O Gemini não participa da decisão automática.

## Evidência da abertura

`OrdemServico.evidencia_preditiva` guarda uma cópia estruturada, imutável pelo fluxo normal do modelo e somente leitura na API, da análise que efetivamente abriu a ordem. Não se usa a primeira detecção do alerta: ela pode ser anterior, quando a previsão ainda estava fora do prazo.

Inclui resumo legível, instante de registro, equipamento/sensor/unidade/limite, valores e horários selecionados, contagens, ritmo completo e exibido, R², persistência, critérios, configuração, projeção e versão `linear-persistent-upper-limit-v2`. Novas análises e mudanças cadastrais não substituem essa evidência. Registros antigos mantêm o histórico existente, sem fabricar evidências ausentes.

## Tela e API

A página dá destaque ao gráfico em largura total, com seleção de sensor em um painel temporário. O padrão é Ao vivo, com até 60 leituras dos últimos cinco minutos; o modo Previsão para manutenção usa o resultado do servidor. A opção Ampliar gráfico preserva período, escala e pausa. A prévia com ao menos três horários distintos continua visível antes da confirmação. A projeção operacional confirmada desenha a antecedência configurada; prévias e outros gráficos conservam seu horizonte curto. Escala e ajuste histórico ficam em Opções do gráfico. Fórmula e critérios ficam em seções expansíveis. Detalhes de UX: [Telemetria e tendências](TELEMETRIA_UX.md).

- Configurações: `/api/telemetria/trend-config/`, com novo campo `antecedencia_os_minutos`.
- Análise: `/api/telemetria/tendencias/?sensor_id=<id>`; `?all=true` inclui estados insuficientes/desativados na lista.
- A resposta acrescenta `intervention_reason`, `method_version`, `slope_full_precision` e o novo campo em `config_used`, mantendo os campos anteriores.
- A resposta de Tendências também inclui `source_duration_minutes` (tempo real coberto pelas leituras originais verificadas) e `predictive_orders_summary`: `total`, `open_count` e `primary_order` (`id`, `titulo`, `status`, `data_abertura`). O resumo considera ordens acessíveis pelo perfil, independentemente do estado do alerta. A aberta mais recente é prioritária; sem abertas, a encerrada mais recente. Duas consultas em lote evitam carregar evidências e descrições por sensor.
- Histórico sob demanda: `/api/ordens-servico/?sensor_origem=<id>&historico_preditivo=true&limit=10`. Inclui vínculo legado pelo sensor do alerta apenas se `sensor_origem` estiver ausente; ordena abertas primeiro, depois abertura e id decrescentes, com paginação existente. O filtro `historico_preditivo` restringe a ordens preditivas. A visibilidade é compartilhada com a tela de atendimento: empresa e, para técnicos, próprias ou sem responsável.
- O.S.: `/api/ordens-servico/<id>/` expõe `evidencia_preditiva`, protegida contra escrita pela API.
- Permissões e isolamento por empresa continuam em vigor. Somente admin altera configuração global; gestores alteram sensores da própria empresa.

## Validação

Cobrir duas horas exatas, prazo inclusivo sem arredondamento, histórico insuficiente com coleta frequente, distribuição com milhares de dados, picos/oscilações, queda, limite atingido, projeção vencida, episódios, captura tardia da evidência, imutabilidade, API, migração sem sobrescrita e concorrência em PostgreSQL. A demonstração administrativa conserva seu perfil próprio de um minuto.
