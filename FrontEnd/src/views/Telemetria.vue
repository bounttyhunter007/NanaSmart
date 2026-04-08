<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import api from '../services/api';

const route = useRoute();

const equipamentosAgrupados = ref({});
const isLoading = ref(true);
let pollingTimer = null;

const loadTelemetria = async () => {
  try {
    // 1. Buscamos equipamentos
    const resEq = await api.get('equipamentos/');
    const eqs = resEq.data.results || resEq.data;

    // 2. Buscamos sensores
    const resSensores = await api.get('telemetria/sensores/');
    const sensores = resSensores.data.results || resSensores.data;

    // 3. Buscamos as últimas leituras
    const resLeituras = await api.get('telemetria/leituras/?limit=50');
    const ultimasLeituras = resLeituras.data.results || resLeituras.data;

    const mapaLeituras = {};
    ultimasLeituras.forEach(l => {
      if (!mapaLeituras[l.sensor]) mapaLeituras[l.sensor] = l;
    });
    
    // Anexa a leitura ao sensor
    const sensoresComLeitura = sensores.map(s => ({
      ...s,
      leitura: mapaLeituras[s.id]
    }));

    // Agrupa sensores dentro de seus equipamentos
    const agrupamento = {};
    
    // Inicializa estrutura para todos equipamentos encontrados
    eqs.forEach(eq => {
      agrupamento[eq.id] = {
        ...eq,
        sensores: []
      };
    });

    // Coloca cada sensor dentro do equipamento certo
    sensoresComLeitura.forEach(s => {
      if (s.equipamento && s.equipamento.id && agrupamento[s.equipamento.id]) {
        agrupamento[s.equipamento.id].sensores.push(s);
      } else if (s.equipamento && agrupamento[s.equipamento]) {
        // Fallback caso a API retorne just ID em vez de objeto json no sensor
        agrupamento[s.equipamento].sensores.push(s);
      }
    });

    equipamentosAgrupados.value = agrupamento;

  } catch (error) {
    console.error('Erro ao buscar dados de telemetria', error);
  } finally {
    isLoading.value = false;
  }
};

const filterId = computed(() => route.query.id);

const filteredEquipamentos = computed(() => {
  const all = Object.values(equipamentosAgrupados.value);
  if (!filterId.value) return all;
  return all.filter(eq => String(eq.id) === String(filterId.value));
});

onMounted(() => {
  loadTelemetria();
  pollingTimer = setInterval(() => {
    loadTelemetria();
  }, 5000);
});

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer);
});

// Calcula qual a cor geral do Equipamento baseado no pior sensor
const getEquipamentoHealth = (eq) => {
  if (!eq.sensores || eq.sensores.length === 0) return 'neutral';
  let hasWarning = false;
  
  for (const s of eq.sensores) {
    const status = getHealthStatus(s);
    if (status.color === 'danger') return 'danger';
    if (status.color === 'warning') hasWarning = true;
  }
  
  return hasWarning ? 'warning' : 'success';
};

const getHealthStatus = (sensor) => {
  if (!sensor.leitura) return { color: 'neutral', text: 'Off' };
  const v = sensor.leitura.valor;
  const t = sensor.tipo_sensor;

  if (t === 'temperatura') {
    if (v > 85) return { color: 'danger', text: 'Crítico' };
    if (v > 70) return { color: 'warning', text: 'Alerta' };
    return { color: 'success', text: 'Normal' };
  }
  
  if (t === 'vibracao') {
    if (v > 15) return { color: 'danger', text: 'Crítico' };
    if (v > 10) return { color: 'warning', text: 'Alerta' };
    return { color: 'success', text: 'Normal' };
  }

  if (v > 80) return { color: 'warning', text: 'Alta' };
  return { color: 'success', text: 'Normal' };
};

const formatTime = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second:'2-digit' });
};
</script>

