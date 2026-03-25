<template>
  <div class="input-wrap">
    <label v-if="label" :for="id" class="input-label">{{ label }}</label>
    <input
      :id="id"
      v-bind="$attrs"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      class="input"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue?: string
  label?: string
  type?: string
  placeholder?: string
  id?: string
}>()
defineEmits(['update:modelValue'])
</script>

<style scoped>
.input-wrap { display: flex; flex-direction: column; gap: 5px; }
.input-label { font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg-muted); }
.input {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--fg);
  font-family: var(--font);
  font-size: 12px;
  padding: 8px 10px;
  outline: none;
  transition: border-color var(--transition);
  width: 100%;
}
.input:focus { border-color: var(--accent); }
.input::placeholder { color: var(--fg-dim); }
</style>
