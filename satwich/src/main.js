import Vue from 'vue'
import VueRouter from 'vue-router'
import App from './App.vue'
import Example from "./Example.vue"
import Dashboard from "./components/Dashboard.vue"
Vue.use(VueRouter)
Vue.config.productionTip = false

const router= new VueRouter({
  routes: [
    {
      path: '/example',
      name: 'Example',
      component: Example
    },
    {
      path: '/',
      name: 'Default',
      component: Dashboard
    },
  ]
})

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')