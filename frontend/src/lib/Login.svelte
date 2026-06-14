<script>
  import Camera from "./Camera.svelte";

  let { onSwitch, onLogin } = $props();

  let username = $state("");
  let capturedBlob = $state(null);
  let error = $state("");
  let loading = $state(false);

  function handleCapture(blob) {
    capturedBlob = blob;
  }

  async function submit() {
    error = "";
    if (!username.trim() || !capturedBlob) {
      error = "Enter your username and capture your face";
      return;
    }
    loading = true;
    const fd = new FormData();
    fd.append("username", username.trim());
    fd.append("face", capturedBlob, "face.jpg");

    const res = await fetch("/api/login", { method: "POST", body: fd });
    loading = false;
    if (!res.ok) {
      const data = await res.json();
      error = data.detail || "Login failed";
      return;
    }
    onLogin();
  }
</script>

<h1>Login</h1>

<input
  type="text"
  placeholder="Username"
  bind:value={username}
  disabled={loading}
/>
<Camera onCapture={handleCapture} />
{#if error}<p class="error">{error}</p>{/if}
<button onclick={submit} disabled={loading}>
  {loading ? "Verifying…" : "Login"}
</button>
<p class="switch">
  No account?
  <button class="link" onclick={() => onSwitch()}>Register</button>
</p>

<style>
  h1 {
    text-align: center;
    margin-bottom: 1.5rem;
  }
  input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid #ccc;
    border-radius: 6px;
    margin-bottom: 1rem;
    font-size: 1rem;
  }
  button {
    display: block;
    width: 100%;
    padding: 0.7rem;
    margin-top: 0.75rem;
    font-size: 1rem;
    border: none;
    border-radius: 6px;
    background: #4f46e5;
    color: #fff;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
  }
  .link {
    display: inline;
    width: auto;
    padding: 0;
    background: none;
    color: #4f46e5;
    text-decoration: underline;
    font-size: inherit;
  }
  .error {
    color: #dc2626;
    text-align: center;
    margin-top: 0.5rem;
  }
  .switch {
    text-align: center;
    margin-top: 1rem;
  }
</style>
