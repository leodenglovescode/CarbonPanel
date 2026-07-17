<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="dialog.active" class="dialog-backdrop" @click.self="onCancel">
        <div class="dialog-panel" role="alertdialog" aria-modal="true">
          <h2 class="dialog-title">{{ dialog.active.title }}</h2>
          <p class="dialog-message">{{ dialog.active.message }}</p>
          <div class="dialog-actions">
            <BaseButton v-if="dialog.active.kind === 'confirm'" variant="ghost" @click="onCancel">
              {{ dialog.active.cancelLabel }}
            </BaseButton>
            <BaseButton :variant="dialog.active.variant" @click="onConfirm">
              {{ dialog.active.confirmLabel }}
            </BaseButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useDialogStore } from '@/stores/dialog'
import BaseButton from './BaseButton.vue'

const dialog = useDialogStore()

function onConfirm() {
  dialog.respond(true)
}
function onCancel() {
  dialog.respond(false)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && dialog.active) onCancel()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

// Autofocus the confirm button so Enter/Space works without a mouse.
watch(
  () => dialog.active,
  async (state) => {
    if (!state) return
    await nextTick()
    document.querySelector<HTMLButtonElement>('.dialog-panel .btn-primary, .dialog-panel .btn-danger')?.focus()
  },
)
</script>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 16px;
}

.dialog-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card-hover);
  padding: 20px;
  width: 100%;
  max-width: 380px;
  font-family: var(--font);
}

.dialog-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--fg);
}

.dialog-message {
  margin: 0 0 18px;
  font-size: 12px;
  color: var(--fg-muted);
  white-space: pre-wrap;
  line-height: 1.5;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity var(--transition);
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
.dialog-fade-enter-active .dialog-panel {
  transition: transform var(--transition);
}
.dialog-fade-enter-from .dialog-panel {
  transform: translateY(4px) scale(0.98);
}
</style>
