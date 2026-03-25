<template>
  <button :class="['btn', `btn-${variant}`]" :disabled="disabled" v-bind="$attrs">
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ variant?: 'primary' | 'ghost' | 'danger'; disabled?: boolean }>()
</script>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background var(--transition),
    border-color var(--transition),
    color var(--transition),
    transform var(--transition),
    box-shadow var(--transition);
  border: 1px solid transparent;
  white-space: nowrap;
  user-select: none;
}
.btn:not(:disabled):active { transform: scale(0.96); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-primary {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}
.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
  box-shadow: 0 0 12px rgba(0,255,136,0.25);
}

.btn-ghost {
  background: transparent;
  color: var(--fg-muted);
  border-color: var(--border);
}
.btn-ghost:hover:not(:disabled) {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: var(--accent-border);
}

.btn-danger {
  background: transparent;
  color: var(--danger);
  border-color: rgba(255,68,68,0.3);
}
.btn-danger:hover:not(:disabled) {
  background: var(--danger-dim);
  box-shadow: 0 0 8px rgba(255,68,68,0.15);
}
</style>
