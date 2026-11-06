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
      computed: getter => ({ get value() { return getter(); } }), watch() {}, onMounted() {}, onUnmounted(callback) { unmount.push(callback); },
      nextTick: callback => callback?.(), createApp: options => ({ mount() { app = options.setup(); } }) },
    localStorage: { getItem() { return ''; }, setItem() {}, removeItem() {} },
    document: { hidden: false, addEventListener() {}, removeEventListener() {}, documentElement: { classList: { add() {}, remove() {} } }, getElementById() {} },
    window: {}, console, URLSearchParams, Date, setTimeout, clearTimeout,
    setInterval(callback, ms) { const id = ++timerId; timers.set(id, { callback, ms }); return id; },
    clearInterval(id) { timers.delete(id); },
    fetch: async url => { urls.push(url); const body = await handler(url); return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => body }; },
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
  assert.equal(app.trendPage.equipment, ''); assert.equal(app.trendPage.sensor, '');
  assert.equal(app.trendCount.value, 2); assert.equal(app.trendPage.offset, 0);
  app.trendPage.equipment = 3; app.trendPage.sensor = 1; app.applyTrendFilters();
  assert.equal(app.trendCount.value, 1);
  assert.equal(app.telemetry.equipment, 99); assert.equal(app.telemetry.sensor, 999);
  app.telemetry.equipment = 100; await app.applyTelemetryFilters(true);
  assert.equal(app.trendPage.equipment, 3); assert.equal(app.trendPage.sensor, 1);
  assert.equal(app.trendCount.value, 1);
});
test('escolher equipamento em Tendências limpa apenas seu sensor e restringe opções', async () => {
  const other = anomaly(2); other.sensor_info.equipamento_id = 4; other.sensor_info.equipamento_nome = 'Bomba';
  const { app } = fixture(() => [anomaly(1), other]);
  await app.fetchTrends();
  app.telemetry.sensor = 88;
  Object.assign(app.trendPage, { equipment: 4, sensor: 1, offset: 20 });
  app.applyTrendFilters(true);
  assert.equal(app.trendPage.sensor, ''); assert.equal(app.trendPage.offset, 0);
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
