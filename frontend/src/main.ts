import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

// Apply saved theme before first render to avoid flash
const savedTheme = localStorage.getItem('cp_theme') ?? 'dark'
const resolvedTheme = savedTheme === 'auto'
  ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  : savedTheme
document.documentElement.setAttribute('data-theme', resolvedTheme)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