<template>
  <div class="telemetria-view">
    <div class="page-header">
      <div class="title-group">
        <h2>Telemetria Consolidada <span class="live-dot"></span></h2>
        <p>Visão global dos equipamentos e seus respectivos parâmetros vitais em tempo real</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading && Object.keys(equipamentosAgrupados).length === 0" class="loading-state glass-panel">
      <div class="loader-spinner"></div>
      <p>Estabelecendo conexão multicanal...</p>
    </div>

    <div v-else-if="Object.keys(equipamentosAgrupados).length === 0" class="empty-state glass-panel">
      <h3>Nenhum equipamento monitorado com telemetria</h3>
    </div>

    <!-- Painel de Grids por EQUIPAMENTO -->
    <div v-else class="equipamentos-grid">
      <div 
        class="equipamento-card glass-panel" 
        v-for="eq in filteredEquipamentos" 
        :key="eq.id"
      >
        <div class="eq-header" :class="`border-${getEquipamentoHealth(eq)}`">
          <div class="eq-info-main">
            <h3>{{ eq.nome }}</h3>
            <span class="eq-serial">S/N: {{ eq.numero_serie }}</span>
          </div>
          <div class="status-bolinha" :class="`bg-${getEquipamentoHealth(eq)}`"></div>
        </div>

        <div class="eq-body">
          <div v-if="!eq.sensores || eq.sensores.length === 0" class="sem-sensores">
            Nenhum sensor atrelado.
          </div>
          
          <div v-else class="sensores-list">
            <div 
              class="sensor-item" 
              v-for="s in eq.sensores" 
              :key="s.id"
              :class="`bg-light-${getHealthStatus(s).color}`"
            >
              <div class="sensor-title-col">
                <span class="s-type">{{ s.tipo_sensor }}</span>
                <span class="s-last-sync" v-if="s.leitura">◷ {{ formatTime(s.leitura.data_hora) }}</span>
                <span class="s-last-sync" v-else>Off</span>
              </div>
              
              <div class="sensor-val-col" :class="`text-${getHealthStatus(s).color}`">
                <span class="s-val">{{ s.leitura ? Number(s.leitura.valor).toFixed(1) : '-' }}</span>
                <span class="s-unit">{{ s.unidade_medida }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="eq-footer">
           <button class="grafico-btn">Abrir Painel Completo</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 2rem;
}

.title-group h2 {
  font-size: 1.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.live-dot {
  width: 12px;
  height: 12px;
  background-color: var(--color-danger);
  border-radius: 50%;
  display: inline-block;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.8);
  animation: pulse-red 1.5s infinite;
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.title-group p {
  color: var(--color-text-muted);
}

.equipamentos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.5rem;
}

.equipamento-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  transition: transform 0.2s, box-shadow 0.2s;
}

.equipamento-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.2);
}

.eq-header {
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: rgba(15, 23, 42, 0.4);
  border-left: 4px solid var(--color-border);
}

.eq-header.border-success { border-left-color: #10b981; }
.eq-header.border-warning { border-left-color: #f59e0b; }
.eq-header.border-danger { border-left-color: #ef4444; }

.eq-info-main h3 {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
  letter-spacing: -0.3px;
}

.eq-serial {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-family: monospace;
}

.status-bolinha {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  margin-top: 0.25rem;
}
.bg-success { background-color: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.5); }
.bg-warning { background-color: #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.5); }
.bg-danger { background-color: #ef4444; box-shadow: 0 0 10px rgba(239,68,68,0.8); animation: pulse-red 1s infinite;}
.bg-neutral { background-color: #64748b; }

.eq-body {
  padding: 1rem 1.25rem;
  flex: 1;
}

.sem-sensores {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  text-align: center;
  padding: 1rem 0;
  opacity: 0.6;
}

.sensores-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sensor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255,255,255, 0.02);
}

.bg-light-success { border-left: 2px solid #10b981; }
.bg-light-warning { border-left: 2px solid #f59e0b; background: rgba(245,158,11, 0.05); }
.bg-light-danger { border-left: 2px solid #ef4444; background: rgba(239,68,68, 0.1); }
.bg-light-neutral { border-left: 2px solid #475569; }

.sensor-title-col {
  display: flex;
  flex-direction: column;
}

.s-type {
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text);
}

.s-last-sync {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.sensor-val-col {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.s-val {
  font-size: 1.4rem;
  font-weight: 700;
}

.s-unit {
  font-size: 0.8rem;
  opacity: 0.8;
}

.text-success { color: #10b981; }
.text-warning { color: #f59e0b; }
.text-danger { color: #ef4444; text-shadow: 0 0 10px rgba(239,68,68,0.4); }
.text-neutral { color: var(--color-text-muted); }

.eq-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(0, 0, 0, 0.1);
}

.grafico-btn {
  width: 100%;
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 0.5rem;
  border-radius: var(--radius-md);
}

.grafico-btn:hover {
  background: rgba(59, 130, 246, 0.1);
}
</style>
