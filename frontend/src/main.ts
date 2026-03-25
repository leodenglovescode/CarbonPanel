import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

// Apply saved theme before first render to avoid flash
const savedTheme = localStorage.getItem('cp_theme') ?? 'dark'
document.documentElement.setAttribute('data-theme', savedTheme)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
