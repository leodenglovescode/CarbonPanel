<template>
  <BaseModal
    :open="!!dialog.active"
    :title="dialog.active?.title ?? ''"
    role="alertdialog"
    max-width="380px"
    @close="onCancel"
  >
    <template v-if="dialog.active">
      <p class="dialog-message">{{ dialog.active.message }}</p>
      <div class="dialog-actions">
        <BaseButton
          v-if="dialog.active.kind === 'confirm'"
          variant="ghost"
          data-autofocus
          @click="onCancel"
        >
          {{ dialog.active.cancelLabel }}
        </BaseButton>
        <BaseButton
          :variant="dialog.active.variant"
          :data-autofocus="dialog.active.kind === 'alert' ? '' : undefined"
          @click="onConfirm"
        >
          {{ dialog.active.confirmLabel }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { useDialogStore } from '@/stores/dialog'
import BaseButton from './BaseButton.vue'
import BaseModal from './BaseModal.vue'

const dialog = useDialogStore()

function onConfirm() {
  dialog.respond(true)
}
function onCancel() {
  dialog.respond(false)
}
</script>

<style scoped>
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
</style>
