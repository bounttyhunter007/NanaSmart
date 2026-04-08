<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();

const userProfile = ref({
  first_name: 'Usuário',
  last_name: '',
  tipo_usuario: 'usuario',
  cargo: 'Colaborador',
  empresa_nome: ''
});

const activeAlertsCount = ref(0);

const loadData = async () => {
  try {
    const [profileRes, alertsRes] = await Promise.all([
      api.get('auth/me/'),
      api.get('alertas/?status=ativo')
    ]);
    userProfile.value = profileRes.data;
    activeAlertsCount.value = alertsRes.data.count || alertsRes.data.length || 0;
  } catch (error) {
    console.error('Erro ao carregar dados do layout:', error);
  }
};

onMounted(() => {
  loadData();
});

const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  router.push('/login');
};
</script>

<template>
  <div class="layout-container">
    <!-- Sidebar Premium -->
    <aside class="sidebar glass-panel">
      <div class="logo">
        <div class="logo-wrapper">
          <div class="logo-icon"></div>
          <div class="logo-glow"></div>
        </div>
        <h2>Maintainix</h2>
      </div>
      
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" active-class="active">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          Home
        </router-link>
        
        <router-link to="/ativos" class="nav-item" active-class="active">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
            <line x1="12" y1="22.08" x2="12" y2="12" />
          </svg>
          Equipamentos
        </router-link>

        <router-link to="/telemetria" class="nav-item" active-class="active">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20v-6M6 20V10M18 20V4" />
          </svg>
          Telemetria
        </router-link>

        <router-link to="/alertas" class="nav-item" active-class="active">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Alertas
        </router-link>

        <router-link to="/manutencao" class="nav-item" active-class="active">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          Manutenção
        </router-link>
      </nav>
      
      <div class="user-profile-card glass-panel">
        <div class="avatar">
          <span>{{ userProfile.first_name ? userProfile.first_name.charAt(0).toUpperCase() : 'U' }}</span>
          <div class="status-indicator online"></div>
        </div>
        <div class="user-details">
          <p class="u-name">{{ userProfile.first_name }} {{ userProfile.last_name }}</p>
          <p class="u-role">{{ userProfile.cargo }}</p>
        </div>
        <button class="logout-minimal" @click="logout" title="Sair">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="logout-icon"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <header class="top-header glass-panel">
        <div class="header-breadcrumb">
          <span class="root">Maintainix</span>
          <span class="sep">/</span>
          <span class="current">{{ $route.name }}</span>
        </div>

        <div class="header-identity">
          <div class="identity-group" v-if="userProfile.empresa_nome">
            <span class="id-label">Unidade:</span>
            <span class="id-value badge-emerald">{{ userProfile.empresa_nome }}</span>
          </div>
          <div class="v-divider"></div>
          <div class="notification-center">
             <button class="notif-btn" @click="router.push('/alertas')">
               <svg class="icon-notif" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/></svg>
               <span class="notif-count" v-if="activeAlertsCount > 0">{{ activeAlertsCount }}</span>
             </button>
          </div>
        </div>
      </header>

      <div class="content-viewport">
        <router-view v-slot="{ Component }">
          <transition name="page-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: #020617;
  color: #f8fafc;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  border-right: 1px solid rgba(255,255,255,0.05);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 2rem;
}
.logo-wrapper { position: relative; }
.logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, #10b981, #3b82f6); border-radius: 8px; z-index: 2; position: relative; }
.logo-glow { position: absolute; top: 0; left: 0; width: 32px; height: 32px; background: #3b82f6; filter: blur(15px); opacity: 0.5; }
.logo h2 { font-size: 1.4rem; font-weight: 800; letter-spacing: -1px; }

.nav-menu { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
.nav-item {
  display: flex; align-items: center; gap: 0.85rem; padding: 0.85rem 1rem;
  border-radius: 12px; color: #94a3b8; font-weight: 600; font-size: 0.9rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.nav-item:hover { background: rgba(255,255,255,0.03); color: white; transform: translateX(4px); }
.nav-item.active { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border-right: 3px solid #3b82f6; }
.nav-item .icon { width: 20px; height: 20px; }

.user-profile-card {
  margin-top: auto; padding: 1rem; border-radius: 16px;
  display: flex; align-items: center; gap: 0.75rem;
  background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05);
}
.avatar { width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #334155, #0f172a); display: flex; align-items: center; justify-content: center; font-weight: 800; position: relative; }
.status-indicator { position: absolute; bottom: -2px; right: -2px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid #1e293b; }
.status-indicator.online { background: #10b981; box-shadow: 0 0 10px #10b981; }
.u-name { font-size: 0.85rem; font-weight: 700; margin-bottom: 2px; }
.u-role { font-size: 0.7rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
.logout-minimal { margin-left: auto; color: #94a3b8; padding: 0.5rem; border-radius: 8px; transition: 0.2s; }
.logout-minimal:hover { color: #ef4444; background: rgba(239, 68, 68, 0.1); }
.logout-icon { width: 18px; height: 18px; }

/* Main Content */
.main-content { flex: 1; display: flex; flex-direction: column; }
.top-header {
  height: 80px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 2rem; border-bottom: 1px solid rgba(255,255,255,0.05);
  background: rgba(2, 6, 23, 0.8); backdrop-filter: blur(10px);
}
.header-breadcrumb { display: flex; align-items: center; gap: 0.75rem; font-size: 0.9rem; }
.header-breadcrumb .root { font-weight: 800; color: #94a3b8; }
.header-breadcrumb .current { font-weight: 800; color: white; text-transform: capitalize; }
.header-breadcrumb .sep { opacity: 0.3; }

.header-identity { display: flex; align-items: center; gap: 1.5rem; }
.identity-group { display: flex; align-items: center; gap: 0.75rem; }
.id-label { font-size: 0.75rem; font-weight: 800; color: #64748b; text-transform: uppercase; }
.id-value { font-size: 0.85rem; font-weight: 800; padding: 0.4rem 1rem; border-radius: 20px; }
.badge-emerald { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.1); }
.v-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

.notif-btn { position: relative; width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #94a3b8; transition: 0.2s; }
.notif-btn:hover { background: rgba(255,255,255,0.05); color: white; }
.icon-notif { width: 22px; height: 22px; }
.notif-count { position: absolute; top: 10px; right: 10px; min-width: 14px; height: 14px; background: #ef4444; border-radius: 50%; border: 2px solid #020617; font-size: 0.5rem; font-weight: 900; display: flex; align-items: center; justify-content: center; color: white; }

.content-viewport { flex: 1; overflow-y: auto; padding: 2rem; }

/* Transitions */
.page-slide-enter-active, .page-slide-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.page-slide-enter-from { opacity: 0; transform: translateX(20px); }
.page-slide-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
