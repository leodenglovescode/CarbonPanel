import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'primary' | 'danger'
}

export interface AlertOptions {
  title?: string
  message: string
  okLabel?: string
  variant?: 'primary' | 'danger'
}

interface DialogState {
  kind: 'confirm' | 'alert'
  title: string
  message: string
  confirmLabel: string
  cancelLabel: string
  variant: 'primary' | 'danger'
  resolve: (value: boolean) => void
}

export const useDialogStore = defineStore('dialog', () => {
  const active = ref<DialogState | null>(null)

  function confirm(opts: ConfirmOptions): Promise<boolean> {
    return new Promise((resolve) => {
      active.value = {
        kind: 'confirm',
        title: opts.title ?? 'Confirm',
        message: opts.message,
        confirmLabel: opts.confirmLabel ?? 'Confirm',
        cancelLabel: opts.cancelLabel ?? 'Cancel',
        variant: opts.variant ?? 'primary',
        resolve,
      }
    })
  }

  function alert(opts: AlertOptions): Promise<void> {
    return new Promise((resolve) => {
      active.value = {
        kind: 'alert',
        title: opts.title ?? 'Notice',
        message: opts.message,
        confirmLabel: opts.okLabel ?? 'OK',
        cancelLabel: '',
        variant: opts.variant ?? 'primary',
        resolve: () => resolve(),
      }
    })
  }

  function respond(value: boolean) {
    active.value?.resolve(value)
    active.value = null
  }

  return { active, confirm, alert, respond }
})
