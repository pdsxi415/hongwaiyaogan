import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import FileUploader from './components/FileUploader.vue';
import AdminLogin from './components/AdminLogin.vue';
import AdminPanel from './components/AdminPanel.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: FileUploader },
    { path: '/admin/login', component: AdminLogin },
    { 
      path: '/admin', 
      component: AdminPanel,
      beforeEnter: (to, from, next) => {
        if (!localStorage.getItem('token')) {
          next('/admin/login')
        } else {
          next()
        }
      }
    }
  ]
});

const app = createApp(App);
app.use(ElementPlus);
app.use(router);
app.mount('#app');