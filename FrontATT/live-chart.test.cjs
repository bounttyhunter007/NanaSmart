const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require('node:path').join(__dirname, 'live-chart.js'), 'utf8');
const stamp = n => new Date(Date.UTC(2026, 10, 6, 12) + n * 1000).toISOString();
const reading = (id, seconds, value = 40) => ({ id, sensor: 1, timestamp: stamp(seconds), valor: value });
const sensor = { id: 1, nome: 'Temperatura', ativo: true, unidade_medida: '°C', limite_alerta: 100 };

function fixture(handler, equipmentOptions = [{ id: 1, nome: 'Bomba' }]) {
  const watchers = [], mounts = [], unmounts = [], timers = new Map(), listeners = new Map();
  const urls = [];
  let id = 0;
  const context = {
    Vue: { ref: value => ({ value }), computed: getter => ({ get value() { return getter(); } }),
      watch(source, callback) { const get = typeof source === 'function' ? source : Array.isArray(source) ? () => source.map(s => s.value) : () => source.value; watchers.push({ get, callback, last: JSON.stringify(get()) }); },
      onMounted: fn => mounts.push(fn), onUnmounted: fn => unmounts.push(fn) },
    Date, Intl, URLSearchParams, performance: { now: () => 0 },
    document: { hidden: false, addEventListener: (key, fn) => listeners.set(key, fn), removeEventListener: key => listeners.delete(key) },
    matchMedia: () => ({ matches: true }), requestAnimationFrame() { throw new Error('Motion reduction should skip animation'); }, cancelAnimationFrame() {},
    setInterval(fn, ms) { timers.set(++id, { fn, ms }); return id; }, clearInterval: id => timers.delete(id),
  };
  vm.runInNewContext(source, context);
  const api = context.NanaLiveChart;
  const props = { empresa: '', equipamentos: equipmentOptions, api: async url => {
    urls.push(url);
    if (url.includes('/sensores/')) return { results: [sensor] };
    return handler(url);
  } };
  const app = api.component.setup(props);
  async function flush() {
    for (let i = 0; i < 15; i++) {
      for (const w of watchers) { const value = w.get(), key = JSON.stringify(value); if (key !== w.last) { w.last = key; w.callback(value); } }
      await Promise.resolve();
    }
  }
  return { context, api, app, props, urls, timers, document: context.document, listeners, flush,
    async mount() { mounts.forEach(fn => fn()); await flush(); }, unmount() { unmounts.forEach(fn => fn()); } };
}

test('timestamps preserve spacing for 2s, 10s and 10min sensors, including irregular cadence', () => {
  const { api } = fixture(() => ({}));
  for (const interval of [2, 10, 600]) {
    const rows = Array.from({ length: 60 }, (_, i) => reading(i + 1, i * interval));
    const plot = api.chart(rows, sensor);
    assert.equal(plot.points.length, 60);
    assert.equal(plot.domain.to - plot.domain.from, 59 * interval * 1000);
  }
  const p = api.chart([reading(1, 0), reading(2, 2), reading(3, 20)], sensor);
  assert.ok(Math.abs((p.points[1].x - p.points[0].x) / (p.points[2].x - p.points[0].x) - .1) < 1e-10);
});

test('poll is 5s, unchanged responses keep exactly the same chart, equal values add real points', async () => {
  let batch = [reading(1, 0)];
  const f = fixture(() => ({ results: [...batch].reverse() }));
  await f.mount();
  assert.equal(f.app.rows.value.length, 1);
  assert.equal([...f.timers.values()].filter(t => t.ms === 5000).length, 1);
  const unchanged = f.app.displayed.value;
  await f.app.refresh();
  assert.equal(f.app.displayed.value, unchanged);
  batch.push(reading(2, 2), reading(3, 4));
  await f.app.refresh();
  assert.deepEqual(Array.from(f.app.rows.value, r => r.id), [1, 2, 3]);
  assert.equal(f.app.displayed.value.points[0].y, f.app.displayed.value.points[2].y);
  const latest = f.app.displayed.value;
  await f.app.refresh();
  assert.equal(f.app.displayed.value, latest);
  f.unmount(); assert.equal(f.timers.size, 0); assert.equal(f.listeners.size, 0);
});

