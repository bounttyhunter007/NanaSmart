<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import api from '../services/api';

const route = useRoute();

const ordens = ref([]);
const equipamentos = ref([]);
const isLoading = ref(true);
const isModalOpen = ref(false);

const novaOS = ref({
  titulo: '',
  descricao: '',
  equipamento: '',
  prioridade: 'media',
  status: 'pendente'
});

const loadOS = async () => {
  isLoading.value = true;
  try {
    const response = await api.get('ordens-servico/');
    ordens.value = response.data.results || response.data;
    
    // Carregar equipamentos para o select do modal
    const eqRes = await api.get('equipamentos/');
    equipamentos.value = eqRes.data.results || eqRes.data;
    }
  } catch (error) {
    console.error("Erro ao carregar Ordens de Serviço:", error);
  } finally {
    isLoading.value = false;
  }
};

const filterId = computed(() => route.query.id);

const filteredOrdens = computed(() => {
  if (!filterId.value) return ordens.value;
  return ordens.value.filter(os => {
    // Verifica se os.equipamento é objeto ou ID
    const eqId = os.equipamento?.id || os.equipamento;
    return String(eqId) === String(filterId.value);
  });
});

const criarOS = async () => {
  try {
    const response = await api.post('ordens-servico/', novaOS.value);
    ordens.value.unshift(response.data);
    isModalOpen.value = false;
    resetForm();
  } catch (error) {
    console.error("Erro ao criar O.S:", error);
    alert("Erro ao criar Ordem de Serviço. Verifique os campos.");
  }
};

const atualizarStatus = async (os, novoStatus) => {
  try {
    const response = await api.patch(`ordens-servico/${os.id}/`, {
      status: novoStatus
    });
    const index = ordens.value.findIndex(o => o.id === os.id);
    if (index !== -1) {
      ordens.value[index] = response.data;
    }
  } catch (error) {
    console.error("Erro ao atualizar status:", error);
  }
};

const resetForm = () => {
  novaOS.value = {
    titulo: '',
    descricao: '',
    equipamento: '',
    prioridade: 'media',
    status: 'pendente'
  };
};

const getStatusBadge = (status) => {
  if (status === 'concluida') return 'badge-success';
  if (status === 'andamento') return 'badge-primary';
  if (status === 'cancelada') return 'badge-danger';
  return 'badge-warning';
};

const getPrioridadeClass = (prio) => {
  if (prio === 'urgente') return 'text-danger fw-bold';
  if (prio === 'alta') return 'text-warning';
  return '';
};

const formatData = (isoString) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleDateString('pt-BR');
};

onMounted(() => {
  loadOS();
});
</script>

