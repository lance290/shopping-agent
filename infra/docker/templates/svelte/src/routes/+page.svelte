<script lang="ts">
  const title = 'Svelte + TypeScript';
</script>

<main>
  <h1>{title}</h1>
  <p>Production-ready template from CFOI Framework</p>
  <div class="links">
    <a href="/health" target="_blank">Check Health</a>
    <a href="https://kit.svelte.dev/docs" target="_blank">Documentation</a>
  </div>
</main>

<style>
  main {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2rem;
    font-family: system-ui, sans-serif;
  }

  h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  p {
    font-size: 1.25rem;
    color: #666;
  }

  .links {
    margin-top: 2rem;
    display: flex;
    gap: 1rem;
  }

  a {
    padding: 0.75rem 1.5rem;
    background: #ff3e00;
    color: white;
    border-radius: 0.5rem;
    text-decoration: none;
    transition: opacity 0.2s;
  }

  a:hover {
    opacity: 0.8;
  }
</style>
