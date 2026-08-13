<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="modal-overlay" @pointerdown.self="emit('close')">
        <section
          ref="panelEl"
          class="modal-panel"
          :style="{ maxWidth }"
          :role="role"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          @keydown="onKeydown"
        >
          <header class="modal-header">
            <h2 :id="titleId" class="modal-title">{{ title }}</h2>
            <button type="button" class="modal-close" aria-label="Close dialog" @click="emit('close')">
              ✕
            </button>
          </header>
          <div class="modal-body">
            <slot />
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onUnmounted, ref, useId, watch } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  title: string
  maxWidth?: string
  role?: 'dialog' | 'alertdialog'
}>(), {
  maxWidth: '440px',
  role: 'dialog',
})

const emit = defineEmits<{ close: [] }>()
const panelEl = ref<HTMLElement | null>(null)
const titleId = `modal-title-${useId()}`
let previousFocus: HTMLElement | null = null
let previousOverflow = ''

function focusableElements(): HTMLElement[] {
  if (!panelEl.value) return []
  return Array.from(panelEl.value.querySelectorAll<HTMLElement>(
    'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  )).filter((el) => !el.hasAttribute('hidden'))
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return

  const focusable = focusableElements()
  if (!focusable.length) {
    event.preventDefault()
    panelEl.value?.focus()
    return
  }

  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previousFocus = document.activeElement as HTMLElement | null
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      await nextTick()
      const initial = panelEl.value?.querySelector<HTMLElement>(
        '[data-autofocus], [autofocus], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)',
      )
      ;(initial ?? panelEl.value)?.focus()
    } else {
      document.body.style.overflow = previousOverflow
      await nextTick()
      previousFocus?.focus()
      previousFocus = null
    }
  },
)

onUnmounted(() => {
  document.body.style.overflow = previousOverflow
  previousFocus?.focus()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
}
.modal-panel {
  width: 100%;
  max-height: min(90dvh, 760px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card-hover);
  color: var(--fg);
  font-family: var(--font);
}
.modal-panel:focus { outline: 1px solid var(--accent-border); }
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.modal-title { margin: 0; font-size: 13px; font-weight: 600; }
.modal-close {
  min-width: 32px;
  min-height: 32px;
  background: none;
  border: none;
  color: var(--fg-dim);
  font: 14px/1 var(--font);
  cursor: pointer;
}
.modal-close:hover, .modal-close:focus-visible { color: var(--fg); }
.modal-body { min-height: 0; overflow-y: auto; padding: 16px; }
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity var(--transition); }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-active .modal-panel { transition: transform var(--transition); }
.modal-fade-enter-from .modal-panel { transform: translateY(4px) scale(0.98); }
</style>
