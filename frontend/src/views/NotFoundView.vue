<template>
  <main class="not-found">
    <p class="code">404</p>
    <h1>Page not found</h1>
    <p>The address may be incorrect or the page may have moved.</p>
    <RouterLink class="home-link" to="/">Return to dashboard</RouterLink>
  </main>
</template>

<style scoped>
.not-found {
  min-height: 60dvh; display: grid; place-content: center; justify-items: center;
  gap: 10px; padding: 24px; text-align: center; color: var(--fg-muted);
}
.code { margin: 0; color: var(--accent); font-size: clamp(36px, 10vw, 72px); font-weight: 700; }
h1 { margin: 0; color: var(--fg); font-size: 18px; }
p { margin: 0; font-size: 12px; }
.home-link {
  margin-top: 8px; padding: 7px 12px; border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm); color: var(--accent); text-decoration: none;
}
.home-link:hover, .home-link:focus-visible { background: var(--accent-dim); }
</style>
