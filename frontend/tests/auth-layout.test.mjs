import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { effectScope, nextTick, reactive, ref, watch } from 'vue'

// Exercise the layout's actual setup logic with Vue reactivity. Stub rendering
// and the network boundary so the session/bootstrap ordering is deterministic.
const source = readFileSync(new URL('../src/components/layout/AuthLayout.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
  .replace(/^import .*$/gm, '')
const setup = new Function(
  'onMounted', 'onUnmounted', 'ref', 'watch', 'useMetricsStore',
  'useAuthStore', 'useWebSocket', 'document', script,
)

function mount(authenticated) {
  const auth = reactive({ isAuthenticated: authenticated })
  const state = { connections: 0, disconnections: 0 }
  const mounted = []
  const unmounted = []
  const scope = effectScope()
  scope.run(() => setup(
    (callback) => mounted.push(callback),
    (callback) => unmounted.push(callback), ref, watch,
    () => ({}), () => auth,
    () => ({
      connect() { if (auth.isAuthenticated) state.connections++ },
      disconnect() { state.disconnections++ },
    }),
    { body: { style: { overflow: '' } } },
  ))
  mounted.forEach((callback) => callback())
  return {
    auth, state,
    unmount() {
      unmounted.forEach((callback) => callback())
      scope.stop()
    },
  }
}

test('connects when the session check finishes after layout mount', async () => {
  const layout = mount(false)
  assert.equal(layout.state.connections, 0)
  layout.auth.isAuthenticated = true
  await nextTick()
  assert.equal(layout.state.connections, 1)
  layout.unmount()
})

test('connects when already authenticated and disconnects on unmount', () => {
  const layout = mount(true)
  assert.equal(layout.state.connections, 1)
  layout.unmount()
  assert.equal(layout.state.disconnections, 1)
})

test('disconnects on logout and reconnects after another login', async () => {
  const layout = mount(true)
  layout.auth.isAuthenticated = false
  await nextTick()
  assert.equal(layout.state.disconnections, 1)
  layout.auth.isAuthenticated = true
  await nextTick()
  assert.equal(layout.state.connections, 2)
  layout.unmount()
  layout.auth.isAuthenticated = false
  await nextTick()
  assert.equal(layout.state.disconnections, 2)
})
