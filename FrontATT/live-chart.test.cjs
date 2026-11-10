const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require('node:path').join(__dirname, 'live-chart.js'), 'utf8');
const stamp = n => new Date(Date.UTC(2026, 10, 6, 12) + n * 1000).toISOString();
const reading = (id, seconds, value = 40) => ({ id, sensor: 1, timestamp: stamp(seconds), valor: value });
const sensor = { id: 1, nome: 'Temperatura', ativo: true, unidade_medida: '°C', limite_alerta: 100 };

function fixture(handler, equipmentOptions = [{ id: 1, nome: 'Bomba' }], extraProps = {}) {
  const watchers = [], mounts = [], unmounts = [], timers = new Map(), listeners = new Map();
  const urls = [], requests = [];
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
  const props = { empresa: '', equipamentos: equipmentOptions, ...extraProps, api: async (url,opts) => {
    urls.push(url);
    requests.push({url,opts});
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
  return { context, api, app, props, urls, requests, timers, document: context.document, listeners, flush,
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
  assert.ok(f.app.displayed.value.projection); assert.equal(f.app.displayed.value.trendPath,''); assert.equal(f.urls.length,calls);
  f.app.showHistoryFit.value=true; await f.flush(); assert.ok(f.app.displayed.value.trendPath);
  const previous=f.app.displayed.value; await f.app.refresh(); assert.equal(f.app.displayed.value,previous);
  batch.push(reading(4,6,48)); await f.app.refresh();
  assert.equal(f.app.fitted.value[1].timestamp,stamp(6)); assert.equal(f.app.rows.value.length,4);
  f.app.showTrend.value=false; await f.flush(); assert.equal(f.app.displayed.value.trendPath,''); f.unmount();
});

test('official sample shows a preliminary preview while awaiting operational criteria', () => {
  const { api }=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,45),reading(3,1800,55)];
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',regression_line:api.fitLine(rows)};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.fitted.value.length,2); assert.ok(sample.plot.value.projection.path);
  assert.equal(sample.plot.value.domain.to,Date.parse(stamp(2700)));
  analysis.insufficient_data=true; analysis.regression_line=null;
  assert.ok(sample.plot.value.projection.path); assert.equal(sample.plot.value.projection.kind,'preliminary');
  assert.equal(sample.plot.value.projection.reachesLimit,false);
  assert.match(sample.fitMessage.value,/preliminar/);
  analysis.insufficient_data=false; analysis.analysis_enabled=false;
  assert.equal(sample.plot.value.trendPath,''); assert.match(sample.fitMessage.value,/desativada/);
});

test('future area stays reserved when a confirmed trend stabilizes or awaits data', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,50),reading(3,1200,60)];
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'increasing',regression_line:api.fitLine(rows)};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.plot.value.trendPath,'');
  const end=sample.plot.value.domain.to, divider=sample.plot.value.future.startX;
  assert.ok(sample.plot.value.projection.path);
  sample.showHistoryFit.value=true; assert.ok(sample.plot.value.trendPath);
  sample.showHistoryFit.value=false;
  analysis.direction='stable';
  assert.equal(sample.plot.value.domain.to,end); assert.equal(sample.plot.value.future.startX,divider);
  assert.equal(sample.plot.value.trendPath,''); assert.equal(sample.plot.value.projection.kind,'preliminary');
  analysis.insufficient_data=true; analysis.regression_line=null;
  assert.ok(sample.plot.value.projection.path); assert.equal(sample.plot.value.domain.to,end);
});

test('forecast and limit leave vertical headroom and remain visible after real exceedance', () => {
  const {api}=fixture(() => ({}));
  for (const values of [[40,60,80],[80,100,120]]) {
    const rows=values.map((v,i)=>reading(i+1,i*600,v));
    const fit=api.fitLine(rows), future=api.projectForward(rows,fit,{limit:100});
    const plot=api.chart(rows,sensor,null,'auto',null,false,fit,future);
    assert.ok(plot.projection.end.y>55); assert.ok(plot.limits.every(t=>t.y>55));
    assert.ok(plot.points.every(p=>p.y>42 && p.y<230));
  }
});

