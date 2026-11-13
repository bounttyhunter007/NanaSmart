# Base e roteiro de apresentação

Os dados são sintéticos e identificados por `[DEMO]`. Fabricantes e modelos seguem o catálogo do projeto, sem representar máquinas físicas cadastradas. Alertas e ordens automáticas são calculados pelos serviços reais. Gemini é opcional e não participa dessa decisão.

## Preparação

Use um banco de demonstração que possa ser substituído. Pare o simulador antes de gerar a base. Na pasta do projeto, com o ambiente virtual ativado:

```powershell
python manage.py migrate
python scripts/seed_db.py --check
python scripts/seed_db.py --empresas 2 --equipamentos 10 --funcionarios 4 --days 120 --seed 42
python scripts/simulador_realtime.py --check
python manage.py runserver 127.0.0.1:9000
```

O seed **apaga e substitui** os dados operacionais. A transação é revertida em caso de falha ou interrupção antes do commit. Contas administrativas existentes preservam senhas, perdem o vínculo com a empresa removida e superusuários ficam com perfil `admin`. O resumo final só aparece após a gravação; guarde os logins, IDs e comandos impressos. `--check` verifica parâmetros/migrações, mas não certifica os dados da base antiga nem testa a conexão com Gemini.

Abra `FrontATT/index.html`. Quando o banco já tinha um `admin`, use sua senha existente. Na base nova: `admin` / `admin`. Na empresa 1: `gestor.demo.1` / `123` e `tecnico.demo.1.1` / `123`. Empresa 2 usa `gestor.demo.2` e `tecnico.demo.2.1`. Havendo colisão com administrador preservado, vale o login com sufixo impresso pelo seed.

Os nomes e valores se repetem com a mesma `--seed`; horários são relativos à execução e IDs não são fixos. O padrão cria um gestor e três técnicos por empresa. O mínimo é um gestor e um técnico. Para todos os cenários, use pelo menos três equipamentos por empresa; bases menores mostram aviso de cobertura parcial.

Para a apresentação, prepare a base com `scripts/seed_db.py`. Os comandos antigos `popular_banco`, `popular_usuarios`, `popular_equipamentos` e `popular_os` fazem cadastros parciais e não garantem sensores, histórico, indicadores ou cobertura dos cenários deste roteiro.

## Onde encontrar os exemplos

Cada empresa recebe os mesmos três primeiros tipos de cenário. Procure pelo sufixo `E01-01`, `E01-02` ou `E01-03` na empresa 1 (`E02` na empresa 2).

| Equipamento | Criticidade | O que mostrar |
|---|---|---|
| Motor, final `-01` | B | Leituras estáveis; trabalho atribuído e livre; plano de manutenção por horímetro |
| Bomba, final `-02` | A | Temperatura crescente abaixo do limite máximo; alerta de tendência e O.S. preditiva com evidências da previsão |
| Compressor de reserva, final `-03` | C, avaliação individual | Pressão com alerta crítico ativo; vibração com episódio crítico normalizado; temperatura com duas ocorrências normalizadas vinculadas à mesma O.S. ainda aberta |

Com cinco ou mais equipamentos, o quarto estará em manutenção com trabalho em andamento, e o quinto inativo, com sensores desativados e leituras antigas. O simulador não os alimenta. Os demais equipamentos complementam o catálogo. Todos têm quatro manutenções concluídas, duas delas dentro dos últimos sete dias, custos e uma solicitação cancelada sem execução. Os ativos também têm inspeção pendente sem responsável.

## Roteiro dos três perfis

1. **Administrador:** mostrar as duas empresas, equipamentos A/B/C, ocorrências recentes e indicadores com filtro de 7 ou 30 dias. Abrir os alertas do compressor, conferir horários de abertura, elevação, normalização e vínculo com O.S. A normalização do sensor não conclui a manutenção.
2. **Gestor da empresa 1:** mostrar os mesmos dados dentro da sua empresa. Na fila, abrir uma inspeção disponível e atribuí-la ao técnico. Mostrar conclusões recentes e custos. Os exemplos A/B/C são criticidades dos equipamentos e prioridades herdadas nas novas ordens; não confundem prioridade com gravidade do alerta.
3. **Técnico da empresa 1:** mostrar uma ordem pendente atribuída, uma em andamento e ordens disponíveis. Executar uma ação permitida sobre a própria ordem e conferir o histórico. A empresa 2 deve permanecer fora do seu escopo.
4. **Administrador, tendência ao vivo:** usar a [demonstração guiada de aproximadamente um minuto](DEMONSTRACAO_TENDENCIAS.md), que cria sensor próprio. Mostrar quantidade e duração mínimas, previsão de atingir o limite e O.S. automática. Opcionalmente avançar para ultrapassagem e recuperação.

## Telemetria e horímetro

Para manter um gráfico se movimentando, copie o comando **Ao vivo** impresso para o motor da empresa escolhida. Ele usa `--cenario oscilacao` e o ID realmente gerado. Esse cenário fica abaixo do aviso e não interfere nos sensores históricos de tendência e recorrência dos outros equipamentos. Para conferir antes, acrescente `--check`; para observar propostas sem gravar, use `--cycles 3 --dry-run --debug`.

O cenário padrão `misto` depende de sorte. A escalada padrão leva cerca de 25 minutos no total; fases são alvos e não garantem que cada faixa seja atingida instantaneamente. Evite alimentar todos os sensores enquanto mostra um episódio histórico específico, porque as novas leituras mudam legitimamente a análise e podem normalizar alertas. O dashboard e a lista de tendências atualizam em até aproximadamente 30 segundos; o gráfico do equipamento consulta a cada cinco segundos.

Para manutenção por horímetro, abra o motor `-01`. O seed imprime o plano e a conta: normalmente **1000 h atuais + 250 h de intervalo = disparo em 1250 h**. Atualize o horímetro do equipamento para o valor de disparo indicado. A gravação do equipamento cria a O.S. `[PREDITIVA] [DEMO] Inspeção periódica` e atualiza o próximo marco. Salvar novamente o mesmo valor não deve duplicar a ordem. O simulador de sensores não avança o horímetro.

## Validação automatizada

```powershell
python manage.py test telemetria.test_seed_demo telemetria.test_seed_telemetry telemetria.test_simulador_realtime --settings=app.test_settings --noinput
```

Os testes verificam datas e vínculos, KPIs recentes, escopo dos três perfis, evidências, recuperação/recorrência, acionamento por horímetro, retomada, operação sem gravação, migrações pendentes, preservação de administradores e reversão após falha. Usam o banco descartável; não preparam o banco da apresentação.