test('slow sensor keeps old measurements visible with no extension to current clock', async () => {
  const batch = [reading(1, 0), reading(2, 600)];
  const f = fixture(() => ({ results: [...batch].reverse() }));
  await f.mount();
  assert.equal(f.app.displayed.value.domain.to, Date.parse(stamp(600)));
  const previous = f.app.displayed.value;
  for (let n = 0; n < 5; n++) await f.app.refresh();
  assert.equal(f.app.displayed.value, previous);
  assert.ok(f.app.age.value);
});

test('pause, hidden page and unmount stop requests; resume fetches fresh data', async () => {
  const f = fixture(() => ({ results: [reading(1, 0)] })); await f.mount();
  f.app.togglePause(); const count = f.urls.length;
  await f.app.refresh(); assert.equal(f.urls.length, count); assert.equal(f.timers.size, 0);
  f.app.togglePause(); await f.flush(); assert.ok(f.urls.length > count);
  f.document.hidden = true; f.listeners.get('visibilitychange')();
  const hiddenCount = f.urls.length; await f.app.refresh();
  assert.equal(f.urls.length, hiddenCount); assert.equal(f.timers.size, 0);
  f.document.hidden = false; f.listeners.get('visibilitychange')(); await f.flush();
  assert.ok(f.urls.length > hiddenCount); f.unmount();
});

test('overlapping requests are skipped; error preserves data and a retry clears it', async () => {
  let deferred, fail = false;
  const f = fixture(() => { if (fail) throw Error('offline'); return deferred ? new Promise(resolve => { deferred = resolve; }) : { results: [reading(1, 0)] }; });
  await f.mount(); deferred = true;
  const pending = f.app.refresh(), before = f.urls.length;
  await f.app.refresh(); assert.equal(f.urls.length, before);
  deferred({ results: [reading(2, 2), reading(1, 0)] }); deferred = null; await pending;
  const previous = f.app.displayed.value; fail = true; await f.app.refresh();
  assert.ok(f.app.error.value); assert.equal(f.app.displayed.value, previous);
  fail = false; await f.app.refresh(); assert.equal(f.app.error.value, ''); f.unmount();
});

test('switching sensor discards the previous pending response and resets scale', async () => {
  let release, wait = false;
  const f = fixture(url => {
    if (new URL('http://local' + url).searchParams.get('sensor') === '2') return { results: [{ ...reading(20, 10, -20), sensor: 2 }] };
    return wait ? new Promise(resolve => { release = resolve; }) : { results: [reading(1, 0, 500)] };
  });
  await f.mount(); wait = true; const old = f.app.refresh();
  f.app.sensors.value.push({ ...sensor, id: 2, limite_alerta: 10 }); f.app.sensorId.value = 2; await f.flush();
  release({ results: [reading(99, 200, 999)] }); await old;
  assert.equal(f.app.rows.value[0].id, 20); assert.ok(f.app.displayed.value.domain.max < 100); f.unmount();
});

test('zero, negative and constant values are valid; invalid readings and duplicate IDs are removed', () => {
  const { api } = fixture(() => ({}));
  const rows = api.normalize([reading(1, 0, 0), reading(2, 10, -2), reading(2, 10, -2), reading(3, 20, NaN), reading(4, 30, null)]);
  assert.equal(rows.length, 2); assert.equal(rows[0].valor, 0);
  const plot = api.chart(rows, sensor);
  assert.ok(plot.points.every(p => Number.isFinite(p.y)));
  assert.ok(plot.limits.every(t => t.y > 42 && t.y < 230));
  assert.equal(api.thresholds({ ...sensor, limite_alerta: 0 }).length, 0);
  assert.equal(api.thresholds({ ...sensor, limite_alerta_baixo_pct: 0 })[0].value, 0);
});

test('fixed window ends at last reading, snapshots pages and warns at 1000 measurements', async () => {
  const { api } = fixture(() => ({})); let page = 0; const urls = [];
  const result = await api.readings(async url => {
    urls.push(url);
    if (++page === 1) return { results: [reading(1200, 1200)], count: 1200 };
    const offset = (page - 2) * 200;
    return { count: 1200, results: Array.from({ length: 200 }, (_, i) => reading(1200 - offset - i, 1200 - offset - i)), next: offset < 1000 ? '/api/telemetria/leituras/?sensor=1&id_ate=1200&offset=' + (offset + 200) : null };
  }, 1, '60');
  assert.equal(result.rows.length, 1000); assert.equal(result.truncated, true);
  const params = new URL('http://local' + urls[1]).searchParams;
  assert.equal(params.get('timestamp_ate'), stamp(1200)); assert.equal(params.get('id_ate'), '1200');
});

