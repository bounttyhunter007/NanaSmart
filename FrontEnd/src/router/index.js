import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '../layouts/MainLayout.vue';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Ativos from '../views/Ativos.vue';
import Telemetria from '../views/Telemetria.vue';
import Alertas from '../views/Alertas.vue';
import Manutencao from '../views/Manutencao.vue';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: Home,
      },
      {
        path: 'ativos',
        name: 'Ativos',
        component: Ativos,
      },
      {
        path: 'telemetria',
        name: 'Telemetria',
        component: Telemetria,
      },
      {
        path: 'alertas',
        name: 'Alertas',
        component: Alertas,
      },
      {
        path: 'manutencao',
        name: 'Manutencao',
        component: Manutencao,
      },
      // Future routes (Dashboards) will go here
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Route Guards
router.beforeEach((to, from, next) => {
  const isAuthenticated = !!localStorage.getItem('access_token');
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login');
  } else if (to.name === 'Login' && isAuthenticated) {
    next('/');
  } else {
    next();
  }
});

export default router;