test('scale recovers gradually after an obsolete high peak leaves the live window', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,45),reading(3,1200,50)];
  let envelope={min:0,max:1000};
  const first=api.chart(rows,sensor,envelope); assert.ok(first.domain.max<1000);
  for(let i=0;i<30;i++) envelope=api.chart(rows,sensor,envelope).domain;
  assert.ok(envelope.max<120); assert.ok(envelope.max>100);
});

test('sample uses sensor-specific alarm thresholds independently of forecast', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,10,40),reading(3,20,40)];
  const sample=api.sampleComponent.setup({readings:rows,sensor:{...sensor,limite_alerta_baixo_pct:60,limite_alerta_medio_pct:75,limite_alerta_critico_pct:90},
    analysis:{analysis_enabled:true,insufficient_data:true}});
  assert.deepEqual(Array.from(sample.limits.value,t=>t.value),[60,75,90]);
  assert.equal(sample.plot.value.limits.length,1); assert.equal(sample.plot.value.limits[0].value,100);
  assert.equal(sample.plot.value.projection.kind,'stable');
  assert.equal(sample.plot.value.projection.reachesLimit,false);
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

test('limit crossing is marked without truncating the forecast line', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,3600,60),reading(3,7200,80)],fit=api.fitLine(rows);
  const reached=api.projectForward(rows,fit,{limit:90});
  assert.equal(reached.reachesLimit,true);
  assert.equal(reached.breach.timestamp,stamp(9000));
  assert.equal(reached.breach.valor,90);
  assert.equal(reached.points[1].timestamp,stamp(10800));
  assert.equal(reached.points[1].valor,100);
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
  assert.equal(sample.plot.value.projection.kind,'preliminary');
  assert.ok(sample.plot.value.projection.path);
  assert.equal(sample.plot.value.projection.reachesLimit,false);
});

test('visual preview includes slow trends even before the minimum duration or sensitivity', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,10,40.001),reading(3,20,40.002)];
  const analysis={analysis_enabled:true,insufficient_data:true,data_quality:'insufficient',direction:'stable',
    config_used:{minimo_leituras:7,duracao_minima_minutos:30}};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.projected.value.kind,'preliminary');
  assert.ok(sample.projected.value.points[1].valor>40.002);
  assert.equal(sample.projected.value.points[0].timestamp,rows[2].timestamp);
  assert.match(sample.fitMessage.value,/7 leituras cobrindo 30 min/);
  assert.equal(sample.estimate.value,null);
  analysis.insufficient_data=false; analysis.data_quality='valid';
  assert.equal(sample.projected.value.kind,'preliminary');
  assert.ok(sample.plot.value.projection.path);
  assert.equal(analysis.direction,'stable'); assert.equal(analysis.insufficient_data,false);
});

test('flat readings produce a horizontal visual preview without a breach prediction', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,60),reading(2,600,60),reading(3,1200,60)];
  const preview=api.projectForward(rows,api.fitLine(rows),{visual:true,limit:100});
  assert.equal(preview.kind,'stable');
  assert.equal(preview.points[0].valor,60); assert.equal(preview.points[1].valor,60);
  assert.equal(preview.reachesLimit,false); assert.equal(preview.limitOutside,false);
  assert.match(api.projectionExplanation(preview),/horizontal/);
  const plot=api.chart(rows,sensor,null,'auto',null,false,[],preview);
  assert.equal(plot.projection.points[0].y,plot.projection.points[1].y);
});

test('oscillating readings keep a readable exploratory line without a time-to-limit claim', () => {
  const {api}=fixture(() => ({}));
  const rows=[40,60,41,59,42].map((valor,i)=>reading(i+1,i*600,valor));
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'stable',
    regression_line:api.fitLine(rows)};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.projected.value.kind,'low_confidence');
  assert.equal(sample.projected.value.horizon,1200000);
  assert.ok(sample.plot.value.projection.path);
  assert.equal(sample.projected.value.reachesLimit,false);
  assert.equal(sample.estimate.value,null);
  assert.match(sample.fitMessage.value,/baixa consistência/);
});