test('multiple equipment options require an explicit choice and do not poll', async () => {
  const f = fixture(() => ({}), [{ id: 1, nome: 'A' }, { id: 2, nome: 'B' }]); await f.mount();
  assert.equal(f.app.equipment.value, ''); assert.equal(f.urls.length, 0); assert.equal(f.timers.size, 0); f.unmount();
});

test('unmounted pending request never restores data or timers', async () => {
  let release;
  const f = fixture(() => new Promise(resolve => { release = resolve; })); await f.mount();
  f.unmount(); release({ results: [reading(10, 10)] }); await f.flush();
  assert.equal(f.app.rows.value.length, 0); assert.equal(f.timers.size, 0);
});


test('animated updates finish with all new points and synchronized axes and limits', async () => {
  let batch = [reading(1,0,40), reading(2,2,42)];
  const f = fixture(() => ({ results: [...batch].reverse() }));
  const frames = new Map(); let nextId=0;
  f.context.matchMedia = () => ({ matches:false });
  f.context.requestAnimationFrame = callback => { frames.set(++nextId,callback); return nextId; };
  f.context.cancelAnimationFrame = id => frames.delete(id);
  await f.mount();
  batch.push(reading(3,4,105),reading(4,6,120));
  await f.app.refresh();
  assert.equal(frames.size,1);
  const first = frames.keys().next().value, halfway=frames.get(first); frames.delete(first); halfway(150);
  assert.equal(f.app.displayed.value.points.length,4);
  const second = frames.keys().next().value, finish=frames.get(second); frames.delete(second); finish(300);
  const plot=f.app.displayed.value;
  assert.equal(plot.points.length,4);
  assert.equal(plot.domain.to,Date.parse(stamp(6)));
  assert.ok(plot.domain.max>120);
  assert.ok(plot.points[3].y < plot.limits[2].y);
  assert.equal(frames.size,0);
  f.unmount();
});

test('regression respects irregular timing, repeated timestamps and stable values', () => {
  const { api } = fixture(() => ({}));
  const fit = api.fitLine([reading(1,0,40),reading(2,2,41),reading(3,20,50)]);
  assert.equal(fit.length,2); assert.equal(fit[0].timestamp,stamp(0)); assert.equal(fit[1].timestamp,stamp(20));
  assert.ok(Math.abs(fit[0].valor-40)<1e-9); assert.ok(Math.abs(fit[1].valor-50)<1e-9);
  assert.equal(api.fitLine([reading(1,0),reading(2,0),reading(3,10)]).length,0);
  const stable=api.fitLine([reading(1,0,0),reading(2,10,0),reading(3,600,0)]);
  assert.equal(stable[0].valor,0); assert.equal(stable[1].valor,0);
});

test('trend scale includes fitted endpoints and never extends into future time', () => {
  const { api } = fixture(() => ({}));
  const rows=[reading(1,0,0),reading(2,1,0),reading(3,2,100)], fit=api.fitLine(rows);
  const plot=api.chart(rows,null,null,'auto',null,false,fit);
  assert.ok(fit[0].valor<0); assert.ok(plot.domain.min<fit[0].valor);
  assert.equal(plot.domain.to,Date.parse(rows[2].timestamp));
  assert.ok(plot.trendPath); assert.equal(plot.points.length,3);
});

test('live trend is optional, uses the displayed window and adds no polling requests', async () => {
  let batch=[reading(1,0,40),reading(2,2,41),reading(3,4,43)];
  const f=fixture(() => ({results:[...batch].reverse()})); await f.mount();
  assert.equal(f.app.displayed.value.trendPath,''); const calls=f.urls.length;
  f.app.showTrend.value=true; await f.flush();
  assert.ok(f.app.displayed.value.trendPath); assert.equal(f.urls.length,calls);
  const previous=f.app.displayed.value; await f.app.refresh(); assert.equal(f.app.displayed.value,previous);
  batch.push(reading(4,6,48)); await f.app.refresh();
  assert.equal(f.app.fitted.value[1].timestamp,stamp(6)); assert.equal(f.app.rows.value.length,4);
  f.app.showTrend.value=false; await f.flush(); assert.equal(f.app.displayed.value.trendPath,''); f.unmount();
});

