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
  const context = {
    Vue: { ref: value => ({ value }), reactive: value => value,
      computed: getter => ({ get value() { return getter(); } }), watch() {}, onMounted() {},
      nextTick: callback => callback?.(), createApp: options => ({ mount() { app = options.setup(); } }) },
    localStorage: { getItem() { return ''; }, setItem() {}, removeItem() {} },
    document: { documentElement: { classList: { add() {}, remove() {} } }, getElementById() {} },
    window: {}, console, URLSearchParams, Date, setTimeout, clearTimeout,
    fetch: async url => { urls.push(url); const body = await handler(url); return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => body }; },
  };
  vm.runInNewContext(source, context);
  return { app, urls };
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
  const sample = (id, condition) => ({ sensor_id: id, sensor_info: { equipamento_id: 1 },
    analysis_enabled: condition !== 'disabled', insufficient_data: condition === 'insufficient',
    is_anomalous: condition === 'anomalous', direction: 'stable' });
  const rows = [sample(1,'anomalous'), sample(2,'normal'), sample(3,'insufficient'), sample(4,'disabled')];
  const { app, urls } = fixture(() => rows);
  Object.assign(app.telemetry, { tab: 'tendencias', size: 2 });
  await app.fetchTelemetria();
  assert.equal(app.telemetryCount.value, 4);
  assert.equal(app.telemetrySummary.value.disabled, 1);
  app.changeTelemetryPage(1);
  assert.equal(app.telemetryRows.value[0].sensor_id, 3);
  app.telemetry.condition = 'insufficient'; app.applyTelemetryFilters();
  assert.equal(app.telemetryCount.value, 1);
  assert.equal(app.telemetryRows.value[0].sensor_id, 3);
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