test('preview preserves source-quality failures and upgrades only after server confirmation', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,60),reading(3,1200,80)];
  const analysis={analysis_enabled:true,insufficient_data:false,data_quality:'valid',direction:'stable',
    regression_line:api.fitLine(rows),source_r_squared:.3,source_persistence_ratio:.5};
  const sample=api.sampleComponent.setup({readings:rows,sensor,analysis});
  assert.equal(sample.projected.value.kind,'low_confidence');
  assert.equal(sample.projected.value.reachesLimit,false);
  Object.assign(analysis,{direction:'increasing',source_r_squared:1,source_persistence_ratio:1});
  assert.equal(sample.projected.value.kind,'confirmed');
  assert.equal(sample.projected.value.reachesLimit,true);
  assert.equal(sample.projected.value.points[1].valor,100);
  analysis.analysis_enabled=false;
  assert.equal(sample.projected.value,null);
  assert.match(sample.fitMessage.value,/desativada/);
});

test('near-limit forecast spans the future region on desktop and mobile instead of collapsing into a dot', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,600,70),reading(3,1200,99.99)];
  const future=api.projectForward(rows,api.fitLine(rows),{visual:true,limit:100});
  assert.equal(future.reachesLimit,true);
  assert.ok(future.points[1].valor>100);
  for(const compact of [false,true]) {
    const plot=api.chart(rows,sensor,null,'auto',null,compact,[],future,{futureSpace:true,showFit:false});
    assert.ok(plot.projection.breach.x-plot.projection.startX<1);
    assert.equal(plot.projection.end.x,plot.right);
    assert.ok(plot.projection.end.x-plot.projection.startX>(compact?90:200));
    assert.ok(plot.projection.breach.x<plot.projection.end.x);
    assert.equal(plot.points.length,3);
    assert.ok(plot.projection.end.y>42);
  }
  assert.doesNotMatch(api.component.template,/forecast-endpoint/);
  assert.doesNotMatch(api.sampleComponent.template,/forecast-endpoint/);
});

test('a long selected window cannot compress a short live forecast into a few pixels', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,10,45),reading(3,20,50)];
  const future=api.projectForward(rows,api.fitLine(rows),{visual:true,limit:100});
  for(const compact of [false,true]) {
    const plot=api.chart(rows,sensor,null,'360',null,compact,[],future,{futureSpace:true});
    assert.equal(plot.domain.from,Date.parse(stamp(0)));
    assert.equal(plot.domain.to,Date.parse(stamp(30)));
    assert.equal(plot.projection.end.x,plot.right);
    assert.ok(Math.abs(plot.projection.width/(plot.right-plot.left)-1/3)<1e-9);
  }
  const historyOnly=api.chart(rows,sensor,null,'360');
  assert.equal(historyOnly.domain.from,Date.parse(stamp(20))-360*60000);
});

test('visual mode still requires three unique valid timestamps and matching fit endpoints', () => {
  const {api}=fixture(() => ({}));
  const rows=[reading(1,0,40),reading(2,10,50),reading(3,20,60)],fit=api.fitLine(rows);
  for(const sample of [[],rows.slice(0,2),[rows[0],rows[1],{...rows[1],id:9}],
    [rows[0],rows[1],{...rows[2],valor:null}]]) {
    assert.equal(api.projectForward(sample,fit,{visual:true}),null);
  }
  assert.equal(api.projectForward(rows,[{...fit[0],timestamp:stamp(-10)},fit[1]],{visual:true}),null);
  assert.equal(api.projectForward(rows,fit,{visual:true,analysis:{analysis_enabled:false}}),null);
});

