/* Shared live view. Polling cadence never creates measurements or advances the time axis. */
(function (root) {
  const number = value => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: Math.abs(Number(value)) < 1 ? 6 : 3 }).format(value);
  const date = value => new Date(value).toLocaleString('pt-BR');
  const forecastDate = value => new Date(value).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  const list = data => Array.isArray(data) ? data : data?.results || [];
  const localPath = url => url.replace(/^https?:\/\/[^/]+/, '');
  function normalize(rows) {
    const byId = new Map();
    for (const row of rows) {
      if (row.valor === null || row.valor === '' || !Number.isFinite(Number(row.valor)) || !Number.isFinite(Date.parse(row.timestamp))) continue;
      byId.set(String(row.id), { ...row, valor: Number(row.valor) });
    }
    return [...byId.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp) || Number(a.id) - Number(b.id));
  }
  function thresholds(sensor) {
    const limit = Number(sensor?.limite_alerta);
    if (!Number.isFinite(limit) || limit <= 0) return [];
    const percentages = ['baixo', 'medio', 'critico'].map((name, i) => Number(sensor['limite_alerta_' + name + '_pct'] ?? [70, 85, 100][i]));
    if (!percentages.every(Number.isFinite) || !(0 <= percentages[0] && percentages[0] < percentages[1] && percentages[1] < percentages[2] && percentages[2] <= 100)) return [];
    return percentages.map((pct, i) => ({ name: ['Baixo', 'Médio', 'Crítico'][i], value: limit * pct / 100,
      color: ['var(--warn)', 'var(--live-medium)', 'var(--danger)'][i], dash: ['3 5', '9 5', '12 4 2 4'][i] }));
  }
  function fitLine(rows) {
    // A visual fit uses exactly the displayed time sample, with one value per timestamp.
    const times = new Map();
    for (const row of normalize(rows)) times.set(Date.parse(row.timestamp), row);
    const sample = [...times.values()];
    if (sample.length < 3) return [];
    const origin = Date.parse(sample[0].timestamp);
    const xs = sample.map(r => (Date.parse(r.timestamp)-origin)/3600000);
    const meanX = xs.reduce((sum,x) => sum+x,0)/xs.length;
    const meanY = sample.reduce((sum,r) => sum+r.valor,0)/sample.length;
    const spread = xs.reduce((sum,x) => sum+(x-meanX)**2,0);
    if (!(spread > 0)) return [];
    const slope = xs.reduce((sum,x,i) => sum+(x-meanX)*(sample[i].valor-meanY),0)/spread;
    return [0,sample.length-1].map(i => ({ timestamp:sample[i].timestamp, valor:meanY+slope*(xs[i]-meanX) }));
  }
  function projectionSummary(analysis) {
    if (!analysis?.analysis_enabled || analysis.insufficient_data || analysis.data_quality !== 'valid' || analysis.direction !== 'increasing') return null;
    const limit = Number(analysis.limite_operacional ?? analysis.sensor_info?.limite_alerta);
    if (!Number.isFinite(limit) || limit <= 0) return null;
    const at = analysis.projected_breach_at;
    const reference = analysis.readings_summary?.[analysis.readings_summary.length-1]?.timestamp;
    const end = Date.parse(at), last = Date.parse(reference), queried = Date.parse(analysis.analyzed_at);
    if (!Number.isFinite(end) || !Number.isFinite(last) || !Number.isFinite(queried) || end <= queried || end <= last) return null;
    const minutes = (end-last)/60000;
    const rounded = Math.max(1, Math.round(minutes));
    const hours = Math.floor(rounded/60), rest = rounded%60;
    const duration = rounded < 60 ? rounded + ' min' : hours + ' h' + (rest ? ' ' + rest + ' min' : '');
    return { at, reference, duration };
  }
  function horizonLabel(milliseconds) {
    const seconds = Math.max(1, Math.round(milliseconds / 1000));
    if (seconds < 60) return seconds + ' s';
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return minutes + ' min';
    return Math.floor(minutes / 60) + ' h' + (minutes % 60 ? ' ' + minutes % 60 + ' min' : '');
  }
  function projectForward(rows, fitted, { analysis = null, limit = null, visual = false, horizonMinutes = null } = {}) {
    const unique = new Map();
    for (const row of normalize(rows)) unique.set(Date.parse(row.timestamp), row);
    const sample = [...unique.values()];
    if (sample.length < 3 || fitted.length !== 2) return null;
    const first = sample[0], last = sample[sample.length - 1];
    const from = Date.parse(last.timestamp), span = from - Date.parse(first.timestamp);
    const fitSpan = Date.parse(fitted[1].timestamp) - Date.parse(fitted[0].timestamp);
    const slope = (Number(fitted[1].valor) - Number(fitted[0].valor)) / fitSpan;
    if (!(span > 0) || !(fitSpan > 0) || !Number.isFinite(slope) || !Number.isFinite(Number(fitted[0].valor)) || Date.parse(fitted[0].timestamp) !== Date.parse(first.timestamp) || Date.parse(fitted[1].timestamp) !== from) return null;
    if (analysis && !analysis.analysis_enabled) return null;
    const mean = sample.reduce((sum, row) => sum + row.valor, 0) / sample.length;
    const total = sample.reduce((sum, row) => sum + (row.valor - mean) ** 2, 0);
    const residual = sample.reduce((sum, row) => sum + (row.valor - (Number(fitted[0].valor) + slope * (Date.parse(row.timestamp) - Date.parse(fitted[0].timestamp)))) ** 2, 0);
    const r2 = total > 0 ? Math.max(0, 1 - residual / total) : 1;
    const persistence = sample.slice(1).filter((row, i) => (row.valor - sample[i].valor) * slope > 0).length / (sample.length - 1);
    const confirmed = Boolean(analysis && !analysis.insufficient_data && analysis.data_quality === 'valid' &&
      ['increasing', 'decreasing'].includes(analysis.direction) && (analysis.direction === 'increasing') === (slope > 0) && slope !== 0);
    const minR2 = analysis?.config_used?.r2_minimo ?? .8, minPersistence = analysis?.config_used?.persistencia_minima ?? .7;
    const sourceConsistent = ['source_r_squared', 'source_persistence_ratio'].every((key,i) =>
      analysis?.[key] == null || Number(analysis[key]) >= [minR2, minPersistence][i]);
    const consistent = total === 0 || (r2 >= minR2 && persistence >= minPersistence && sourceConsistent);
    if (!visual && (slope === 0 || (analysis ? !confirmed : !consistent))) return null;
    // The visual preview has its own status. Operational confirmation, alert
    // creation and the official time-to-limit estimate remain server decisions.
    const kind = confirmed ? 'confirmed' : total === 0 ? 'stable' : !consistent ? 'low_confidence' : analysis ? 'preliminary' : 'visual';
    // Keep at least two thirds of the time axis for observations. Long-range
    // limit estimates stay in the optional detail instead of flattening history.
    // Só a análise operacional recebe horizonte explícito. A prévia curta
    // mantém espaço para o histórico enquanto os critérios estão pendentes.
    const requestedHorizon = Number(horizonMinutes) * 60000;
    const horizon = confirmed && requestedHorizon > 0 && Number.isFinite(requestedHorizon)
      ? requestedHorizon : Math.min(span / 2, 24 * 3600000);
    const to = from + horizon;
    if (!Number.isFinite(to) || !Number.isFinite(new Date(to).getTime())) return null;
    const upper = Number(limit);
    const canEstimateLimit = !visual || (analysis ? confirmed : consistent);
    const untilLimit = canEstimateLimit && Number.isFinite(upper) && upper > 0 && upper > last.valor && slope > 0 ? (upper - last.valor) / slope : null;
    const reachesLimit = untilLimit !== null && untilLimit > 0 && untilLimit <= horizon;
    // Crossing the limit is an annotation along the line, not its endpoint.
    // Stopping there made a near-limit forecast collapse into a single dot.
    const endValue = last.valor + slope * horizon;
    if (!Number.isFinite(endValue)) return null;
    return { from, to, horizon, horizonLabel: horizonLabel(horizon), reachesLimit, kind, r2, persistence,
      limitOutside: untilLimit !== null && untilLimit > horizon,
      breach: reachesLimit ? {timestamp:new Date(from + untilLimit).toISOString(), valor:upper} : null,
      points: [{ timestamp: last.timestamp, valor: last.valor }, { timestamp: new Date(to).toISOString(), valor: endValue }] };
  }
  function projectionLabel(projection) {
    return {confirmed:'Projeção da tendência', stable:'Projeção estável', low_confidence:'Projeção exploratória', preliminary:'Projeção preliminar', visual:'Projeção visual'}[projection?.kind] || 'Projeção futura';
  }
  function projectionExplanation(projection, analysis = null) {
    if (!projection) return analysis?.analysis_enabled === false ? 'Análise de tendência desativada para este sensor.' : 'Aguardando pelo menos 3 horários de medição diferentes para projetar.';
    const message = projection.kind === 'stable' ? 'A projeção é horizontal porque as leituras estão constantes.' :
      projection.kind === 'low_confidence' ? 'As leituras oscilam: a linha exploratória indica a direção estimada, com baixa consistência.' :
      projection.kind === 'preliminary' ? 'A projeção preliminar mostra o ritmo da amostra, ainda sem confirmação para alertas de tendência.' :
      'Azul: leituras reais. Roxo à direita: projeção, se o ritmo continuar. A divisória marca a última medição.';
    if (analysis?.insufficient_data) {
      const minimum = analysis.config_used?.minimo_leituras, duration = analysis.config_used?.duracao_minima_minutos;
      return message + (minimum != null && duration != null ? ` A confirmação operacional exige ${minimum} leituras cobrindo ${duration} min.` : ' Aguardando a quantidade e o tempo mínimos para confirmação operacional.');
    }
    return message;
  }
  function lineAnnotations(points, projectedPoints, projection, left, right, format, bottom = 230) {
    if (!points.length) return [];
    const last = points[points.length - 1];
    const end = projectedPoints[projectedPoints.length - 1];
    const make = (point, id, text, caption, below = false) => {
      const width = Math.max(text.length * 8, caption.length * 6.5);
      const x = Math.min(right - 8, Math.max(left + width + 4, point.x - 8));
      const y = Math.max(56, Math.min(bottom - 24, point.y + (below ? 22 : -24)));
      return { id, x, y, text, caption, width };
    };
    const latest = make(last, 'latest', format(last.valor), 'Última leitura');
    const labels = [latest];
    if (projection && end) {
      const estimate = make(end, 'estimate', '≈ ' + format(end.valor), '+' + projection.horizonLabel);
      // Keep the two labels apart on flat lines and narrow/mobile charts.
      const overlaps = () => Math.abs(latest.y - estimate.y) < 34 &&
        latest.x > estimate.x - estimate.width - 10 && estimate.x > latest.x - latest.width - 10;
      if (overlaps()) Object.assign(estimate, make(end, 'estimate', estimate.text, estimate.caption, true));
      if (overlaps()) estimate.y = latest.y <= bottom - 60 ? latest.y + 36 : latest.y - 36;
      labels.push(estimate);
    }
    return labels;
  }
  function chart(rows, sensor, envelope = null, minutes = 'auto', domain = null, compact = false, trendLine = [], projection = null, view = {}) {
    const width = view.width || (compact ? 360 : 900), height = view.height || 285;
    const bottom = height - 55;
    if (!rows.length) return { width, height, bottom, left:compact ? 48 : 72, right:compact ? 344 : 722, points: [], annotations: [], ticks: [], times: [], limits: [], offscaleLimits:[], path: '', trendPath: '', projection: null, domain: null };
    const limits = view.limits || thresholds(sensor), values = rows.map(r => r.valor).concat(view.focus ? [] : limits.map(t => t.value), view.showFit === false ? [] : trendLine.map(p => p.valor), (projection?.points || []).map(p => p.valor));
    const rawMin = Math.min(...values), rawMax = Math.max(...values);
    const minimumRange = view.focus ? Math.max(Math.abs(rawMax) * .002, .000001) : 0;
    const range = Math.max(rawMax - rawMin, minimumRange);
    const padding = (range || Math.max(Math.abs(rawMax) * 0.1, 1)) * (view.focus ? .25 : .15);
    // Expand immediately; recover gradually after an old peak leaves the window.
    const extra = Math.max(0, minimumRange - (rawMax - rawMin)) / 2;
    const targetMin = rawMin - extra - padding, targetMax = rawMax + extra + padding;
    if (view.focus && envelope && envelope.max - envelope.min > (targetMax-targetMin)*4) envelope = null;
    let min = Math.min(targetMin, envelope ? envelope.min * .8 + targetMin * .2 : targetMin);
    let max = Math.max(targetMax, envelope ? envelope.max * .8 + targetMax * .2 : targetMax);
    const to = Date.parse(rows[rows.length - 1].timestamp);
    const first = Date.parse(rows[0].timestamp);
    const requestedFrom = minutes === 'auto' ? first : to - Number(minutes) * 60000;
    // A selected window is a filter, not a reason to draw hours of empty space
    // before a short sample and compress the forecast to a few pixels.
    const from = view.futureSpace || view.focus ? Math.max(requestedFrom, first) : requestedFrom;
    const futureTo = projection?.to || (view.futureSpace ? to + Math.min(Math.max(to-from, 2000)/2, 86400000) : to);
    const bounds = domain || { min, max, from: from === to ? to - 1000 : from, to: futureTo };
    ({ min, max } = bounds);
    const y = value => bottom - (value - min) / (max - min) * (bottom - 42);
    const axisNumber = new Intl.NumberFormat('pt-BR', {maximumFractionDigits:Math.max(2,Math.min(8,1-Math.floor(Math.log10((max-min)/4))))});
    const labelWidth = Math.max(...Array.from({length:5}, (_, i) => axisNumber.format(min + (max-min)*i/4).length)) * 7 + 16;
    const left = view.width ? Math.max(compact ? 48 : 72, labelWidth) : compact ? 48 : 72;
    const right = compact ? width - 16 : view.focus ? width - 28 : width - 178;
    const x = time => left + (time - bounds.from) / Math.max(bounds.to - bounds.from, 1) * (right-left);
    const points = rows.map(r => ({ ...r, x: x(Date.parse(r.timestamp)), y: y(r.valor) }));
    const crossesDate = new Date(bounds.from).toLocaleDateString() !== new Date(bounds.to).toLocaleDateString();
    const timeFormat = new Intl.DateTimeFormat('pt-BR', { ...(crossesDate ? { day: '2-digit', month: '2-digit' } : {}), hour: '2-digit', minute: '2-digit', ...(bounds.to - bounds.from < 3600000 ? { second: '2-digit' } : {}) });
    const projectedPoints = (projection?.points || []).map(p => ({ ...p, x: x(Date.parse(p.timestamp)), y: y(p.valor) }));
    const plottedLimits = limits.map(t => ({...t,y:y(t.value),visible:t.value>=min && t.value<=max,position:t.value>max?'acima':'abaixo'}));
    return { points, annotations: lineAnnotations(points, projectedPoints, projection, left, right, value => axisNumber.format(value), bottom), width, height, bottom, left, right, domain: bounds, path: points.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' '),
      ticks: Array.from({ length: 5 }, (_, i) => { const v = min + (max - min) * i / 4; return { value: v, label: axisNumber.format(v), y: y(v) }; }),
      times: Array.from({ length: 3 }, (_, i) => ({ x: left + i * (right-left)/2, label: timeFormat.format(bounds.from + (bounds.to - bounds.from) * i / 2) })),
      trendPath: view.showFit === false ? '' : trendLine.map((p,i) => `${i ? 'L' : 'M'}${x(Date.parse(p.timestamp)).toFixed(2)},${y(p.valor).toFixed(2)}`).join(' '),
      future: futureTo > to ? { startX: Math.min(right, Math.max(left, x(to))), width: Math.max(0, right - Math.max(left, x(to))), timestamp: rows[rows.length-1].timestamp } : null,
      projection: projection ? { ...projection, startX: Math.min(right, Math.max(left, x(projection.from))), width: Math.max(0, right - Math.max(left, x(projection.from))),
        points: projectedPoints, path: projectedPoints.map((p,i) => `${i ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' '), end: projectedPoints[projectedPoints.length - 1],
        breach:projection.breach ? {...projection.breach,x:x(Date.parse(projection.breach.timestamp)),y:y(projection.breach.valor)} : null } : null,
      limits: plottedLimits, offscaleLimits:plottedLimits.filter(t=>!t.visible) };
  }
  async function readings(api, sensorId, minutes) {
    const base = new URLSearchParams({ sensor: String(sensorId), escopo_operacional: 'true', limit: minutes === 'auto' ? '60' : '1' });
    const head = await api('/api/telemetria/leituras/?' + base, {cache:'no-store'});
    if (!head) throw new Error('Consulta interrompida.');
    const latest = list(head)[0];
    if (!latest) return { rows: [], truncated: false };
    let data = head, rows = minutes === 'auto' ? list(head) : [];
    const maximum = minutes === 'auto' ? 60 : 1000;
    if (minutes !== 'auto') {
      base.set('timestamp_de', new Date(Date.parse(latest.timestamp) - Number(minutes) * 60000).toISOString());
      base.set('timestamp_ate', latest.timestamp);
      base.set('id_ate', String(latest.id));
      base.set('limit', '200');
      data = await api('/api/telemetria/leituras/?' + base, {cache:'no-store'});
      if (!data) throw new Error('Consulta interrompida.');
      rows = list(data);
    }
    const seen = new Set();
    while (data.next && rows.length < maximum + (minutes === 'auto' ? 0 : 1)) {
      if (seen.has(data.next)) break;
      seen.add(data.next);
      let next = localPath(data.next);
      if (minutes === 'auto') {
        const query = new URLSearchParams(next.split('?')[1]);
        query.set('timestamp_ate', latest.timestamp); query.set('id_ate', String(latest.id));
        next = next.split('?')[0] + '?' + query;
      }
      data = await api(next, {cache:'no-store'});
      if (!data) throw new Error('Consulta interrompida.');
      rows.push(...list(data));
    }
    const unique = normalize(rows);
    const cutoff = Date.parse(latest.timestamp) - 5*60000;
    return { rows: (minutes === 'auto' ? unique.filter(r=>Date.parse(r.timestamp)>=cutoff) : unique).slice(-maximum), truncated: minutes !== 'auto' && (unique.length > maximum || Number(data.count || head.count) > maximum || Boolean(data.next)) };
  }
  function useCompact() {
    const media = root.matchMedia?.('(max-width: 700px)');
    const compact = Vue.ref(media?.matches || false);
    const changed = () => { compact.value = media.matches; };
    Vue.onMounted(() => media?.addEventListener?.('change', changed));
    Vue.onUnmounted(() => media?.removeEventListener?.('change', changed));
    return compact;
  }
  function useChartDimensions(props, compact) {
    const host = Vue.ref(null), width = Vue.ref(0), viewportHeight = Vue.ref(root.innerHeight || 900);
    let observer;
    const measure = () => {
      width.value = Math.max(250, host.value?.clientWidth || (compact.value ? 360 : 900));
      viewportHeight.value = root.innerHeight || 900;
    };
    Vue.onMounted(() => {
      if (!props.large) return;
      measure();
      if (root.ResizeObserver && host.value) { observer = new root.ResizeObserver(measure); observer.observe(host.value); }
      root.addEventListener?.('resize', measure);
    });
    Vue.onUnmounted(() => { observer?.disconnect(); root.removeEventListener?.('resize', measure); });
    const geometry = Vue.computed(() => props.large ? {
      width: width.value || (compact.value ? 360 : 900),
      height: props.expanded ? Math.max(240, viewportHeight.value - (compact.value ? 450 : 380))
        : compact.value ? 260 : Math.round(Math.min(480, Math.max(320, viewportHeight.value * .44))),
    } : {});
    return {host, geometry};
  }
  const component = {
    props: { api: { type: Function, required: true }, empresa: { default: '' }, equipamentos: { default: null }, selectedSensor:{default:null}, showReading:{type:Boolean,default:true}, clean:{type:Boolean,default:false}, large:{type:Boolean,default:false}, expanded:{type:Boolean,default:false} },
    emits: ['reading-update'],
    setup(props, context) {
      const emit = context?.emit || (() => {});
      const { ref, computed, watch, onMounted, onUnmounted } = Vue;
      const compact = useCompact();
      const dimensions = useChartDimensions(props, compact);
      const showTrend = ref(Boolean(props.selectedSensor));
      const showHistoryFit = ref(false);
      const scale = ref('focus'), received = ref(0);
      const equipment = ref(''), sensorId = ref(''), minutes = ref('auto'), options = ref([]), sensors = ref([]);
      const rows = ref([]), displayed = ref(chart([], null)), busy = ref(false), optionsBusy = ref(false), paused = ref(false);
      const error = ref(''), optionsError = ref(''), updatedAt = ref(null), now = ref(Date.now()), truncated = ref(false), selected = ref(null);
      let generation = 0, optionGeneration = 0, equipmentGeneration = 0, timer = null, clock = null, frame = null, envelope = null, signature = '', disposed = false;
      const sensor = computed(() => sensors.value.find(s => Number(s.id) === Number(sensorId.value)));
      const fitted = computed(() => showTrend.value ? fitLine(rows.value) : []);
      const projected = computed(() => showTrend.value ? projectForward(rows.value, fitted.value, {limit:sensor.value?.limite_alerta,visual:true}) : null);
      const fitMessage = computed(() => projectionExplanation(projected.value));
      const view = () => ({focus:scale.value==='focus', futureSpace:showTrend.value, showFit:showHistoryFit.value || !projected.value, ...dimensions.geometry.value});
      const latest = computed(() => rows.value[rows.value.length - 1]);
      const age = computed(() => {
        if (!latest.value) return '';
        const seconds = Math.max(0, Math.floor((now.value - Date.parse(latest.value.timestamp)) / 1000));
        return seconds < 60 ? `${seconds} s` : seconds < 3600 ? `${Math.floor(seconds / 60)} min` : `${Math.floor(seconds / 3600)} h ${Math.floor(seconds % 3600 / 60)} min`;
      });
      const detail = computed(() => selected.value || latest.value);
      function cancelAnimation() { if (frame !== null) cancelAnimationFrame(frame); frame = null; }
      function stop() {
        if (timer !== null) clearInterval(timer);
        if (clock !== null) clearInterval(clock);
        timer = clock = null; cancelAnimation(); ++generation; busy.value = false;
      }
      function reset() {
        stop(); envelope = null; signature = ''; rows.value = []; displayed.value = chart([], null);
        updatedAt.value = null; selected.value = null; truncated.value = false; error.value = ''; received.value=0;
      }
      function render(next, animate) {
        cancelAnimation();
        const previous = displayed.value;
        if (!animate || !previous.domain || !next.domain || root.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { displayed.value = next; return; }
        const started = performance.now();
        function step(time) {
          const t = Math.min((time - started) / 300, 1), d = {};
          for (const key of ['min', 'max', 'from', 'to']) d[key] = previous.domain[key] + (next.domain[key] - previous.domain[key]) * t;
          displayed.value = t === 1 ? next : chart(rows.value, sensor.value, envelope, minutes.value, d, compact.value, fitted.value, projected.value, view());
          frame = t < 1 ? requestAnimationFrame(step) : null;
        }
        frame = requestAnimationFrame(step);
      }
      async function refresh() {
        if (busy.value || paused.value || document.hidden || !sensorId.value || !sensor.value?.ativo || disposed) return;
        const request = generation;
        busy.value = true;
        try {
          const result = await readings(props.api, sensorId.value, minutes.value);
          if (request !== generation || disposed) return;
          emit('reading-update', {sensorId:Number(sensorId.value), company:props.empresa,
            reading:result.rows[result.rows.length - 1] || null});
          const nextSignature = JSON.stringify([result.rows, thresholds(sensor.value)]);
          updatedAt.value = new Date().toISOString(); now.value = Date.now(); error.value = ''; truncated.value = result.truncated;
          if (nextSignature !== signature) {
            const previousIds = new Set(rows.value.map(r=>String(r.id)));
            received.value = signature ? result.rows.filter(r=>!previousIds.has(String(r.id))).length : 0;
            signature = nextSignature; rows.value = result.rows; selected.value = null;
            const next = chart(rows.value, sensor.value, envelope, minutes.value, null, compact.value, fitted.value, projected.value, view());
            envelope = next.domain ? { min: next.domain.min, max: next.domain.max } : null;
            render(next, true);
          } else received.value = 0;
        } catch (_) {
          if (request === generation && !disposed) error.value = 'Não foi possível consultar novas leituras. O último gráfico foi preservado.';
        } finally { if (request === generation) busy.value = false; }
      }
      function start() {
        stop();
        if (paused.value || document.hidden || !sensor.value?.ativo || disposed) return;
        refresh(); timer = setInterval(refresh, 5000); clock = setInterval(() => { now.value = Date.now(); }, 1000);
      }
      async function loadOptions() {
        if (props.selectedSensor) { loadFixedSensor(); return; }
        const request = ++equipmentGeneration;
        optionsBusy.value = true; optionsError.value = '';
        try {
          const response = props.equipamentos !== null ? { opcoes_equipamentos: props.equipamentos } : await props.api('/api/dashboards/resumo/?incluir_desempenho=false' + (props.empresa ? '&empresa_id=' + props.empresa : ''));
          if (request !== equipmentGeneration || disposed) return;
          if (!response) throw new Error();
          options.value = response.opcoes_equipamentos || [];
          if (!options.value.some(e => Number(e.id) === Number(equipment.value))) equipment.value = options.value.length === 1 ? options.value[0].id : '';
        } catch (_) { if (request === equipmentGeneration && !disposed) optionsError.value = 'Não foi possível carregar os equipamentos.'; }
        finally { if (request === equipmentGeneration) optionsBusy.value = false; }
      }
      function loadFixedSensor() {
        if (!props.selectedSensor || disposed) return;
        ++optionGeneration; ++equipmentGeneration;
        optionsBusy.value=false; optionsError.value='';
        const fixed = {...props.selectedSensor,ativo:props.selectedSensor.ativo ?? true};
        sensors.value=[fixed]; equipment.value=fixed.equipamento_id;
        if (Number(sensorId.value) === Number(fixed.id)) refresh();
        else sensorId.value=fixed.id;
      }
      async function loadSensors() {
        reset(); const request = ++optionGeneration;
        sensorId.value = ''; sensors.value = []; optionsError.value = '';
        if (!equipment.value) { optionsBusy.value = false; return; }
        optionsBusy.value = true;
        try {
          let url = '/api/telemetria/sensores/?equipamento=' + equipment.value + '&escopo_operacional=true&limit=200';
          const result = [];
          while (url) {
            const data = await props.api(url);
            if (request !== optionGeneration || disposed) return;
            if (!data) throw new Error();
            result.push(...list(data)); url = data.next ? localPath(data.next) : '';
          }
          sensors.value = result;
          if (result.length === 1) sensorId.value = result[0].id;
        } catch (_) { if (request === optionGeneration && !disposed) optionsError.value = 'Não foi possível carregar os sensores.'; }
        finally { if (request === optionGeneration) optionsBusy.value = false; }
      }
      function togglePause() { paused.value = !paused.value; if (paused.value) stop(); else start(); }
      function fit() { envelope = null; render(chart(rows.value, sensor.value, null, minutes.value, null, compact.value, fitted.value, projected.value, view()), false); }
      function visibility() { if (document.hidden) stop(); else start(); }
      watch([compact, showTrend, showHistoryFit, scale, () => JSON.stringify(dimensions.geometry.value)], () => {
        envelope = null;
        const next = chart(rows.value, sensor.value, envelope, minutes.value, null, compact.value, fitted.value, projected.value, view());
        envelope = next.domain ? { min:next.domain.min, max:next.domain.max } : null;
        render(next, false);
      });
      watch(equipment, () => { if (!props.selectedSensor) loadSensors(); });
      watch([sensorId, minutes], () => { reset(); start(); });
      watch(() => props.empresa, () => { reset(); ++optionGeneration; equipment.value = ''; sensorId.value = ''; sensors.value = []; loadOptions(); });
      watch(() => props.equipamentos, loadOptions);
      watch(() => props.selectedSensor, loadOptions);
      onMounted(() => { loadOptions(); document.addEventListener('visibilitychange', visibility); });
      onUnmounted(() => { disposed = true; ++optionGeneration; ++equipmentGeneration; stop(); document.removeEventListener('visibilitychange', visibility); });
      return { plotHost: dimensions.host, compact, showTrend, showHistoryFit, scale, received, fitted, projected, fitMessage, equipment, sensorId, minutes, options, sensors, sensor, rows, displayed, busy, optionsBusy, paused, error, optionsError, updatedAt, truncated, latest, detail, age, selected,
        refresh, loadOptions, loadSensors, togglePause, fit, number, date, projectionLabel };
    },
    template: `
      <section ref="plotHost" class="live-chart" :class="{'chart-clean':clean,'chart-large':large,'reading-in-header':!showReading}" aria-label="Acompanhamento de medições">
        <div class="live-controls">
          <label v-if="!selectedSensor">Equipamento<select v-model="equipment" :disabled="optionsBusy"><option value="">Escolha o equipamento</option><option v-for="e in options" :key="e.id" :value="e.id">{{ e.nome }}</option></select></label>
          <label v-if="!selectedSensor">Sensor<select v-model="sensorId" :disabled="!equipment || optionsBusy"><option value="">Escolha o sensor</option><option v-for="s in sensors" :key="s.id" :value="s.id">{{ s.nome }} · {{ s.unidade_medida }}{{ s.ativo ? '' : ' · inativo' }}</option></select></label>
          <label>{{ clean ? 'Período do gráfico' : 'Janela' }}<select v-model="minutes"><option value="auto">{{ clean ? 'Últimos 5 minutos' : 'Ao vivo — últimos 5 min (até 60 leituras)' }}</option><option value="5">5 minutos</option><option value="15">15 minutos</option><option value="60">1 hora</option><option value="120">2 horas</option><option value="360">6 horas</option><option value="1440">24 horas</option></select></label>
          <label v-if="!clean">Escala<select v-model="scale"><option value="focus">Acompanhar variação</option><option value="limits">Incluir todos os limites</option></select></label>
          <div v-if="!clean" class="live-buttons"><button class="btn btn-ghost btn-sm" :disabled="!sensorId" @click="togglePause">{{ paused ? 'Retomar ao vivo' : 'Pausar' }}</button><button class="btn btn-ghost btn-sm" :disabled="!rows.length" @click="fit">Ajustar escala</button></div>
          <details v-if="clean" class="chart-options"><summary>Opções do gráfico</summary><div><label>Escala<select v-model="scale"><option value="focus">Acompanhar variação</option><option value="limits">Incluir todos os limites</option></select></label><label><input type="checkbox" v-model="showTrend"> Tendência e projeção</label><label v-if="showTrend"><input type="checkbox" v-model="showHistoryFit"> Ajuste no histórico</label><button class="btn btn-ghost btn-sm" :disabled="!sensorId" @click="togglePause">{{ paused ? 'Retomar' : 'Pausar' }}</button><button class="btn btn-ghost btn-sm" :disabled="!rows.length" @click="fit">Ajustar escala</button></div></details>
        </div>
        <p v-if="optionsError" class="telemetry-notice" role="alert">{{ optionsError }} <button class="btn btn-ghost btn-sm" @click="equipment ? loadSensors() : loadOptions()">Tentar novamente</button></p>
        <p v-if="error" class="telemetry-notice" role="alert">{{ error }} <button class="btn btn-ghost btn-sm" :disabled="busy || paused" @click="refresh">Tentar novamente</button></p>
        <div v-if="!sensorId" class="live-placeholder">{{ optionsBusy ? 'Carregando opções…' : equipment && !sensors.length ? 'Nenhum sensor disponível neste equipamento.' : 'Escolha um equipamento e um sensor para acompanhar as medições.' }}</div>
        <template v-else>
          <div class="live-status"><span :class="['live-state', {paused:paused || !sensor?.ativo, failed:!!error}]">{{ !sensor?.ativo ? 'Sensor inativo · consulta interrompida' : paused ? 'Acompanhamento pausado' : busy ? 'Consultando…' : received ? received + ' nova(s) leitura(s) recebida(s) · consulta a cada 5 s' : 'Aguardando novas medições · consulta a cada 5 s' }}</span><span>Última consulta: {{ updatedAt ? date(updatedAt) : 'aguardando' }}</span></div>
          <div v-if="showReading && rows.length" class="live-measure"><div><span>Última medição</span><strong>{{ number(latest.valor) }} <small>{{ sensor?.unidade_medida }}</small></strong></div><p>{{ date(latest.timestamp) }}<br>há {{ age }}</p></div>
          <div v-if="rows.length" class="trend-chart-toolbar"><label class="trend-chart-toggle"><input type="checkbox" v-model="showTrend"> Mostrar tendência e projeção</label><label v-if="showTrend && projected" class="trend-chart-toggle"><input type="checkbox" v-model="showHistoryFit"> Comparar ajuste no histórico</label><div class="trend-chart-legend" aria-label="Legenda do gráfico"><span><i class="legend-reading"></i>Leituras reais</span><span v-if="displayed.trendPath"><i class="legend-trend"></i>Tendência da janela</span><span v-if="displayed.projection"><i class="legend-projection"></i>{{ projectionLabel(displayed.projection) }}</span><span v-if="displayed.limits.some(t=>t.visible)"><i class="legend-limit"></i>Limites na escala</span></div></div>
          <p v-if="showTrend && rows.length" class="trend-chart-explanation">{{ fitMessage }}</p>
          <div v-if="rows.length" class="live-plot">
            <svg :viewBox="'0 0 ' + displayed.width + ' ' + displayed.height" :style="large ? {height:displayed.height + 'px'} : null" role="img" :aria-label="'Medições de ' + sensor?.nome + ', unidade ' + sensor?.unidade_medida">
              <defs><clipPath :id="'live-clip-' + $.uid"><rect :x="displayed.left-6" y="25" :width="displayed.right-displayed.left+12" :height="displayed.bottom - 19"/></clipPath></defs>
              <text :x="displayed.left" y="18" class="live-axis">{{ sensor?.unidade_medida }}</text>
              <g v-if="displayed.future" class="forecast-region">
              <rect :x="displayed.future.startX" y="36" :width="displayed.future.width" :height="displayed.bottom - 30" class="forecast-shade"/>
              <line :x1="displayed.future.startX" y1="36" :x2="displayed.future.startX" :y2="displayed.bottom + 6" class="forecast-divider"><title>Última leitura real · {{ date(displayed.future.timestamp) }}</title></line>
              <text v-if="!compact" :x="(displayed.left + displayed.future.startX)/2" y="30" text-anchor="middle" class="forecast-region-label">Leituras reais</text>
              <text :x="displayed.future.startX + displayed.future.width/2" y="30" text-anchor="middle" class="forecast-region-label">{{ compact ? ('confirmed' === displayed.projection?.kind ? 'Projeção' : 'Prévia') : projectionLabel(displayed.projection) }}</text>
              <text v-if="!displayed.projection" :x="displayed.future.startX + displayed.future.width/2" :y="(displayed.bottom + 42)/2" text-anchor="middle" class="forecast-region-label">Mínimo: 3 horários</text>
            </g>
            <g v-for="tick in displayed.ticks" :key="tick.y"><line :x1="displayed.left" :y1="tick.y" :x2="displayed.right" :y2="tick.y" class="live-grid"/><text :x="displayed.left-10" :y="tick.y+4" text-anchor="end" class="live-axis">{{ tick.label }}</text></g>
              <g v-for="limit in displayed.limits.filter(t=>t.visible)" :key="limit.name"><line :x1="displayed.left" :y1="limit.y" :x2="displayed.right" :y2="limit.y" :stroke="limit.color" :stroke-dasharray="limit.dash" stroke-width="1.5"/><text v-if="!compact && scale !== 'focus'" :x="displayed.right + 16" :y="limit.y+4" :fill="limit.color" class="live-limit-label">{{ limit.name }} · {{ number(limit.value) }}</text></g>
              <g :clip-path="'url(#live-clip-' + $.uid + ')'">
                <path :d="displayed.path" fill="none" stroke="var(--ice)" stroke-width="2.5" vector-effect="non-scaling-stroke"/>
                <path v-if="displayed.trendPath" :d="displayed.trendPath" class="trend-fit-line"/>
              <g v-if="displayed.projection">
                <path :d="displayed.projection.path" class="trend-projection-line" :class="{'forecast-uncertain':displayed.projection.kind === 'low_confidence'}"/>
                <circle v-if="displayed.projection.breach" :cx="displayed.projection.breach.x" :cy="displayed.projection.breach.y" r="4" class="forecast-breach" tabindex="0" :aria-label="'Alcance estimado do limite: ' + number(displayed.projection.breach.valor) + ' ' + sensor?.unidade_medida + ' em ' + date(displayed.projection.breach.timestamp)"><title>Alcance estimado do limite · {{ number(displayed.projection.breach.valor) }} {{ sensor?.unidade_medida }} · {{ date(displayed.projection.breach.timestamp) }}</title></circle>
              </g>
                              <circle v-for="(point,index) in displayed.points" :key="point.id" :cx="point.x" :cy="point.y" :r="index === displayed.points.length-1 ? 5 : 3" fill="var(--ice)" class="live-point" tabindex="0" role="button" :aria-label="number(point.valor) + ' ' + sensor?.unidade_medida + ' em ' + date(point.timestamp)" @mouseenter="selected=point" @mouseleave="selected=null" @focus="selected=point" @blur="selected=null" @click="selected=point" @keydown.enter="selected=point" @keydown.space.prevent="selected=point"><title>{{ number(point.valor) }} {{ sensor?.unidade_medida }} · {{ date(point.timestamp) }}</title></circle>
              </g>
              <g v-for="label in displayed.annotations" :key="label.id" class="chart-line-label" :class="'chart-line-label-' + label.id">
                <text :x="label.x" :y="label.y" text-anchor="end"><tspan class="chart-line-value">{{ label.text }}</tspan><tspan :x="label.x" dy="15" class="chart-line-caption">{{ label.caption }}</tspan></text>
              </g>
              <text v-for="(time,i) in displayed.times" :key="i" :x="time.x" :y="displayed.height - 25" :text-anchor="i === 0 ? 'start' : i === 2 ? 'end' : 'middle'" class="live-axis">{{ time.label }}</text>
            </svg>
            <p class="live-point-detail" aria-live="polite">{{ detail ? number(detail.valor) + ' ' + sensor?.unidade_medida + ' · ' + date(detail.timestamp) : '' }}</p>
          </div>
          <div v-else class="live-placeholder">{{ busy ? 'Consultando medições…' : sensor?.ativo ? 'Nenhuma medição registrada para este sensor.' : 'Selecione um sensor ativo para acompanhar.' }}</div>
          <p v-if="rows.length" class="live-note">{{ minutes === 'auto' ? 'Janela móvel de até 5 minutos; o histórico antigo fica nas janelas maiores.' : 'Janela encerrada na última medição recebida.' }} <span v-if="showTrend">A tendência visual é recalculada com as leituras desta janela quando novas medições chegam.</span></p>
          <div v-if="displayed.limits.length" class="alarm-thresholds" aria-label="Limites de alarme do sensor"><span v-for="limit in displayed.limits" :key="limit.name" :style="{color:limit.color}">{{ limit.name }} ≥ {{ number(limit.value) }} {{ sensor?.unidade_medida }}<small v-if="!limit.visible"> · {{ limit.position }} da escala</small></span></div>
          <p v-if="displayed.projection" class="forecast-caption">{{ projectionLabel(displayed.projection) }} de até {{ displayed.projection.horizonLabel }} após a última leitura: {{ number(displayed.projection.end.valor) }} {{ sensor?.unidade_medida }} ao final do trecho, se o ritmo continuar.<span v-if="displayed.projection.limitOutside"> O limite fica além deste trecho.</span><span v-if="displayed.projection.reachesLimit"> O marcador indica o alcance estimado do limite.</span><span v-if="displayed.projection.kind !== 'confirmed'"> Prévia visual; alertas e OS dependem da confirmação no servidor.</span></p>
          <footer v-if="rows.length" class="live-footer"><span>{{ rows.length }} medições · última leitura em {{ date(latest.timestamp) }}</span><span v-if="!displayed.limits.length">Limites operacionais indisponíveis</span></footer>
          <p v-if="truncated" class="live-note chart-data-warning">Exibindo as 1.000 medições mais recentes. A janela selecionada contém mais dados.</p>
        </template>
      </section>`
  };
  const sampleComponent = {
    props: ['readings', 'sensor', 'analysis', 'clean', 'horizonMinutes', 'large', 'expanded'],
    setup(props) {
      const compact = useCompact();
      const dimensions = useChartDimensions(props, compact);
      const showHistoryFit = Vue.ref(false);
      const scale = Vue.ref('focus');
      const fitted = Vue.computed(() => {
        const a = props.analysis;
        if (!a?.analysis_enabled) return [];
        // Keep a preliminary visual fit while operational criteria are pending.
        // The visual preview never authorizes an alert or work order.
        return a.regression_line?.length === 2 ? a.regression_line.filter(p => Number.isFinite(Number(p.valor)) && Number.isFinite(Date.parse(p.timestamp))) : fitLine((props.readings || []).map((r,i) => ({...r,id:r.id ?? i})));
      });
      const projected = Vue.computed(() => projectForward((props.readings || []).map((r,i) => ({...r,id:r.id ?? i})), fitted.value, {analysis:props.analysis,limit:props.sensor?.limite_alerta,visual:true,horizonMinutes:props.horizonMinutes}));
      const estimate = Vue.computed(() => projectionSummary(props.analysis));
      const fitMessage = Vue.computed(() => projectionExplanation(projected.value, props.analysis));
      const limits = Vue.computed(() => thresholds(props.sensor));
      const plot = Vue.computed(() => {
        const rows = normalize((props.readings || []).map((r,i) => ({ ...r, id:r.id ?? i })));
        const limit = Number(props.sensor?.limite_alerta);
        // A single operating reference keeps the plot readable; all alarm
        // thresholds remain available below it, using this sensor's actual rules.
        const references = Number.isFinite(limit) && limit > 0 ? [{name:'Limite superior',value:limit,color:'var(--danger)',dash:'8 5'}] : [];
        return chart(rows, null, null, 'auto', null, compact.value, fitted.value, projected.value,
          {focus:scale.value==='focus', futureSpace:true, showFit:showHistoryFit.value || !projected.value, limits:references, ...dimensions.geometry.value});
      });
      return { plotHost: dimensions.host, compact, showHistoryFit, scale, fitted, projected, estimate, fitMessage, limits, plot, number, date, forecastDate, projectionLabel };
    },
    template: `
      <figure ref="plotHost" class="measurement-sample" :class="{'chart-clean':clean,'chart-large':large}">
        <figcaption>Leituras e projeção · {{ sensor?.unidade_medida }}</figcaption>
        <div class="trend-chart-toolbar"><div class="trend-chart-legend" aria-label="Legenda do gráfico"><span><i class="legend-reading"></i>Leituras reais</span><span v-if="plot.trendPath"><i class="legend-trend"></i>{{ analysis?.insufficient_data ? 'Tendência preliminar' : 'Tendência calculada' }}</span><span v-if="plot.projection"><i class="legend-projection"></i>{{ projectionLabel(plot.projection) }}</span><span v-if="plot.limits.some(t=>t.visible)"><i class="legend-limit"></i>Limite superior</span></div><label v-if="projected" class="trend-chart-toggle"><input type="checkbox" v-model="showHistoryFit"> Comparar ajuste no histórico</label></div>
        <label v-if="!clean" class="trend-chart-toggle">Escala<select v-model="scale"><option value="focus">Acompanhar variação</option><option value="limits">Incluir limite superior</option></select></label>
        <details v-if="clean" class="chart-options"><summary>Opções do gráfico</summary><div><label>Escala<select v-model="scale"><option value="focus">Acompanhar variação</option><option value="limits">Incluir limite superior</option></select></label><label><input type="checkbox" v-model="showHistoryFit"> Ajuste no histórico</label></div></details>
        <p class="trend-chart-explanation">{{ fitMessage }}</p>
        <svg :viewBox="'0 0 ' + plot.width + ' ' + plot.height" :style="large ? {height:plot.height + 'px'} : null" role="img" :aria-label="'Leituras reais, tendência e projeção de ' + sensor?.nome">
          <g v-if="plot.future" class="forecast-region">
              <rect :x="plot.future.startX" y="36" :width="plot.future.width" :height="plot.bottom - 30" class="forecast-shade"/>
              <line :x1="plot.future.startX" y1="36" :x2="plot.future.startX" :y2="plot.bottom + 6" class="forecast-divider"><title>Última leitura real · {{ date(plot.future.timestamp) }}</title></line>
              <text v-if="!compact" :x="(plot.left + plot.future.startX)/2" y="30" text-anchor="middle" class="forecast-region-label">Leituras reais</text>
              <text :x="plot.future.startX + plot.future.width/2" y="30" text-anchor="middle" class="forecast-region-label">{{ compact ? ('confirmed' === plot.projection?.kind ? 'Projeção' : 'Prévia') : projectionLabel(plot.projection) }}</text>
              <text v-if="!plot.projection" :x="plot.future.startX + plot.future.width/2" :y="(plot.bottom + 42)/2" text-anchor="middle" class="forecast-region-label">{{ analysis?.analysis_enabled === false ? 'Desativada' : 'Mínimo: 3 horários' }}</text>
            </g>
            <g v-for="tick in plot.ticks" :key="tick.y"><line :x1="plot.left" :y1="tick.y" :x2="plot.right" :y2="tick.y" class="live-grid"/><text :x="plot.left-10" :y="tick.y+4" text-anchor="end" class="live-axis">{{ tick.label }}</text></g>
          <text :x="plot.left" y="18" class="live-axis">{{ sensor?.unidade_medida }}</text>
          <g v-for="limit in plot.limits.filter(t=>t.visible)" :key="limit.name"><line :x1="plot.left" :y1="limit.y" :x2="plot.right" :y2="limit.y" stroke="var(--danger)" stroke-width="1.5" stroke-dasharray="8 5"/><text v-if="!compact && scale !== 'focus'" :x="plot.right + 16" :y="limit.y+4" fill="var(--danger)" class="live-limit-label">Limite · {{ number(limit.value) }}</text></g>
          <path :d="plot.path" fill="none" stroke="var(--ice)" stroke-width="2.5"/>
          <path v-if="plot.trendPath" :d="plot.trendPath" class="trend-fit-line"/>
          <g v-if="plot.projection">
                <path :d="plot.projection.path" class="trend-projection-line" :class="{'forecast-uncertain':plot.projection.kind === 'low_confidence'}"/>
                <circle v-if="plot.projection.breach" :cx="plot.projection.breach.x" :cy="plot.projection.breach.y" r="4" class="forecast-breach" tabindex="0" :aria-label="'Alcance estimado do limite: ' + number(plot.projection.breach.valor) + ' ' + sensor?.unidade_medida + ' em ' + date(plot.projection.breach.timestamp)"><title>Alcance estimado do limite · {{ number(plot.projection.breach.valor) }} {{ sensor?.unidade_medida }} · {{ date(plot.projection.breach.timestamp) }}</title></circle>
              </g>
                        <circle v-for="point in plot.points" :key="point.id" :cx="point.x" :cy="point.y" r="4" fill="var(--ice)" tabindex="0" :aria-label="number(point.valor) + ' ' + sensor?.unidade_medida + ' em ' + date(point.timestamp)"><title>{{ number(point.valor) }} {{ sensor?.unidade_medida }} · {{ date(point.timestamp) }}</title></circle>
          <g v-for="label in plot.annotations" :key="label.id" class="chart-line-label" :class="'chart-line-label-' + label.id">
            <text :x="label.x" :y="label.y" text-anchor="end"><tspan class="chart-line-value">{{ label.text }}</tspan><tspan :x="label.x" dy="15" class="chart-line-caption">{{ label.caption }}</tspan></text>
          </g>
          <text v-for="(time,i) in plot.times" :key="i" :x="time.x" :y="plot.height - 25" :text-anchor="i===0 ? 'start' : i===2 ? 'end' : 'middle'" class="live-axis">{{ time.label }}</text>
        </svg>
        <p v-if="plot.offscaleLimits.length" class="live-note"><span v-for="limit in plot.offscaleLimits" :key="limit.name">{{ limit.name }}: {{ number(limit.value) }} {{ sensor?.unidade_medida }} · {{ limit.position }} da escala. </span>Use “Incluir limite superior” para vê-lo no eixo.</p>
        <p v-if="compact && plot.limits.some(t=>t.visible)" class="live-note">Limite superior: {{ number(plot.limits[0].value) }} {{ sensor?.unidade_medida }}</p>
        <div v-if="limits.length" class="alarm-thresholds" aria-label="Faixas que geram alerta por leitura real"><span>Alerta por leitura real:</span><span v-for="limit in limits" :key="limit.name" :style="{color:limit.color}">{{ limit.name }} ≥ {{ number(limit.value) }} {{ sensor?.unidade_medida }}</span></div>
        <p v-if="analysis?.sample_selection === 'time_distributed'" class="live-note">{{ analysis.readings_count }} leituras reais distribuídas no tempo para preservar a duração mínima. A consistência também foi verificada nas {{ analysis.source_readings_count }} leituras originais desse período.</p>
        <div v-if="plot.points.length" class="live-footer"><span>Início observado: {{ date(plot.points[0].timestamp) }}</span><span>Última leitura real: {{ date(plot.points[plot.points.length-1].timestamp) }}</span></div>
        <p v-if="plot.projection" class="forecast-caption">{{ projectionLabel(plot.projection) }} de até {{ plot.projection.horizonLabel }} após a última leitura: {{ number(plot.projection.end.valor) }} {{ sensor?.unidade_medida }} ao final do trecho, se o ritmo continuar.<span v-if="plot.projection.limitOutside"> O limite fica além deste trecho.</span><span v-if="plot.projection.reachesLimit"> O marcador indica o alcance estimado do limite.</span><span v-if="plot.projection.kind !== 'confirmed'"> Prévia visual; alertas e OS dependem da confirmação no servidor.</span></p>
        <details v-if="estimate" class="trend-estimate"><summary>Ver estimativa de horário até o limite</summary><strong>Por volta de {{ forecastDate(estimate.at) }}</strong><p>Aproximadamente {{ estimate.duration }} após a última medição, registrada em {{ date(estimate.reference) }}.</p><p>Cálculo com a última medição e o ritmo da tendência, se esse ritmo continuar. Estima o alcance do limite, não um horário de falha.</p></details>
      </figure>`
  };
  root.NanaLiveChart = { normalize, thresholds, fitLine, projectionSummary, projectForward, projectionLabel, projectionExplanation, horizonLabel, chart, readings, component, sampleComponent };
})(globalThis);
