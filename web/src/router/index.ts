import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import LabPage from '../pages/LabPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage },
    { path: '/lab', component: LabPage },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})
