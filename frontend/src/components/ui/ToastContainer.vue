<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div
          v-for="t in alerts.toasts"
          :key="t.id"
          :class="['toast', `toast-${t.level}`]"
          @click="alerts.dismiss(t.id)"
        >
          <span class="toast-icon">{{ t.level === 'danger' ? '⚠' : '!' }}</span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useAlertsStore } from '@/stores/alerts'
const alerts = useAlertsStore()
</script>

<style scoped>
.toast-stack {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 9999;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: var(--radius);
  border: 1px solid;
  font-size: 11px;
  font-family: var(--font);
  cursor: pointer;
  pointer-events: auto;
  min-width: 220px;
  max-width: 340px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  transition: opacity var(--transition), transform var(--transition);
}

.toast-warning {
  background: var(--warning-dim);
  border-color: rgba(255,170,0,0.35);
  color: var(--warning);
}
.toast-danger {
  background: var(--danger-dim);
  border-color: rgba(255,68,68,0.35);
  color: var(--danger);
}

.toast-icon { font-size: 12px; flex-shrink: 0; }
.toast-msg  { flex: 1; color: var(--fg); }
.toast-close {
  background: none; border: none; color: var(--fg-dim);
  font-size: 10px; cursor: pointer; padding: 0; line-height: 1;
  flex-shrink: 0;
}
.toast-close:hover { color: var(--fg); }

/* TransitionGroup animations */
.toast-enter-active { transition: opacity 200ms ease, transform 200ms ease; }
.toast-leave-active { transition: opacity 180ms ease, transform 180ms ease; }
.toast-enter-from   { opacity: 0; transform: translateX(24px); }
.toast-leave-to     { opacity: 0; transform: translateX(24px); }
</style>
