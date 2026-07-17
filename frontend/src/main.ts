import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
// Self-hosted (OFL-1.1 licensed) instead of the Google Fonts CDN — the page
// no longer has to wait on an external font host before it can render text.
import '@fontsource/jetbrains-mono/300.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import '@fontsource/jetbrains-mono/600.css'
import '@fontsource/jetbrains-mono/700.css'
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
