<script>
  import Camera from "./Camera.svelte";

  let { onSwitch } = $props();

  let username = $state("");
  let faceName = $state("Face 1");
  let capturedBlob = $state(null);
  let error = $state("");
  let ok = $state(false);

  function handleCapture(blob) {
    capturedBlob = blob;
  }

  async function submit() {
    error = "";
    if (!username.trim() || !capturedBlob) {
      error = "Enter a username and capture your face";
      return;
    }
    const fd = new FormData();
    fd.append("username", username.trim());
    fd.append("face_name", faceName.trim() || "Face 1");
    fd.append("face", capturedBlob, "face.jpg");

    const res = await fetch("/api/register", { method: "POST", body: fd });
    if (!res.ok) {
      const data = await res.json();
      error = data.detail || "Registration failed";
      return;
    }
    ok = true;
  }
</script>

<h1>Register</h1>

{#if ok}
  <p class="success">Registered! You can now log in.</p>
  <button onclick={() => onSwitch()}>Go to Login</button>
{:else}
  <input
    type="text"
    placeholder="Username"
    bind:value={username}
  />
  <input
    type="text"
    placeholder="Face name (e.g. Face 1)"
    bind:value={faceName}
  />
  <Camera onCapture={handleCapture} />
  {#if error}<p class="error">{error}</p>{/if}
  <button onclick={submit}>Register</button>
  <p class="switch">
    Already registered?
    <button class="link" onclick={() => onSwitch()}>Log in</button>
  </p>
{/if}

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
    margin-bottom: 0.75rem;
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
  .success {
    color: #16a34a;
    text-align: center;
    margin: 1rem 0;
    font-weight: 600;
  }
  .switch {
    text-align: center;
    margin-top: 1rem;
  }
</style>