test('live preview stays visible when the next sample becomes constant', async () => {
  let batch=[reading(1,0,40),reading(2,60,50),reading(3,120,60)];
  const f=fixture(() => ({results:[...batch].reverse()})); await f.mount();
  f.app.showTrend.value=true; await f.flush(); assert.ok(f.app.displayed.value.projection.path);
  batch=[reading(4,180,60),reading(5,240,60),reading(6,300,60)];
  await f.app.refresh();
  assert.equal(f.app.projected.value.kind,'stable');
  assert.ok(f.app.displayed.value.projection.path);
  assert.equal(f.app.displayed.value.points.length,3);
  f.unmount();
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

test('live window excludes old seed history and slides as readings arrive', async () => {
  let batch=[reading(1,-7200,120),reading(2,-3600,110),reading(3,0,70),reading(4,30,70.1),reading(5,60,70.2)];
  const f=fixture(()=>({results:[...batch].reverse()})); await f.mount();
  assert.deepEqual(Array.from(f.app.rows.value,r=>r.id),[3,4,5]);
  assert.equal(f.app.displayed.value.domain.from,Date.parse(stamp(0)));
  f.app.showTrend.value=true; await f.flush();
  assert.ok(f.app.fitted.value[1].valor>f.app.fitted.value[0].valor);
  batch.push(reading(6,350,71),reading(7,380,70.5),reading(8,410,70));
  const previous=f.app.displayed.value;
  await f.app.refresh();
  assert.deepEqual(Array.from(f.app.rows.value,r=>r.id),[6,7,8]);
  assert.ok(f.app.fitted.value[1].valor<f.app.fitted.value[0].valor);
  assert.equal(f.app.projected.value.points[0].timestamp,stamp(410));
  assert.ok(f.app.displayed.value.domain.from>previous.domain.from);
  assert.equal(f.app.received.value,3);
  assert.ok(f.requests.filter(r=>r.url.includes('/leituras/')).every(r=>r.opts.cache==='no-store'));
  await f.app.refresh(); assert.equal(f.app.received.value,0);
  f.unmount();
});

test('focus scale keeps small changes near a limit readable and labels distant thresholds separately', () => {
  const {api}=fixture(()=>({}));
  const rows=[reading(1,0,70),reading(2,5,70.01),reading(3,10,70.03)];
  const focused=api.chart(rows,sensor,null,'auto',null,false,[],null,{focus:true});
  assert.ok(focused.domain.max-focused.domain.min<.3);
  assert.ok(Math.abs(focused.points[0].y-focused.points[2].y)>20);
  assert.equal(focused.limits.find(t=>t.name==='Baixo').visible,true);
  assert.deepEqual(Array.from(focused.offscaleLimits,t=>t.name),['Médio','Crítico']);
  assert.ok(focused.offscaleLimits.every(t=>t.position==='acima'));
  const full=api.chart(rows,sensor);
  assert.ok(full.limits.every(t=>t.visible)); assert.ok(full.domain.max>100);
});

test('a peak outside the current window cannot keep the focused scale compressed', () => {
  const {api}=fixture(()=>({}));
  const rows=[reading(1,0,40),reading(2,5,40.1),reading(3,10,40.2)];
  const plot=api.chart(rows,sensor,{min:0,max:1000},'auto',null,false,[],null,{focus:true});
  assert.ok(plot.domain.max-plot.domain.min<1);
  assert.ok(plot.points[0].y-plot.points[2].y>100);
});

test('very small sensor changes have distinct readable axis labels', () => {
  const {api}=fixture(()=>({}));
  const rows=[reading(1,0,.005),reading(2,5,.00501),reading(3,10,.00502)];
  const plot=api.chart(rows,{...sensor,limite_alerta:.01},null,'auto',null,true,[],null,{focus:true});
  assert.equal(new Set(Array.from(plot.ticks,t=>t.label)).size,5);
  assert.ok(plot.points.every(p=>Number.isFinite(p.y)));
  assert.ok(plot.points[0].y-plot.points[2].y>100);
});

test('selected trend sensor uses the live polling component and refreshes its local fit every five seconds', async () => {
  let batch=[reading(1,0,40),reading(2,10,41),reading(3,20,42)];
  const f=fixture(()=>({results:[...batch].reverse()}),null,{selectedSensor:sensor});
  await f.mount();
  assert.equal(f.app.showTrend.value,true);
  assert.ok(f.app.displayed.value.projection);
  assert.ok(f.urls.every(url=>url.includes('/leituras/')));
  const poll=[...f.timers.values()].find(timer=>timer.ms===5000);
  assert.ok(poll);
  batch.push(reading(4,30,43)); await poll.fn();
  assert.equal(f.app.latest.value.id,4);
  assert.equal(f.app.projected.value.points[0].timestamp,stamp(30));
  assert.equal(f.app.received.value,1);
  f.app.scale.value='limits'; await f.flush();
  assert.ok(f.app.displayed.value.limits.every(t=>t.visible));
  assert.ok(f.app.displayed.value.domain.max>100);
  f.unmount(); assert.equal(f.timers.size,0);
});

test('a full live window advances timestamps and reports arrivals even when all values are equal', async () => {
  let batch=Array.from({length:60},(_,i)=>reading(i+1,i*5,70));
  const f=fixture(()=>({results:[...batch].reverse().slice(0,60)})); await f.mount();
  f.app.showTrend.value=true; await f.flush();
  const previous=f.app.displayed.value;
  batch.push(reading(61,300,70)); await f.app.refresh();
  assert.equal(f.app.rows.value.length,60);
  assert.equal(f.app.rows.value[0].id,2);
  assert.equal(f.app.latest.value.id,61);
  assert.equal(f.app.received.value,1);
  assert.ok(f.app.displayed.value.domain.from>previous.domain.from);
  assert.ok(f.app.displayed.value.domain.to>previous.domain.to);
  assert.equal(f.app.projected.value.kind,'stable');
  assert.equal(f.app.projected.value.points[0].timestamp,stamp(300));
  const unchanged=f.app.displayed.value;
  await f.app.refresh(); assert.equal(f.app.displayed.value,unchanged);
  assert.equal(f.app.received.value,0);
  f.unmount();
});

test('switching the selected live sensor discards a pending response and restarts the sample', async () => {
  let pending=false,release;
  const f=fixture(url=>{
    if(url.includes('sensor=2')) return {results:[{...reading(10,30,20),sensor:2}]};
    return pending?new Promise(resolve=>{release=resolve;}):{results:[reading(1,0,50)]};
  },null,{selectedSensor:sensor});
  await f.mount(); pending=true; const old=f.app.refresh();
  f.props.selectedSensor={...sensor,id:2}; await f.flush();
  release({results:[reading(99,100,999)]}); await old;
  assert.equal(f.app.rows.value[0].id,10);
  assert.equal(f.app.received.value,0);
  assert.ok(f.app.displayed.value.domain.max<30);
  f.unmount();
});

test('line labels show only the last measurement and the estimated endpoint with its horizon', () => {
  const {api}=fixture(()=>({}));
  const rows=[reading(1,0,40),reading(2,60,50),reading(3,120,60)];
  const projection=api.projectForward(rows,api.fitLine(rows),{visual:true});
  for (const compact of [false,true]) {
    const plot=api.chart(rows,sensor,null,'auto',null,compact,[],projection,{focus:true,futureSpace:true});
    assert.equal(plot.annotations.length,2);
    assert.equal(plot.annotations[0].text,'60');
    assert.equal(plot.annotations[0].caption,'Última leitura');
    assert.equal(plot.annotations[1].text,'≈ 70');
    assert.equal(plot.annotations[1].caption,'+1 min');
    assert.equal(plot.points.length,3);
    assert.equal(projection.points.length,2);
    for (const label of plot.annotations) {
      assert.ok(label.x-label.width>=plot.left);
      assert.ok(label.x<=plot.right);
      assert.ok(label.y>=56 && label.y<=206);
    }
  }
});

test('flat mobile line labels stay apart and small or negative values retain their scale precision', () => {
  const {api}=fixture(()=>({}));
  for (const [values,expected] of [[[70,70,70],'70'],[[123456.789,123456.789,123456.789],'123.456,79'],[[.00001,.00002,.00003],'0,00003'],[[-3,-2,-1],'-1']]) {
    const rows=values.map((value,i)=>reading(i+1,i*30,value));
    const projection=api.projectForward(rows,api.fitLine(rows),{visual:true});
    const plot=api.chart(rows,sensor,null,'auto',null,true,[],projection,{focus:true,futureSpace:true});
    const [latest,estimate]=plot.annotations;
    const overlap=Math.abs(latest.y-estimate.y)<34 && latest.x>estimate.x-estimate.width-10 && estimate.x>latest.x-latest.width-10;
    assert.equal(overlap,false);
    assert.equal(latest.text,expected);
    assert.match(estimate.text,/^≈ /);
    assert.ok(plot.annotations.every(label=>Number.isFinite(label.x) && Number.isFinite(label.y)));
  }
});

test('without a projection there is one measured value, and empty charts have no labels', () => {
  const {api}=fixture(()=>({}));
  assert.equal(api.chart([],sensor).annotations.length,0);
  const plot=api.chart([reading(1,0,0)],sensor);
  assert.equal(plot.annotations.length,1);
  assert.equal(plot.annotations[0].text,'0');
  assert.equal(plot.annotations[0].id,'latest');
});
