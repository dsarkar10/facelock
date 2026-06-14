<script>
  import { onMount } from "svelte";
  import Register from "./lib/Register.svelte";
  import Login from "./lib/Login.svelte";
  import Dashboard from "./lib/Dashboard.svelte";

  let page = $state("loading");

  onMount(async () => {
    try {
      const res = await fetch("/api/me");
      if (res.ok) {
        page = "dashboard";
      } else {
        page = "login";
      }
    } catch {
      page = "login";
    }
  });
</script>

<main class:wide={page === "dashboard"}>
  {#if page === "loading"}
    <p style="text-align:center;margin-top:4rem;">Loading…</p>
  {:else if page === "register"}
    <Register onSwitch={() => page = "login"} />
  {:else if page === "login"}
    <Login onSwitch={() => page = "register"} onLogin={() => page = "dashboard"} />
  {:else if page === "dashboard"}
    <Dashboard onLogout={() => page = "login"} />
  {/if}
</main>

<style>
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  :global(body) {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #222;
    min-height: 100vh;
  }
  main {
    max-width: 480px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }
  main.wide {
    max-width: none;
    margin: 0;
    padding: 0;
  }
</style>