test('official sample draws the server fit only with sufficient enabled analysis', () => {
  const { api }=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,45),reading(3,1800,55)];
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',regression_line:api.fitLine(rows)};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.fitted.value.length,2); assert.ok(sample.plot.value.trendPath);
  assert.equal(sample.plot.value.domain.to,Date.parse(stamp(1800)));
  analysis.insufficient_data=true; assert.equal(sample.plot.value.trendPath,'');
  analysis.insufficient_data=false; analysis.analysis_enabled=false;
  assert.equal(sample.plot.value.trendPath,''); assert.match(sample.fitMessage.value,/desativada/);
});

test('forecast time is shown only for a valid future projection anchored to the last sample', () => {
  const { api }=fixture(() => ({}));
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'increasing',limite_operacional:100,
    readings_summary:[reading(1,0),reading(2,600),reading(3,1200)],analyzed_at:stamp(1300),projected_breach_at:stamp(4800)};
  assert.equal(api.projectionSummary(analysis).reference,stamp(1200));
  assert.equal(api.projectionSummary(analysis).at,stamp(4800));
  for (const patch of [{direction:'decreasing'},{direction:'stable'},{analysis_enabled:false},{insufficient_data:true},
    {data_quality:'insufficient'},{projected_breach_at:stamp(1250)},{projected_breach_at:null},{limite_operacional:0}]) {
    assert.equal(api.projectionSummary({...analysis,...patch}),null);
  }
});

test('future segment starts at last real point, reserves history and never adds measurements', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,3600,50),reading(3,7200,60)],fit=api.fitLine(rows);
  const future=api.projectForward(rows,fit,{limit:100});
  const plot=api.chart(rows,sensor,null,'auto',null,false,fit,future);
  assert.equal(future.horizon,3600000);
  assert.equal(plot.points.length,3);
  assert.equal(plot.points[2].timestamp,stamp(7200));
  assert.equal(plot.projection.points[0].x,plot.points[2].x);
  assert.equal(plot.projection.points[0].y,plot.points[2].y);
  assert.ok(plot.projection.end.x>plot.points[2].x);
  assert.ok(Math.abs((plot.projection.startX-plot.left)/(plot.right-plot.left)-2/3)<1e-9);
  assert.equal(plot.domain.to,Date.parse(stamp(10800)));
  assert.ok(plot.projection.path); assert.ok(plot.path);
});

test('limit is marked only when reached inside bounded horizon and forecast stops there', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,3600,60),reading(3,7200,80)],fit=api.fitLine(rows);
  const reached=api.projectForward(rows,fit,{limit:90});
  assert.equal(reached.reachesLimit,true);
  assert.equal(reached.points[1].timestamp,stamp(9000));
  assert.equal(reached.points[1].valor,90);
  const far=api.projectForward(rows,fit,{limit:200});
  assert.equal(far.reachesLimit,false); assert.equal(far.limitOutside,true);
  assert.equal(far.points[1].valor,100);
  assert.equal(far.points[1].timestamp,stamp(10800));
  assert.equal(api.projectForward(rows,fit,{limit:null}).reachesLimit,false);
});

test('weak, flat, insufficient or mismatched samples do not generate a future curve', () => {
  const {api}=fixture(() => ({}));
  for (const values of [[40,40,40],[40,40,80,40,40],[40,60,41,59,42]]) {
    const rows=values.map((v,i)=>reading(i+1,i*10,v));
    assert.equal(api.projectForward(rows,api.fitLine(rows),{limit:100}),null);
  }
  const rows=[reading(1,0,40),reading(2,10,45),reading(3,20,50)], fit=api.fitLine(rows);
  assert.equal(api.projectForward(rows.slice(1),fit),null);
  assert.equal(api.projectForward(rows,[{...fit[0],timestamp:stamp(-10)},fit[1]]),null);
  for (const patch of [{analysis_enabled:false},{insufficient_data:true},{data_quality:'insufficient'},{direction:'stable'},{direction:'decreasing'}]) {
    const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'increasing',...patch};
    assert.equal(api.projectForward(rows,fit,{analysis,limit:100}),null);
  }
});

