/* Executar: node --test FrontATT/telemetria.test.cjs. Sem dependências externas. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
function fixture(handler) {
  let app;
  const urls = [];
  const timers = new Map();
  const unmount = [];
  let timerId = 0;
  const context = {
    Vue: { ref: value => ({ value }), reactive: value => value,
      computed: getter => ({ get value() { return typeof getter === 'function' ? getter() : getter.get(); }, set value(value) { getter.set(value); } }), watch() {}, onMounted() {}, onUnmounted(callback) { unmount.push(callback); },
      nextTick: callback => callback?.(), createApp: options => ({ mount() { app = options.setup(); } }) },
    localStorage: { getItem() { return ''; }, setItem() {}, removeItem() {} },
    document: { hidden: false, addEventListener() {}, removeEventListener() {}, documentElement: { classList: { add() {}, remove() {} } }, getElementById() {} },
    window: {}, console, URLSearchParams, Date, setTimeout, clearTimeout,
    setInterval(callback, ms) { const id = ++timerId; timers.set(id, { callback, ms }); return id; },
    clearInterval(id) { timers.delete(id); },
    fetch: async (url, options = {}) => { urls.push(url); const body = await handler(url, options); return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => body }; },
  };
  vm.runInNewContext(source, context);
  return { app, urls, timers, document: context.document, unmount: () => unmount.forEach(callback => callback()) };
}
test('leituras preservam zero, empresa, contexto e paginação sem truncar resultados', async () => {
  const { app, urls } = fixture(() => ({ count: 150, results: Array.from({ length: 50 }, (_, id) => ({ id })) }));
  app.globalEmpresa.value = '2';
  Object.assign(app.telemetry, { min: 0, max: 20, equipment: 3, sensor: 4, size: 50, offset: 50 });
  await app.fetchTelemetria();
  const query = new URL(urls[0]).searchParams;
  assert.equal(query.get('valor_min'), '0');
  assert.equal(query.get('sensor__equipamento__empresa'), '2');
  assert.equal(query.get('sensor'), '4');
  assert.equal(query.get('sensor__equipamento'), '3');
  assert.equal(query.get('offset'), '50');
  assert.equal(app.telemetryRows.value.length, 50);
  assert.equal(app.telemetryCount.value, 150);
});
test('intervalo inválido é explicado sem disparar consulta', async () => {
  const { app, urls } = fixture(() => ({}));
  Object.assign(app.telemetry, { min: 10, max: 0 });
  await app.fetchTelemetria();
  assert.equal(urls.length, 0);
  assert.match(app.telemetry.error, /mínimo/);
});
test('resposta atrasada não substitui resultados do contexto mais recente', async () => {
  let release;
  let calls = 0;
  const { app } = fixture(() => ++calls === 1 ? new Promise(resolve => { release = resolve; }) : ({ count: 1, results: [{ id: 2 }] }));
  const older = app.fetchTelemetria();
  app.telemetry.equipment = 2;
  await app.fetchTelemetria();
  release({ count: 1, results: [{ id: 1 }] });
  await older;
  assert.equal(app.telemetryRows.value[0].id, 2);
  assert.equal(app.telemetry.busy, false);
});
test('tendências distinguem quatro condições, filtram e paginam sem novas consultas', async () => {
  const sample = (id, condition) => ({ sensor_id: id, sensor_info: { id, nome: 'Sensor ' + id, equipamento_id: 1, equipamento_nome: 'Motor' },
    analysis_enabled: condition !== 'disabled', insufficient_data: condition === 'insufficient',
    is_anomalous: condition === 'anomalous', direction: 'stable' });
  const rows = [sample(1,'anomalous'), sample(2,'normal'), sample(3,'insufficient'), sample(4,'disabled')];
  const { app, urls } = fixture(() => rows);
  Object.assign(app.trendPage, { size: 2 });
  await app.fetchTrends();
  assert.equal(app.trendCount.value, 4);
  assert.equal(app.trendSummary.value.disabled, 1);
  app.changeTrendPage(1);
  assert.equal(app.trendRows.value[0].sensor_id, 3);
  app.trendPage.condition = 'insufficient'; app.applyTrendFilters();
  assert.equal(app.trendCount.value, 1);
  assert.equal(app.trendRows.value[0].sensor_id, 3);
  assert.equal(urls.length, 1);
  assert.equal(app.trendDirection(rows[1]), 'Estável');
  assert.equal(app.trendDirection(rows[2]), '—');
});
test('busca de sensor usa filtros próprios e não consulta leituras', async () => {
  const { app, urls } = fixture(() => ({ count: 0, results: [] }));
  Object.assign(app.telemetry, { tab: 'sensores', search: ' Motor ', tipo: 'temperatura', ativo: 'false' });
  await app.fetchTelemetria();
  assert.match(urls[0], /sensores/);
  const query = new URL(urls[0]).searchParams;
  assert.equal(query.get('search'), 'Motor');
  assert.equal(query.get('ativo'), 'false');
});
test('opções percorrem todas as páginas e respeitam filtro de empresa', async () => {
  const { app, urls } = fixture(url => url.includes('offset=100') ? ({ results: [{ id: 101 }], next: null }) : ({ count: 101, results: [{ id: 1 }], next: url + '&offset=100' }));
  app.globalEmpresa.value = 2;
  await app.enterTelemetry();
  assert.equal(app.telemetry.equipments.length, 2);
  assert.equal(app.telemetry.sensors.length, 2);
  assert.ok(urls.some(url => url.includes('equipamento__empresa=2')));
});
test('após exclusão na última página retorna à última página existente', async () => {
  const { app } = fixture(url => ({ count: 20, results: new URL(url).searchParams.get('offset') === '20' ? [] : [{ id: 1 }] }));
  app.telemetry.offset = 20;
  await app.fetchTelemetria();
  assert.equal(app.telemetry.offset, 0);
  assert.equal(app.telemetryRows.value[0].id, 1);
});

function anomaly(id, alertId = id) {
  return { sensor_id: id, sensor_info: { id, nome: 'Sensor ' + id, equipamento_id: 3, equipamento_nome: 'Motor' }, direction: 'increasing',
    analysis_enabled: true, insufficient_data: false, is_anomalous: true, active_alert_id: alertId };
}
test('monitoramento usa 30 segundos e não acumula timers; logout e desmontagem encerram', () => {
  const { app, timers, unmount } = fixture(() => []);
  app.token.value = 'test';
  app.startTrendPolling(); app.startTrendPolling();
  assert.equal(timers.size, 1);
  assert.equal([...timers.values()][0].ms, 30000);
  app.logout();
  assert.equal(timers.size, 0);
  app.token.value = 'next-session';
  app.startTrendPolling(); assert.equal(timers.size, 1); unmount();
  assert.equal(timers.size, 0);
});
test('atualização automática preserva contexto, página e detalhe aberto', async () => {
  const rows = Array.from({ length: 25 }, (_, index) => anomaly(index + 1));
  const { app, urls } = fixture(() => rows);
  app.token.value = 'test'; app.view.value = 'tendencias';
  Object.assign(app.trendPage, { equipment: 3, condition: 'anomalous', size: 20, offset: 20, detail: rows[20] });
  await app.refreshTrendMonitoring();
  assert.match(urls[0], /all=true/);
  assert.equal(app.trendPage.offset, 20);
  assert.equal(app.trendPage.equipment, 3);
  assert.equal(app.trendPage.condition, 'anomalous');
  assert.equal(app.trendPage.detail.sensor_id, 21);
  assert.equal(app.trendRows.value.length, 5);
  assert.equal(app.trendAlerts.value.length, 25);
  assert.equal(app.trendMonitor.newCount, 0);
  assert.equal(app.trendPage.busy, false);
});
test('primeira consulta não avisa; nova condição avisa uma vez sem navegar', async () => {
  let rows = [anomaly(1)];
  const { app } = fixture(() => rows);
  app.token.value = 'test'; app.view.value = 'ordens';
  await app.refreshTrendMonitoring();
  assert.equal(app.trendMonitor.newCount, 0);
  rows = [anomaly(1), anomaly(2)];
  await app.refreshTrendMonitoring(); await app.refreshTrendMonitoring();
  assert.equal(app.trendMonitor.newCount, 1);
  assert.equal(app.view.value, 'ordens');
  assert.equal(app.trendAlerts.value.length, 2);
  rows = [anomaly(1), anomaly(2, 200)];
  await app.refreshTrendMonitoring();
  assert.equal(app.trendMonitor.newCount, 2); // Outro episódio do mesmo sensor.
});
test('falha transitória preserva dados e timestamp e se recupera sem alerta duplicado', async () => {
  let fail = false;
  const { app } = fixture(() => { if (fail) throw new Error('offline'); return [anomaly(1)]; });
  app.token.value = 'test';
  await app.refreshTrendMonitoring(); const stamp = app.trendMonitor.updatedAt;
  fail = true; await app.refreshTrendMonitoring();
  assert.equal(app.trendAlerts.value.length, 1);
  assert.equal(app.trendMonitor.updatedAt, stamp);
  assert.match(app.trendMonitor.error, /última consulta/);
  fail = false; await app.refreshTrendMonitoring();
  assert.equal(app.trendMonitor.error, '');
  assert.equal(app.trendMonitor.newCount, 0);
});
test('monitoramento evita sobreposição, ignora aba oculta e não consulta sem login', async () => {
  let release;
  const { app, urls, document } = fixture(() => new Promise(resolve => { release = resolve; }));
  await app.refreshTrendMonitoring(); assert.equal(urls.length, 0);
  app.token.value = 'test'; document.hidden = true;
  await app.refreshTrendMonitoring(); assert.equal(urls.length, 0);
  document.hidden = false;
  const pending = app.refreshTrendMonitoring();
  await app.refreshTrendMonitoring(); assert.equal(urls.length, 1);
  app.logout(); release([anomaly(1)]); await pending;
  assert.equal(app.trendAlerts.value.length, 0);
});
test('troca de empresa descarta resposta antiga e estabelece nova referência sem avisos falsos', async () => {
  let release;
  const { app } = fixture(url => url.includes('empresa_id=2') ? [anomaly(2)] : new Promise(resolve => { release = resolve; }));
  app.token.value = 'test'; app.view.value = 'perfil';
  const older = app.refreshTrendMonitoring();
  app.globalEmpresa.value = 2; app.onGlobalEmpresaChange();
  await new Promise(resolve => setImmediate(resolve));
  release([anomaly(1)]); await older;
  assert.equal(app.trendAlerts.value[0].sensor_id, 2);
  assert.equal(app.trendMonitor.newCount, 0);
});
test('consulta manual mais recente vence polling pendente', async () => {
  let release;
  let calls = 0;
  const { app } = fixture(() => ++calls === 1 ? new Promise(resolve => { release = resolve; }) : [anomaly(2)]);
  app.token.value = 'test'; app.view.value = 'tendencias';
  const polling = app.refreshTrendMonitoring();
  await app.fetchTrends();
  release([anomaly(1)]); await polling;
  assert.equal(app.trendPage.rows[0].sensor_id, 2);
  assert.equal(app.trendAlerts.value[0].sensor_id, 2);
});

test('filtros e paginação de Telemetria não influenciam a página de Tendências', async () => {
  const { app } = fixture(url => url.includes('/tendencias/') ? [anomaly(1), anomaly(2)] : { count: 1, results: [{ id: 99 }] });
  Object.assign(app.telemetry, { equipment: 99, sensor: 999, offset: 40, size: 50 });
  await app.fetchTrends();
  assert.equal(app.trendPage.equipment, ''); assert.equal(app.trendPage.sensor, 1);
  assert.equal(app.trendCount.value, 2); assert.equal(app.trendPage.offset, 0);
  app.trendPage.equipment = 3; app.trendPage.sensor = 1; app.applyTrendFilters();
  assert.equal(app.trendCount.value, 2);
  assert.equal(app.telemetry.equipment, 99); assert.equal(app.telemetry.sensor, 999);
  app.telemetry.equipment = 100; await app.applyTelemetryFilters(true);
  assert.equal(app.trendPage.equipment, 3); assert.equal(app.trendPage.sensor, 1);
  assert.equal(app.trendCount.value, 2);
});
test('equipamento com um único sensor seleciona-o automaticamente, sem alterar Telemetria', async () => {
  const other = anomaly(2); other.sensor_info.equipamento_id = 4; other.sensor_info.equipamento_nome = 'Bomba';
  const { app } = fixture(() => [anomaly(1), other]);
  await app.fetchTrends();
  app.telemetry.sensor = 88;
  Object.assign(app.trendPage, { equipment: 4, sensor: 1, offset: 20 });
  app.applyTrendFilters(true);
  assert.equal(app.trendPage.sensor, 2); assert.equal(app.trendPage.offset, 0);
  assert.equal(app.trendSensors.value.length, 1); assert.equal(app.trendSensors.value[0].id, 2);
  assert.equal(app.trendEquipments.value.length, 2);
  assert.equal(app.telemetry.sensor, 88);
});
test('atalho explícito abre página de Tendências sem alterar seleção de Telemetria', async () => {
  const { app } = fixture(() => [anomaly(1)]);
  Object.assign(app.telemetry, { equipment: 10, sensor: 20 });
  await app.showTrends(3,1);
  assert.equal(app.view.value, 'tendencias');
  assert.equal(app.trendPage.equipment, 3); assert.equal(app.trendPage.sensor, 1);
  assert.equal(app.telemetry.equipment, 10); assert.equal(app.telemetry.sensor, 20);
  app.clearTrendFilters();
  assert.equal(app.trendCount.value, 1); assert.equal(app.trendPage.equipment, '');
  assert.equal(app.telemetry.sensor, 20);
});
test('menu permite acessar tendências diretamente e a antiga aba não é aceita', async () => {
  const { app, urls } = fixture(() => [anomaly(1)]);
  app.telemetry.equipment = 99;
  app.setTelemetryTab('tendencias');
  assert.equal(app.telemetry.tab, 'leituras');
  app.navigate('tendencias');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(app.view.value, 'tendencias');
  assert.match(urls[0], /tendencias/);
  assert.equal(app.trendPage.equipment, ''); assert.equal(app.trendCount.value, 1);
});

test('seleção inicial abre um único gráfico e mantém a ultrapassagem representável', async () => {
  const row = anomaly(1);
  Object.assign(row.sensor_info, { limite_alerta: 100 });
  row.readings_summary = [{ valor: 40, timestamp: '2026-11-06T10:00:00Z' }, { valor: 108, timestamp: '2026-11-06T11:00:00Z' }];
  const { app } = fixture(() => [row]);
  await app.fetchTrends();
  assert.equal(app.selectedTrend.value.sensor_id, 1);
  assert.equal(app.trendPage.chartMode, 'live');
  app.trendPage.equipment = 3; app.applyTrendFilters(true);
  assert.equal(app.selectedTrend.value.sensor_id, 1);
  const chart = app.selectedTrendChart.value;
  assert.equal(chart.max, 108); assert.equal(chart.limit, 100);
  assert.ok(Number(chart.points.split(' ')[1].split(',')[1]) < chart.limitY);
});
test('vários sensores mantêm uma seleção; clicar na lista muda somente o gráfico', async () => {
  const { app } = fixture(() => [anomaly(1), anomaly(2)]);
  await app.fetchTrends(); app.trendPage.equipment = 3; app.applyTrendFilters(true);
  assert.equal(app.trendPage.sensor, 1);
  app.openTrendDetail(app.trendPage.rows[1]);
  assert.equal(app.selectedTrend.value.sensor_id, 2);
  assert.equal(app.trendCount.value, 2);
});

test('busca ignora acentos, filtra equipamento e mantém a escolha nas atualizações', async () => {
  const first = anomaly(1), second = anomaly(2);
  first.sensor_info.nome = 'Vibração';
  second.sensor_info.equipamento_id = 4;
  second.sensor_info.equipamento_nome = 'Bomba de circulação';
  const {app} = fixture(() => [first, second]);
  await app.fetchTrends();
  app.trendPage.search = 'vibracao'; app.applyTrendFilters();
  assert.equal(app.trendCount.value, 1);
  app.clearTrendFilters();
  app.selectTrendEquipment(4);
  assert.equal(app.trendPage.sensor, 2);
  app.trendPage.chartMode = 'analysis';
  await app.fetchTrends();
  assert.equal(app.trendPage.sensor, 2);
  assert.equal(app.trendPage.chartMode, 'analysis');
  app.trendPage.search = 'inexistente'; app.applyTrendFilters();
  assert.equal(app.trendCount.value, 0);
  assert.equal(app.selectedTrend.value, null);
});

test('os dois tempos são independentes e percentuais são convertidos ao salvar', async () => {
  let saved;
  const {app} = fixture((url, options) => { saved = JSON.parse(options.body); return {}; });
  app.trendConfigModal.form = {ativo:true, periodo_horas:24, num_leituras:50, minimo_leituras:3,
    duracao_minima_minutos:30, antecedencia_os_minutos:480, persistencia_minima:.7, r2_minimo:.8,
    direcao_alerta:'crescente', sensibilidade:'media'};
  app.setTrendTimePreset(120);
  app.trendPersistencePercent.value = 75;
  app.trendR2Percent.value = 90;
  await app.saveTrendConfig();
  assert.equal(saved.duracao_minima_minutos, 120);
  assert.equal(saved.antecedencia_os_minutos, 480);
  assert.equal(saved.persistencia_minima, .75);
  assert.equal(saved.r2_minimo, .9);
});
test('perfil rápido prepara configuração de um minuto sem salvar nem mudar a global', () => {
  const { app, urls } = fixture(() => []);
  app.trendConfigModal.form = { duracao_minima_minutos: 30, minimo_leituras: 3, num_leituras: 50 };
  app.setTrendTimePreset(1);
  assert.equal(app.trendConfigModal.form.duracao_minima_minutos, 1);
  assert.equal(app.trendConfigModal.form.minimo_leituras, 7);
  assert.equal(app.trendConfigModal.form.num_leituras, 500);
  assert.equal(urls.length, 0);
});
function demoSnapshot(step = 1, status = 'executando') {
  const row = anomaly(1);
  return { id: 'demo-id', empresa_id: 2, sensor_id: 1, equipamento_id: 3,
    passo: step, status, analysis: row, alertas: [], ordens: [] };
}
test('demo exige modo admin de teste e empresa antes de enviar qualquer escrita', async () => {
  const { app, urls } = fixture(() => demoSnapshot());
  app.token.value = 'test';
  await app.runTrendDemo(); assert.equal(urls.length, 0);
  app.me.value = { tipo_usuario: 'admin' }; app.testerMode.value = true;
  await app.runTrendDemo(); assert.equal(urls.length, 0); assert.match(app.trendDemo.error, /empresa/);
});
test('demo usa endpoint dedicado, seleciona somente [DEMO] e para timer ao concluir', async () => {
  let body;
  let response = demoSnapshot();
  const { app, urls, timers } = fixture((url, options) => { body = JSON.parse(options.body); return response; });
  app.me.value = { tipo_usuario: 'admin' }; app.testerMode.value = true; app.token.value = 'test';
  app.trendDemo.company = 2; app.telemetry.equipment = 99;
  await app.runTrendDemo();
  assert.match(urls[0], /tendencias\/demo\/$/); assert.equal(body.empresa, 2);
  assert.equal(app.trendPage.equipment, 3); assert.equal(app.trendPage.sensor, 1);
  assert.equal(app.telemetry.equipment, 99);
  assert.equal([...timers.values()][0].ms, 2000);
  response = demoSnapshot(7, 'concluido');
  await app.runTrendDemo('avancar');
  assert.equal(body.acao, 'avancar'); assert.equal(timers.size, 0);
  assert.equal(app.trendDemo.session.status, 'concluido');
});
test('resposta de demo depois do logout é descartada e timer não reaparece', async () => {
  let release;
  const { app, timers } = fixture(() => new Promise(resolve => { release = resolve; }));
  app.me.value = { tipo_usuario: 'admin' }; app.testerMode.value = true; app.token.value = 'test'; app.trendDemo.company = 2;
  const pending = app.runTrendDemo(); app.logout();
  release(demoSnapshot()); await pending;
  assert.equal(app.trendDemo.session, null); assert.equal(timers.size, 0);
});

test('renovação normal de token não perde a demonstração criada', async () => {
  let app;
  const state = fixture(() => { app.token.value = 'renewed-token'; return demoSnapshot(); });
  app = state.app;
  app.me.value = { id: 1, tipo_usuario: 'admin' }; app.testerMode.value = true;
  app.token.value = 'old-token'; app.trendDemo.company = 2;
  await app.runTrendDemo();
  assert.equal(app.trendDemo.session.id, 'demo-id');
  assert.equal(app.trendPage.sensor, 1);
});
test('histórico envia os mesmos filtros, preserva gravidade ordenada pelo servidor e pagina', async () => {
  const rows = [{ id: 8, nivel: 'critico' }, { id: 7, nivel: 'medio' }];
  const { app, urls } = fixture(url => url.includes('offset=2')
    ? { count: 3, results: [{ id: 6 }], previous: '/api/alertas/?offset=0' }
    : { count: 3, results: rows, next: '/api/alertas/?offset=2&sensor=4' });
  app.globalEmpresa.value = '2';
  Object.assign(app.filters.alertas, { search: 'motor', nivel: 'baixo', origem: 'limite', equipamento: 3,
    sensor: 4, from: '2026-11-05T09:00', to: '2026-11-06T09:00' });
  await app.fetchAlertas();
  const query = new URL(urls[0]).searchParams;
  for (const [key, value] of Object.entries({ search: 'motor', nivel: 'baixo', origem: 'limite', equipamento: '3', sensor: '4', equipamento__empresa: '2' }))
    assert.equal(query.get(key), value);
  assert.equal(query.get('data_de'), new Date('2026-11-05T09:00').toISOString());
  assert.equal(query.get('data_ate'), new Date('2026-11-06T09:00').toISOString());
  assert.equal(query.has('status'), false);
  assert.deepEqual(Array.from(app.lists.alertas, a => a.id), [8, 7]);
  assert.equal(app.alertHistory.count, 3);
  await app.fetchPage('alertas', app.pages.alertas.next);
  assert.equal(app.lists.alertas[0].id, 6);
  assert.match(app.alertHistory.url, /offset=2/);
});

test('histórico explica período inválido e descarta consultas atrasadas', async () => {
  let release;
  let calls = 0;
  const { app, urls } = fixture(() => ++calls === 1 ? new Promise(resolve => { release = resolve; })
    : { count: 1, results: [{ id: 2 }] });
  Object.assign(app.filters.alertas, { from: '2026-11-06T09:00', to: '2026-11-05T09:00' });
  await app.fetchAlertas();
  assert.equal(urls.length, 0);
  assert.match(app.alertHistory.error, /inicial/);
  Object.assign(app.filters.alertas, { from: '', to: '' });
  const old = app.fetchAlertas();
  app.filters.alertas.sensor = 2;
  await app.fetchAlertas();
  release({ count: 1, results: [{ id: 1 }] });
  await old;
  assert.equal(app.lists.alertas[0].id, 2);
  assert.equal(app.alertHistory.busy, false);
});

test('detalhe usa todas as amostras da detecção sem misturar o acompanhamento atual', async () => {
  const samples = Array.from({ length: 50 }, (_, i) => ({ valor: i, timestamp: new Date(2026, 10, 6, 8, i).toISOString() }));
  const record = { id: 1, dados_deteccao: { leituras: samples, sensor_nome: 'Original' }, dados_analise: { ultimo_valor: 200 } };
  const { app } = fixture(() => record);
  await app.openAlertaDetails({ id: 1 });
  assert.equal(app.alertReadings.value.length, 50);
  assert.equal(app.alertChart.value.dots.length, 50);
  assert.equal(app.alertChart.value.dots[0].v, 0);
  assert.equal(app.alertChart.value.dots[49].v, 49);
  assert.equal(app.alertEvidence.value.sensor_nome, 'Original');
});

test('gráfico da detecção preserva intervalos reais e os limites configurados na abertura', async () => {
  const start = new Date('2026-11-06T09:00:00Z').getTime();
  const readings = [0, 1, 10].map((minutes, index) => ({ valor: 60 + index * 5,
    timestamp: new Date(start + minutes * 60000).toISOString() }));
  const { app } = fixture(() => ({ id: 1, dados_deteccao: { leituras: readings, limite_operacional: 100,
    analise: { limites_pct: { baixo: 70, medio: 85, critico: 100 } } } }));
  await app.openAlertaDetails({ id: 1 });
  assert.deepEqual(Array.from(app.alertChart.value.dots, point => point.x), [0, 64, 640]);
  assert.equal(app.alertChart.value.highValue, 100);
  assert.deepEqual(Array.from(app.alertChart.value.thresholds, row => row.value), [70, 85, 100]);
  assert.ok(app.alertChart.value.thresholds.every(row => row.y >= 0 && row.y <= 180));
});

test('fechar detalhe ou sair impede reaparecimento de resposta antiga', async () => {
  let release;
  const { app } = fixture(() => new Promise(resolve => { release = resolve; }));
  const request = app.openAlertaDetails({ id: 1 });
  app.closeAlertaDetails();
  release({ id: 1 }); await request;
  assert.equal(app.alertHistory.detail, null);
  const pending = app.fetchAlertas();
  app.logout();
  release({ count: 1, results: [{ id: 99 }] }); await pending;
  assert.equal(app.lists.alertas.length, 0);
});

test('abrir O.S. consulta exclusivamente o vínculo sem assumir nem alterar a ordem', async () => {
  const methods = [];
  const { app, urls } = fixture((url, options) => {
    methods.push(options.method || 'GET');
    if (url.includes('/ordens-servico/42/')) return { id: 42, equipamento: 3, status: 'pendente' };
    if (url.includes('/equipamentos/3/')) return { id: 3, nome: 'Motor' };
    return { results: [] };
  });
  await app.openAlertaOS({ id: 8, equipamento: 3, ordem_servico_id: 42 });
  assert.ok(urls.some(url => url.includes('/api/ordens-servico/42/')));
  assert.equal(app.orderDetail.order.id, 42);
  assert.equal(app.orderDetail.open, true);
  assert.equal(app.equipModal.open, false);
  assert.equal(urls.length, 1);
  assert.ok(methods.every(method => method === 'GET'));
});

test('atalho do alerta abre o sensor correto e mantém filtros independentes do histórico', async () => {
  const { app, urls } = fixture(() => ({ count: 0, results: [] }));
  app.filters.alertas.search = 'ocorrência antiga';
  await app.openAlertaSensor({ id: 8, equipamento: 3, sensor: 4 });
  assert.equal(app.view.value, 'telemetria');
  assert.equal(app.telemetry.equipment, 3);
  assert.equal(app.telemetry.sensor, 4);
  assert.equal(app.filters.alertas.search, 'ocorrência antiga');
  assert.ok(urls.some(url => url.includes('/leituras/?') && new URL(url).searchParams.get('sensor') === '4'));
});

test('dashboard conta ocorrências das últimas 24h além dos seis registros exibidos', async () => {
  const { app, urls } = fixture(url => {
    if (url.includes('/dashboards/resumo/')) return { resumo_status: { total: 1 },
      alertas_ativos: { total: 123 }, alertas_24h: { total: 40, baixo: 30, medio: 8, critico: 2 },
      alertas_recentes: [{ id: 10, nivel: 'baixo' }], detalhes_equipamentos: [] };
    return { count: 0, results: [] };
  });
  app.me.value = { tipo_usuario: 'gestor' };
  await app.fetchDashboard();
  assert.equal(app.alertCount.value, 40);
  assert.equal(app.kpis.value.alertas_24h, 40);
  assert.equal(app.dashAlerts.value.length, 1);
  assert.equal(app.chartAlertNivel.value.find(row => row.label === 'Baixo').pct, 100);
  const alerts = urls.filter(url => url.includes('/api/alertas/?'));
  assert.equal(alerts.length, 0); // Contagem e lista usam o mesmo resumo completo do servidor.
});

test('histórico do equipamento usa o relacionamento, mesmo com título renomeado', () => {
  const { app } = fixture(() => ({}));
  app.equipModal.ordens = [{ id: 1, titulo: 'Inspecionar motor', alerta_origem: 9 },
    { id: 2, titulo: 'Alerta percebido por pessoa', alerta_origem: null }];
  app.equipModal.osFilter = 'automaticas';
  assert.deepEqual(Array.from(app.equipModalFilteredOrdens.value, row => row.id), [1]);
  app.equipModal.osFilter = 'manuais';
  assert.deepEqual(Array.from(app.equipModalFilteredOrdens.value, row => row.id), [2]);
});

test('dashboard usa resumo completo com filtros e carrega desempenho somente ao expandir', async () => {
  const { app, urls } = fixture(() => ({ resumo_status: { total: 300 }, os_abertas: 250, alertas_ativos: { critico: 8 }, atualizado_em: '2026-11-06T12:00:00Z' }));
  app.me.value = { id: 1, tipo_usuario: 'gestor' };
  app.dashSetor.value = 'Produção'; app.dashEquipamento.value = 7;
  await app.fetchDashboard();
  assert.equal(app.dashboardCards.value[2].value, 250);
  let query = new URL(urls[0]).searchParams;
  assert.equal(query.get('incluir_desempenho'), 'false');
  assert.equal(query.get('setor'), 'Produção'); assert.equal(query.get('equipamento_id'), '7');
  app.performanceOpen.value = true; await app.fetchDashboard();
  query = new URL(urls[1]).searchParams;
  assert.equal(query.get('incluir_desempenho'), 'true');
  assert.equal(urls.filter(url => url.includes('/leituras/')).length, 0);
});

test('dashboard descarta resposta da empresa anterior e preserva dados após falha', async () => {
  let release, calls = 0, fail = false;
  const { app } = fixture(() => {
    if (fail) throw Error('offline');
    return ++calls === 1 ? new Promise(resolve => { release = resolve; }) : { os_abertas: 3, resumo_status: { total: 1 } };
  });
  app.me.value = { id: 1, tipo_usuario: 'admin' }; app.globalEmpresa.value = 1;
  const old = app.fetchDashboard(); app.globalEmpresa.value = 2; await app.fetchDashboard();
  release({ os_abertas: 99 }); await old;
  assert.equal(app.dashboardSummary.value.os_abertas, 3);
  const previous = app.dashboardSummary.value; fail = true; await app.fetchDashboard();
  assert.equal(app.dashboardSummary.value, previous); assert.ok(app.dashboardKpisError.value);
});

test('atalhos de ordens mantêm abertas e responsável na consulta, inclusive com resposta lenta', async () => {
  const { app, urls } = fixture(() => ({ results: [], count: 0 }));
  app.me.value = { id: 9, tipo_usuario: 'tecnico' };
  await app.openDashboardOrders('livres');
  const url = urls.find(url => url.includes('/ordens-servico/'));
  const params = new URL(url).searchParams;
  assert.equal(params.get('abertas'), 'true'); assert.equal(params.get('responsavel_escopo'), 'livres');
  assert.equal(app.filters.ordens.status, 'abertas');
  assert.equal(app.filters.ordens.responsavel_escopo, 'livres');
});

test('login técnico não depende de endpoints administrativos de empresas ou usuários', async () => {
  const { app, urls } = fixture(url => {
    if (url.includes('/auth/login/')) return { access: 'test-access', refresh: 'test-refresh' };
    if (url.includes('/auth/me/')) return { id: 9, tipo_usuario: 'tecnico', empresa: 3 };
    if (url.includes('/dashboards/resumo/')) return { empresa_atual: { id: 3, nome: 'Empresa técnica' }, minhas_ordens: 2 };
    if (url.includes('/empresas/') || url.includes('/usuarios/')) throw Error('forbidden');
    return { results: [], count: 0 };
  });
  await app.doLogin();
  for (let i=0;i<15;i++) await Promise.resolve();
  assert.equal(app.loginError.value, '');
  assert.equal(app.dashboardSummary.value.minhas_ordens, 2);
  assert.equal(app.lists.empresas[0].nome, 'Empresa técnica');
  await app.fetchOrdens();
  assert.equal(urls.filter(url => url.includes('/empresas/') || url.includes('/usuarios/')).length, 0);
});
