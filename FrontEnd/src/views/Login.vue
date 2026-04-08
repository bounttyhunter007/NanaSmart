<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
const username = ref('');
const password = ref('');
const error = ref('');
const isLoading = ref(false);

const handleLogin = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    const response = await api.post('auth/token/', {
      username: username.value,
      password: password.value,
    });
    localStorage.setItem('access_token', response.data.access);
    localStorage.setItem('refresh_token', response.data.refresh);
    router.push('/');
  } catch (err) {
    error.value = 'Credenciais inválidas. Verifique seu usuário e senha.';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <!-- Background Hero Image -->
    <div class="hero-background">
       <img src="../assets/industrial_hero.png" alt="Industrial Hero" class="hero-image" />
       <div class="hero-overlay"></div>
    </div>

    <div class="login-container animate-fade-in">
      <div class="login-card glass-panel">
        <div class="brand">
          <div class="brand-logo"></div>
          <h1>Maintainix <span class="v-tag">v2.0</span></h1>
          <p class="brand-slogan">Inteligência Preditiva & Gestão de Ativos</p>
        </div>

        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label>NOME DE USUÁRIO</label>
            <div class="input-wrapper">
              <svg class="icon-input" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <input v-model="username" type="text" placeholder="ex: ana.beatriz" required @focus="error = ''" />
            </div>
          </div>

          <div class="form-group">
            <label>SENHA CORPORATIVA</label>
            <div class="input-wrapper">
              <svg class="icon-input" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <input v-model="password" type="password" placeholder="••••••••" required @focus="error = ''" />
            </div>
          </div>

          <transition name="shake">
            <div v-if="error" class="error-msg">
              <svg class="icon-msg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              {{ error }}
            </div>
          </transition>

          <button type="submit" class="submit-btn" :disabled="isLoading">
            <span v-if="!isLoading">Acessar Plataforma</span>
            <div v-else class="loader-mini"></div>
          </button>
        </form>

        <div class="login-footer">
          <p>Esqueceu sua senha? Entre em contato com o <strong>PCM</strong>.</p>
        </div>
      </div>
      
      <div class="copyright">
        &copy; 2026 Maintainix Industrial Systems. Todos os direitos reservados.
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #020617;
}

/* Background Section */
.hero-background {
  position: absolute;
  inset: 0;
  z-index: 1;
}
.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: brightness(0.4) saturate(1.2);
  transform: scale(1.05);
  animation: slowZoom 30s linear infinite alternate;
}
@keyframes slowZoom {
  from { transform: scale(1); }
  to { transform: scale(1.15); }
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, transparent, #020617 80%);
}

/* Login Card Area */
.login-container {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.login-card {
  padding: 3rem 2.5rem;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(25px);
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 40px 100px rgba(0,0,0,0.8);
}

.brand {
  text-align: center;
  margin-bottom: 2.5rem;
}
.brand-logo {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #10b981, #3b82f6);
  border-radius: 12px;
  margin: 0 auto 1.5rem;
  box-shadow: 0 0 30px rgba(59, 130, 246, 0.4);
}
.brand h1 {
  font-size: 2.4rem;
  font-weight: 800;
  letter-spacing: -2px;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
.v-tag {
  font-size: 0.7rem;
  background: rgba(255,255,255,0.05);
  padding: 2px 8px;
  border-radius: 4px;
  color: #64748b;
  font-weight: 600;
}
.brand-slogan {
  color: #94a3b8;
  font-size: 0.85rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.form-group label {
  font-size: 0.7rem;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.8px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.icon-input {
  position: absolute;
  left: 1rem;
  width: 18px;
  height: 18px;
  color: #475569;
}
.input-wrapper input {
  width: 100%;
  padding: 1rem 1rem 1rem 3rem;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  color: white;
  font-size: 0.95rem;
  transition: all 0.3s;
}
.input-wrapper input:focus {
  outline: none;
  background: rgba(0,0,0,0.5);
  border-color: #3b82f6;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.2);
}

.submit-btn {
  margin-top: 1rem;
  padding: 1.1rem;
  background: white;
  color: black;
  border: none;
  border-radius: 12px;
  font-weight: 800;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.submit-btn:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 15px 30px rgba(255,255,255,0.15);
  background: #f1f5f9;
}
.submit-btn:active { transform: translateY(0); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.error-msg {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.8rem;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border-left: 3px solid #ef4444;
}
.icon-msg { width: 16px; height: 16px; flex-shrink: 0; }

.login-footer {
  text-align: center;
  margin-top: 1.5rem;
  font-size: 0.75rem;
  color: #64748b;
}

.copyright {
  text-align: center;
  font-size: 0.75rem;
  color: #475569;
}

/* Animations */
.animate-fade-in { animation: fadeIn 1s ease-out both; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

.shake-enter-active { animation: shake 0.4s; }
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.loader-mini {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0,0,0,0.1);
  border-top-color: black;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
