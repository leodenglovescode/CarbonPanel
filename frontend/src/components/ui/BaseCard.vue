<template>
  <div class="card">
    <div v-if="$slots.header || title" class="card-header">
      <slot name="header">
        <span class="card-title">{{ title }}</span>
      </slot>
    </div>
    <div class="card-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<style scoped>
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition:
    border-color var(--transition),
    box-shadow var(--transition),
    background var(--transition);
}

.card:hover {
  border-color: rgba(128,128,128,0.2);
  box-shadow: var(--shadow-card-hover);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--border-subtle);
  transition: border-color var(--transition);
}

.card-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}

.card-body {
  padding: 12px 14px;
}
</style>