test('consistent falling trend projects downward without inventing an upper limit breach', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,80),reading(2,3600,70),reading(3,7200,60)];
  const future=api.projectForward(rows,api.fitLine(rows),{limit:100});
  assert.equal(future.points[1].valor,50); assert.equal(future.reachesLimit,false); assert.equal(future.limitOutside,false);
});

test('very long history caps future horizon at one day', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,10),reading(2,864000,20),reading(3,1728000,30)];
  const future=api.projectForward(rows,api.fitLine(rows));
  assert.equal(future.horizon,86400000);
  assert.ok(future.to-Date.parse(rows[2].timestamp)<=86400000);
});

test('live future stays stationary without new data and rebuilds with all new measurements', async () => {
  let batch=[reading(1,0,40),reading(2,10,45),reading(3,20,50)];
  const f=fixture(() => ({results:[...batch].reverse()})); await f.mount();
  f.app.showTrend.value=true; await f.flush();
  assert.ok(f.app.displayed.value.projection);
  const previous=f.app.displayed.value;
  await f.app.refresh(); assert.equal(f.app.displayed.value,previous);
  batch.push(reading(4,30,55),reading(5,40,60)); await f.app.refresh();
  assert.equal(f.app.rows.value.length,5);
  assert.equal(f.app.displayed.value.projection.points[0].timestamp,stamp(40));
  assert.equal(f.app.displayed.value.points[4].timestamp,stamp(40));
  f.app.showTrend.value=false; await f.flush();
  assert.equal(f.app.displayed.value.projection,null);
  assert.equal(f.app.displayed.value.domain.to,Date.parse(stamp(40)));
  f.unmount();
});

test('official sample uses backend direction and keeps observed timestamps outside projected points', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,3600,60),reading(3,7200,80)];
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'increasing',regression_line:api.fitLine(rows)};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.ok(sample.plot.value.projection);
  assert.equal(sample.plot.value.points.length,rows.length);
  assert.equal(sample.plot.value.points[2].timestamp,stamp(7200));
  analysis.direction='stable';
  assert.equal(sample.plot.value.projection,null);
  assert.ok(sample.plot.value.trendPath);
});

test('animated projection stays synchronized with real points and final time domain', async () => {
  let batch=[reading(1,0,40),reading(2,10,45),reading(3,20,50)];
  const f=fixture(() => ({results:[...batch].reverse()}));
  const frames=new Map(); let nextId=0;
  f.context.matchMedia=()=>({matches:false});
  f.context.requestAnimationFrame=fn=>{frames.set(++nextId,fn);return nextId;};
  f.context.cancelAnimationFrame=id=>frames.delete(id);
  await f.mount(); f.app.showTrend.value=true; await f.flush();
  batch.push(reading(4,30,55),reading(5,40,60)); await f.app.refresh();
  let key=frames.keys().next().value,fn=frames.get(key);frames.delete(key);fn(150);
  assert.ok(f.app.displayed.value.projection.path);
  assert.ok(f.app.displayed.value.projection.startX<=f.app.displayed.value.right);
  key=frames.keys().next().value;fn=frames.get(key);frames.delete(key);fn(300);
  const plot=f.app.displayed.value;
  assert.equal(plot.points.length,5);
  assert.equal(plot.projection.points[0].x,plot.points[4].x);
  assert.equal(plot.projection.points[0].y,plot.points[4].y);
  assert.equal(plot.domain.to,Date.parse(stamp(60)));
  assert.equal(frames.size,0);f.unmount();
});

test('fixed history window remains anchored to real measurement with a separate future extension', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,60,45),reading(3,120,50)],fit=api.fitLine(rows);
  const future=api.projectForward(rows,fit);
  const plot=api.chart(rows,sensor,null,'5',null,false,fit,future);
  assert.equal(plot.domain.from,Date.parse(stamp(120))-300000);
  assert.equal(plot.domain.to,Date.parse(stamp(180)));
  assert.equal(plot.points[2].timestamp,stamp(120));
  assert.ok((plot.projection.startX-plot.left)/(plot.right-plot.left)>=2/3);
});