<template>
  <div class="manutencao-view">
    <div class="page-header">
      <div class="title-group">
        <h2>Ordens de Manutenção (O.S)</h2>
        <p>Acompanhamento de reparos e intervenções técnicas</p>
      </div>
      <button class="premium-btn" @click="isModalOpen = true">
        <svg class="icon icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
        Nova Ordem de Serviço
      </button>
    </div>

    <!-- Filtros Rápidos (Opcional Futuro) -->
    
    <div v-if="isLoading && ordens.length === 0" class="loading-state glass-panel">
      <div class="loader-spinner"></div>
      <p>Buscando cronograma de manutenção...</p>
    </div>

    <div v-else-if="ordens.length === 0" class="empty-state glass-panel">
      <svg class="icon-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
      <h3>Nenhuma ordem de serviço</h3>
      <p>Tudo em ordem no parque industrial ou sem manutenções registradas.</p>
    </div>

    <!-- Tabela de O.S -->
    <div v-else class="table-container glass-panel">
      <table class="os-table">
        <thead>
          <tr>
            <th>ID / Data</th>
            <th>Equipamento</th>
            <th>Título / Descrição</th>
            <th>Prioridade</th>
            <th>Status</th>
            <th class="text-right">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="os in filteredOrdens" :key="os.id">
            <td class="font-mono">
              <span class="os-id">#{{ os.id }}</span>
              <div class="os-date">{{ formatData(os.data_abertura) }}</div>
            </td>
            <td>
              <div class="eq-info" v-if="os.equipamento">
                <span class="eq-name">{{ os.equipamento.nome || `Eq. #${os.equipamento}` }}</span>
                <span class="eq-serial" v-if="os.equipamento.numero_serie">{{ os.equipamento.numero_serie }}</span>
              </div>
            </td>
            <td>
              <div class="desc-cell">
                <span class="os-titulo">{{ os.titulo }}</span>
                <p class="os-desc-text">{{ os.descricao }}</p>
              </div>
            </td>
            <td :class="getPrioridadeClass(os.prioridade)">
              {{ os.prioridade.toUpperCase() }}
            </td>
            <td>
              <span class="status-badge" :class="getStatusBadge(os.status)">
                {{ os.status.replace('-', ' ') }}
              </span>
            </td>
            <td class="text-right">
              <div class="action-group">
                <button 
                  v-if="os.status === 'pendente'" 
                  class="btn-icon-action primary" 
                  @click="atualizarStatus(os, 'andamento')"
                  title="Iniciar Manutenção"
                >
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path></svg>
                </button>
                <button 
                  v-if="os.status === 'andamento'" 
                  class="btn-icon-action success" 
                  @click="atualizarStatus(os, 'concluida')"
                  title="Finalizar O.S"
                >
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Nova O.S -->
    <transition name="fade">
      <div class="modal-overlay" v-if="isModalOpen">
        <div class="modal-content glass-panel">
          <div class="modal-header">
            <h3>Gerar Ordem de Serviço</h3>
            <button class="close-btn" @click="isModalOpen = false">×</button>
          </div>
          
          <form @submit.prevent="criarOS" class="modal-form">
            <div class="form-group">
              <label>Equipamento Relacionado *</label>
              <select v-model="novaOS.equipamento" required>
                <option value="" disabled>Selecione a máquina</option>
                <option v-for="eq in equipamentos" :key="eq.id" :value="eq.id">
                  {{ eq.nome }} ({{ eq.numero_serie }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Título da Intervenção *</label>
              <input v-model="novaOS.titulo" type="text" required placeholder="Ex: Substituição de Rolamento" />
            </div>
            
            <div class="form-group">
              <label>Descrição Detalhada</label>
              <textarea v-model="novaOS.descricao" rows="3" placeholder="O que precisa ser feito?"></textarea>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Prioridade</label>
                <select v-model="novaOS.prioridade">
                  <option value="baixa">Baixa</option>
                  <option value="media">Média</option>
                  <option value="alta">Alta</option>
                  <option value="urgente">Urgente (Parada)</option>
                </select>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-cancel" @click="isModalOpen = false">Cancelar</button>
              <button type="submit" class="premium-btn">Abrir Ordem de Serviço</button>
            </div>
          </form>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 2rem;
}

.title-group h2 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.title-group p {
  color: var(--color-text-muted);
}

.table-container {
  overflow: hidden;
  border-radius: var(--radius-lg);
}

.os-table {
  width: 100%;
  border-collapse: collapse;
}

.os-table th {
  padding: 1.25rem 1rem;
  background: rgba(15, 23, 42, 0.4);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.os-table td {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.font-mono { font-family: monospace; }
.os-id { font-weight: 700; color: var(--color-primary); }
.os-date { font-size: 0.75rem; color: var(--color-text-muted); }

.eq-info { display: flex; flex-direction: column; }
.eq-name { font-weight: 600; font-size: 0.95rem; }
.eq-serial { font-size: 0.75rem; color: var(--color-text-muted); }

.desc-cell { max-width: 300px; }
.os-titulo { font-weight: 600; display: block; margin-bottom: 0.25rem; }
.os-desc-text { 
  font-size: 0.8rem; 
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  text-transform: capitalize;
}

.badge-warning { background: rgba(245, 158, 11, 0.1); color: #fbbf24; }
.badge-primary { background: rgba(59, 130, 246, 0.1); color: #60a5fa; }
.badge-success { background: rgba(16, 185, 129, 0.1); color: #34d399; }
.badge-danger { background: rgba(239, 68, 68, 0.1); color: #f87171; }

.action-group {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn-icon-action {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  border: 1px solid rgba(255,255,255,0.05);
}

.btn-icon-action.primary { color: #60a5fa; }
.btn-icon-action.primary:hover { background: #3b82f6; color: white; }

.btn-icon-action.success { color: #34d399; }
.btn-icon-action.success:hover { background: #10b981; color: white; }

.btn-icon-action .icon { width: 18px; height: 18px; }

.text-right { text-align: right; }

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 100%;
  max-width: 550px;
  padding: 2.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.close-btn { font-size: 2rem; color: var(--color-text-muted); }

.modal-form { display: flex; flex-direction: column; gap: 1.5rem; }

.form-group { display: flex; flex-direction: column; gap: 0.6rem; }

label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: 500; }

input, select, textarea {
  padding: 0.85rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: white;
  width: 100%;
  font-family: inherit;
}

input:focus, select:focus, textarea:focus { border-color: var(--color-primary); outline: none; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.btn-cancel { padding: 0.75rem 1.5rem; color: var(--color-text-muted); }

/* Loading & Empty states */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem 2rem;
  text-align: center;
}

.loader-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(59, 130, 246, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1.5rem;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

.icon-lg { width: 64px; height: 64px; margin-bottom: 1.5rem; opacity: 0.3; }
</style>
