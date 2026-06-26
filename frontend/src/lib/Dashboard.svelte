<script>
  import { onMount } from "svelte";
  import Camera from "./Camera.svelte";

  let { onLogout } = $props();

  let notifications = $state([]);
  let username = $state("");
  let activeTab = $state("home");

  let ip = $state("");
  let ua = $state("");
  let connType = $state("unknown");
  let downlink = $state(0);
  let rtt = $state(0);
  let online = $state(true);
  let netUpdated = $state("");

  let history = $state([]);
  let faces = $state([]);
  let faceName = $state("");
  let newFaceName = $state("Face ");
  let newFaceBlob = $state(null);
  let editingId = $state(null);
  let editingName = $state("");
  let showingAdd = $state(false);

  let domains = $state([]);
  let newDomain = $state("");
  let domainMsg = $state("");

  let blockedIps = $state([]);
  let newIp = $state("");
  let newIpPort = $state("");
  let newIpProto = $state("tcp");
  let ipMsg = $state("");

  let fwStatus = $state(null);
  let fwMsg = $state("");

  let netTimer;

  onMount(async () => {
    const me = await fetch("/api/me");
    if (me.ok) {
      const data = await me.json();
      username = data.username;
      faceName = data.face_name || "";
    }
    await loadNotifications();
    await loadHistory();
    await loadFaces();
    startNetworkPoll();
  });

  function startNetworkPoll() {
    pollNetwork();
    netTimer = setInterval(pollNetwork, 3000);
  }

  async function pollNetwork() {
    const res = await fetch("/api/network-info");
    if (res.ok) {
      const data = await res.json();
      ip = data.ip;
      ua = data.user_agent;
    }
    online = navigator.onLine;
    const c = navigator.connection;
    if (c) {
      connType = c.effectiveType || "unknown";
      downlink = c.downlink;
      rtt = c.rtt;
    }
    netUpdated = new Date().toLocaleTimeString();
  }

  async function loadNotifications() {
    const res = await fetch("/api/notifications");
    if (res.ok) {
      const data = await res.json();
      notifications = data.notifications;
    }
  }

  async function loadHistory() {
    const res = await fetch("/api/history");
    if (res.ok) {
      const data = await res.json();
      history = data.history;
    }
  }

  async function loadFaces() {
    const res = await fetch("/api/faces");
    if (res.ok) {
      const data = await res.json();
      faces = data.faces;
    }
  }

  async function addFace() {
    if (!newFaceBlob) return;
    const fd = new FormData();
    fd.append("face_name", newFaceName.trim() || "Face");
    fd.append("face", newFaceBlob, "face.jpg");
    await fetch("/api/faces", { method: "POST", body: fd });
    newFaceBlob = null;
    newFaceName = "Face ";
    await loadFaces();
  }

  function startEdit(face) {
    editingId = face.id;
    editingName = face.face_name;
  }

  async function saveEdit(faceId) {
    if (!editingName.trim()) return;
    const fd = new FormData();
    fd.append("face_name", editingName.trim());
    await fetch("/api/faces/" + faceId, { method: "PUT", body: fd });
    editingId = null;
    await loadFaces();
  }

  function cancelEdit() {
    editingId = null;
  }

  async function removeFace(faceId) {
    if (!confirm("Delete this face ID?")) return;
    await fetch("/api/faces/" + faceId, { method: "DELETE" });
    await loadFaces();
  }

  async function dismiss() {
    await fetch("/api/notifications/dismiss", { method: "POST" });
    notifications = [];
  }

  async function logout() {
    clearInterval(netTimer);
    await fetch("/api/logout", { method: "POST" });
    onLogout();
  }

  async function loadDomains() {
    const res = await fetch("/api/block/domains");
    if (res.ok) {
      const data = await res.json();
      domains = data.domains;
    }
  }

  async function addDomain() {
    if (!newDomain.trim()) return;
    const fd = new FormData();
    fd.append("domain", newDomain.trim());
    const res = await fetch("/api/block/domains", { method: "POST", body: fd });
    domainMsg = "";
    if (res.ok || res.status === 409) {
      const data = await res.json();
      domainMsg = data.message || (res.ok ? "Blocked" : "Already blocked");
    } else {
      domainMsg = "Failed to block domain";
    }
    newDomain = "";
    await loadDomains();
  }

  async function removeDomain(id) {
    await fetch("/api/block/domains/" + id, { method: "DELETE" });
    await loadDomains();
  }

  async function loadBlockedIps() {
    const res = await fetch("/api/block/ips");
    if (res.ok) {
      const data = await res.json();
      blockedIps = data.ips;
    }
  }

  async function addIp() {
    if (!newIp.trim()) return;
    const fd = new FormData();
    fd.append("ip", newIp.trim());
    if (newIpPort.trim()) fd.append("port", newIpPort.trim());
    fd.append("protocol", newIpProto);
    const res = await fetch("/api/block/ips", { method: "POST", body: fd });
    ipMsg = "";
    if (res.ok || res.status === 409) {
      const data = await res.json();
      ipMsg = data.message || (res.ok ? "Blocked" : "Already blocked");
    } else {
      ipMsg = "Failed to block IP";
    }
    newIp = "";
    newIpPort = "";
    await loadBlockedIps();
  }

  async function removeIp(id) {
    await fetch("/api/block/ips/" + id, { method: "DELETE" });
    await loadBlockedIps();
  }

  async function loadFirewallStatus() {
    const res = await fetch("/api/firewall/status");
    if (res.ok) {
      fwStatus = await res.json();
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    if (tab === "blocklist") {
      loadDomains();
      loadBlockedIps();
      loadFirewallStatus();
    }
  }
</script>

<div class="layout">
  <aside class="sidebar">
    <div class="user-block">
      <div class="avatar">{username.slice(0, 2).toUpperCase()}</div>
      <span class="uname">{username}</span>
    </div>

    <nav class="nav">
      <button class="nav-item" class:active={activeTab === "home"} onclick={() => switchTab("home")}>
        Home
      </button>
      <button class="nav-item" class:active={activeTab === "security"} onclick={() => switchTab("security")}>
        Security
        {#if notifications.length > 0}
          <span class="badge">{notifications.length}</span>
        {/if}
      </button>
      <button class="nav-item" class:active={activeTab === "network"} onclick={() => switchTab("network")}>
        Network
      </button>
      <button class="nav-item" class:active={activeTab === "history"} onclick={() => switchTab("history")}>
        History
      </button>
      <button class="nav-item" class:active={activeTab === "blocklist"} onclick={() => switchTab("blocklist")}>
        Blocklist
      </button>
      <button class="nav-item" class:active={activeTab === "faceid"} onclick={() => switchTab("faceid")}>
        Face ID
      </button>
    </nav>

    <div class="spacer"></div>

    <button class="logout-btn" onclick={logout}>Logout</button>
  </aside>

  <main class="content">
    {#if activeTab === "home"}
      {@const regEvent = history.find(h => h.attempt_type === "REGISTER")}
      {@const lastLogin = history.find(h => h.attempt_type === "LOGIN")}
      {@const failedCount = history.filter(h => h.attempt_type === "FAILED_LOGIN").length}

      <div class="home-header">
        <div>
          <h1>Dashboard</h1>
          <p class="sub">Face Recognition Security System</p>
        </div>
        <div class="status-badge" class:green={!notifications.length} class:red={notifications.length > 0}>
          {#if notifications.length > 0}
            &#9888; Review Required
          {:else}
            &#10003; All Secure
          {/if}
        </div>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-label">Account Age</span>
          <span class="stat-value">{regEvent ? Math.floor((Date.now() - new Date(regEvent.timestamp).getTime()) / 86400000) + " days" : "—"}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Failed Attempts</span>
          <span class="stat-value" class:red={failedCount > 0}>{failedCount}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Last Login</span>
          <span class="stat-value">{lastLogin ? new Date(lastLogin.timestamp).toLocaleDateString() : "—"}</span>
        </div>
      </div>

      {#if notifications.length > 0}
        <div class="alert-banner">
          <strong>{notifications.length}</strong> unread security alert{notifications.length > 1 ? "s" : ""}
          <button class="text-btn" onclick={() => switchTab("security")}>Review</button>
        </div>
      {/if}

      <section class="section">
        <h2>Recent Activity</h2>
        <div class="alert-card">
          {#each history.slice(0, 5) as h}
            <div class="log-row">
              <span class="log-icon">
                {#if h.attempt_type === "REGISTER"}
                  &#128221;
                {:else if h.attempt_type === "LOGIN"}
                  &#128274;
                {:else}
                  &#9888;
                {/if}
              </span>
              <div class="log-detail">
                <span class="log-type">
                  {#if h.attempt_type === "REGISTER"}
                    Account created
                  {:else if h.attempt_type === "LOGIN"}
                    Successful login
                  {:else}
                    Failed login attempt
                  {/if}
                </span>
                <span class="log-time">{new Date(h.timestamp).toLocaleString()}</span>
              </div>
            </div>
          {:else}
            <p class="empty">No activity yet.</p>
          {/each}
        </div>
      </section>

      <section class="section">
        <h2>Current Session</h2>
        <div class="session-card">
          <div class="session-row">
            <span class="s-label">IP Address</span>
            <span class="s-value">{ip || "—"}</span>
          </div>
          <div class="session-row">
            <span class="s-label">Connection</span>
            <span class="s-value">{connType.toUpperCase()}</span>
          </div>
          <div class="session-row">
            <span class="s-label">Downlink / RTT</span>
            <span class="s-value">{downlink.toFixed(1)} Mb/s &middot; {rtt} ms</span>
          </div>
          <div class="session-row">
            <span class="s-label">Status</span>
            <span class="s-value" class:green={online} class:red={!online}>{online ? "Online" : "Offline"}</span>
          </div>
          <div class="session-row last">
            <span class="s-label">Browser</span>
            <span class="s-value small">{ua || "—"}</span>
          </div>
        </div>
      </section>

    {:else if activeTab === "security"}
      <h1>Security Logs</h1>

      {#if notifications.length > 0}
        <div class="alert-card">
          <div class="card-header">
            <h3>Failed Login Attempts</h3>
            <button class="dismiss-btn" onclick={dismiss}>Dismiss All</button>
          </div>
          {#each notifications as n}
            <div class="log-row snap-row">
              <span class="log-icon">&#9888;</span>
              <div class="log-detail">
                <span class="log-type">Unauthorized login attempt</span>
                <span class="log-time">{new Date(n.timestamp).toLocaleString()}</span>
                {#if n.snapshot_path}
                  <img src="/api/snapshots/{n.id}" alt="Failed login snapshot" class="snap-img" loading="lazy" />
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="safe">No failed login attempts recorded.</p>
      {/if}

    {:else if activeTab === "history"}
      <h1>Activity History</h1>
      <p class="sub">All account events in chronological order</p>

      {#if history.length > 0}
        <div class="alert-card">
          <div class="card-header">
            <h3>Events ({history.length})</h3>
          </div>
          {#each history as h}
            <div class="log-row snap-row">
              <span class="log-icon">
                {#if h.attempt_type === "REGISTER"}
                  &#128221;
                {:else if h.attempt_type === "LOGIN"}
                  &#128274;
                {:else}
                  &#9888;
                {/if}
              </span>
              <div class="log-detail">
                <span class="log-type">
                  {#if h.attempt_type === "REGISTER"}
                    Account created
                  {:else if h.attempt_type === "LOGIN"}
                    Successful login
                  {:else}
                    Failed login attempt
                  {/if}
                </span>
                <span class="log-time">{new Date(h.timestamp).toLocaleString()}</span>
                {#if h.snapshot_path}
                  <img src="/api/snapshots/{h.id}" alt="Failed login snapshot" class="snap-img" loading="lazy" />
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="safe">No history yet.</p>
      {/if}

    {:else if activeTab === "blocklist"}
      <h1>Blocklist</h1>
      <p class="sub">Firewall Controller &amp; Port/IP Manager</p>

      <section class="section">
        <h2>Domain Blocking</h2>
        <p class="hint">Block websites by domain or URL (e.g. google.com, https://instagram.com)</p>
        <div class="block-form">
          <input type="text" placeholder="Enter domain or URL" bind:value={newDomain} />
          <button onclick={addDomain} disabled={!newDomain.trim()}>Block</button>
        </div>
        {#if domainMsg}
          <p class="msg">{domainMsg}</p>
        {/if}
        {#if domains.length > 0}
          <div class="block-list">
            {#each domains as d}
              <div class="block-row">
                <span class="block-domain">{d.domain}</span>
                <span class="block-date">Blocked {new Date(d.created_at).toLocaleDateString()}</span>
                <button class="icon-btn small red" onclick={() => removeDomain(d.id)}>Unblock</button>
              </div>
            {/each}
          </div>
        {:else}
          <p class="empty">No blocked domains.</p>
        {/if}
      </section>

      <section class="section">
        <h2>IP &amp; Port Blocking</h2>
        <div class="block-form ip-form">
          <input type="text" placeholder="IP address (e.g. 192.168.1.100)" bind:value={newIp} />
          <input type="number" placeholder="Port (optional)" bind:value={newIpPort} class="port-input" />
          <select bind:value={newIpProto}>
            <option value="tcp">TCP</option>
            <option value="udp">UDP</option>
            <option value="tcp">TCP+UDP</option>
          </select>
          <button onclick={addIp} disabled={!newIp.trim()}>Block</button>
        </div>
        {#if ipMsg}
          <p class="msg">{ipMsg}</p>
        {/if}
        {#if blockedIps.length > 0}
          <div class="block-list">
            {#each blockedIps as r}
              <div class="block-row">
                <span class="block-domain">{r.ip}{#if r.port}:{r.port}{/if} <span class="proto-tag">{r.protocol}</span></span>
                <span class="block-date">Blocked {new Date(r.created_at).toLocaleDateString()}</span>
                <button class="icon-btn small red" onclick={() => removeIp(r.id)}>Unblock</button>
              </div>
            {/each}
          </div>
        {:else}
          <p class="empty">No blocked IPs or ports.</p>
        {/if}
      </section>

      <section class="section">
        <h2>Firewall Status</h2>
        {#if fwStatus}
          <div class="session-card">
            <div class="session-row">
              <span class="s-label">Operating System</span>
              <span class="s-value">{fwStatus.os}</span>
            </div>
            <div class="session-row">
              <span class="s-label">Sudo Available</span>
              <span class="s-value" class:green={fwStatus.sudo_available} class:red={!fwStatus.sudo_available}>
                {fwStatus.sudo_available ? "Yes" : "No (rules stored in DB only)"}
              </span>
            </div>
            <div class="session-row">
              <span class="s-label">Domain Blocking</span>
              <span class="s-value" class:green={fwStatus.domain_blocking}>
                {fwStatus.domain_blocking ? "/etc/hosts writable" : "Unavailable"}
              </span>
            </div>
            <div class="session-row last">
              <span class="s-label">IP Blocking</span>
              <span class="s-value" class:green={fwStatus.ip_blocking_enabled} class:red={!fwStatus.ip_blocking_enabled}>
                {fwStatus.ip_blocking_enabled ? "Active" : "Not available"}
              </span>
            </div>
          </div>
        {:else}
          <p class="empty">Click to load status.</p>
        {/if}
      </section>

    {:else if activeTab === "faceid"}
      <h1>Face ID Management</h1>
      <p class="sub">Add, rename, or delete your registered faces</p>

      {#each faces as f}
        <div class="face-card">
          {#if editingId === f.id}
            <div class="face-row">
              <span class="face-icon">&#128100;</span>
              <input
                type="text"
                bind:value={editingName}
                class="edit-input"
              />
              <button class="icon-btn green" onclick={() => saveEdit(f.id)}>&#10003;</button>
              <button class="icon-btn" onclick={cancelEdit}>&#10005;</button>
            </div>
          {:else}
            <div class="face-row">
              <span class="face-icon">&#128100;</span>
              <div class="face-info">
                <span class="face-name">{f.face_name}</span>
                <span class="face-date">Added {new Date(f.created_at).toLocaleDateString()}</span>
              </div>
              <button class="icon-btn small" onclick={() => startEdit(f)}>&#9998;</button>
              <button class="icon-btn small red" onclick={() => removeFace(f.id)} disabled={faces.length <= 1} title={faces.length <= 1 ? "Cannot delete the last face" : ""}>&#128465;</button>
            </div>
          {/if}
        </div>
      {:else}
        <p class="safe empty">No faces registered yet.</p>
      {/each}

      <section class="section add-face-section">
        <button class="collapse-toggle" onclick={() => showingAdd = !showingAdd}>
          {showingAdd ? "▼" : "▶"} Add New Face
        </button>
        {#if showingAdd}
          <div class="add-face-body">
            <input
              type="text"
              placeholder="Face name (e.g. Face 2)"
              bind:value={newFaceName}
            />
            <Camera compact onCapture={(b) => newFaceBlob = b} />
            <button onclick={addFace} disabled={!newFaceBlob}>Add Face</button>
          </div>
        {/if}
      </section>

    {:else if activeTab === "network"}
      <h1>Live Network Info</h1>
      <p class="sub">Updated {netUpdated}</p>

      <div class="net-grid">
        <div class="net-card">
          <span class="net-label">IP Address</span>
          <span class="net-value">{ip || "—"}</span>
        </div>
        <div class="net-card">
          <span class="net-label">Connection</span>
          <span class="net-value">{connType.toUpperCase()}</span>
        </div>
        <div class="net-card">
          <span class="net-label">Downlink</span>
          <span class="net-value">{downlink.toFixed(1)} Mb/s</span>
        </div>
        <div class="net-card">
          <span class="net-label">Latency (RTT)</span>
          <span class="net-value">{rtt} ms</span>
        </div>
        <div class="net-card">
          <span class="net-label">Status</span>
          <span class="net-value" class:green={online} class:red={!online}>
            {online ? "Online" : "Offline"}
          </span>
        </div>
        <div class="net-card">
          <span class="net-label">User Agent</span>
          <span class="net-value small">{ua || "—"}</span>
        </div>
      </div>
    {/if}
  </main>
</div>

<style>
  .layout {
    display: flex;
    height: 100vh;
    background: #f9fafb;
  }

  .sidebar {
    width: 220px;
    background: #1e293b;
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    padding: 1.5rem 0;
    flex-shrink: 0;
  }

  .user-block {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0 1.25rem 1.5rem;
    border-bottom: 1px solid #334155;
    margin-bottom: 1rem;
  }

  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #6366f1;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
  }

  .uname {
    font-weight: 600;
    font-size: 0.95rem;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .nav {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0 0.75rem;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.6rem 0.75rem;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: #cbd5e1;
    font-size: 0.9rem;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, color 0.15s;
  }

  .nav-item:hover {
    background: #334155;
    color: #f1f5f9;
  }

  .nav-item.active {
    background: #334155;
    color: #fff;
    font-weight: 600;
  }

  .badge {
    margin-left: auto;
    background: #ef4444;
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
  }

  .spacer {
    flex: 1;
  }

  .logout-btn {
    margin: 0 0.75rem;
    padding: 0.6rem;
    border: 1px solid #475569;
    border-radius: 6px;
    background: transparent;
    color: #94a3b8;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .logout-btn:hover {
    background: #334155;
    color: #f1f5f9;
  }

  .content {
    flex: 1;
    padding: 2rem 2.5rem;
    overflow-y: auto;
  }

  .content h1 {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
  }

  .sub {
    color: #6b7280;
    margin-bottom: 1.5rem;
  }

  .hint {
    color: #6b7280;
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
  }

  .alert-banner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #fef2f2;
    border: 1px solid #fca5a5;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: #991b1b;
    font-size: 0.9rem;
  }

  .text-btn {
    background: none;
    border: none;
    color: #dc2626;
    text-decoration: underline;
    cursor: pointer;
    font-size: 0.85rem;
    margin-left: auto;
  }

  .safe {
    color: #16a34a;
    margin-top: 1rem;
  }

  .home-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 1.25rem;
  }

  .status-badge {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.4rem 0.85rem;
    border-radius: 20px;
    white-space: nowrap;
  }

  .status-badge.green {
    background: #f0fdf4;
    color: #16a34a;
    border: 1px solid #bbf7d0;
  }

  .status-badge.red {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fca5a5;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .stat-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
  }

  .stat-value {
    font-size: 1.2rem;
    font-weight: 700;
    color: #111827;
    font-variant-numeric: tabular-nums;
  }

  .stat-value.red {
    color: #dc2626;
  }

  .section {
    margin-top: 1.5rem;
  }

  .section h2 {
    font-size: 1rem;
    color: #374151;
    margin-bottom: 0.5rem;
  }

  .empty {
    padding: 1.25rem;
    color: #9ca3af;
    text-align: center;
  }

  .session-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
  }

  .session-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .session-row.last {
    border-bottom: none;
  }

  .s-label {
    font-size: 0.8rem;
    color: #6b7280;
  }

  .s-value {
    font-size: 0.85rem;
    color: #111827;
    font-weight: 500;
  }

  .s-value.green {
    color: #16a34a;
  }

  .s-value.red {
    color: #dc2626;
  }

  .s-value.small {
    font-size: 0.75rem;
    font-weight: 400;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .alert-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 1rem;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .card-header h3 {
    font-size: 1rem;
    color: #111827;
  }

  .dismiss-btn {
    padding: 0.35rem 0.85rem;
    font-size: 0.8rem;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    background: #fff;
    color: #374151;
    cursor: pointer;
  }

  .dismiss-btn:hover {
    background: #f9fafb;
  }

  .log-row {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.85rem 1.25rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .log-row:last-child {
    border-bottom: none;
  }

  .snap-row .log-detail {
    gap: 0.4rem;
  }

  .snap-img {
    max-width: 240px;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
    margin-top: 0.25rem;
  }

  .log-icon {
    font-size: 1.1rem;
    color: #dc2626;
    flex-shrink: 0;
  }

  .log-detail {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .log-type {
    font-size: 0.9rem;
    color: #111827;
  }

  .log-time {
    font-size: 0.8rem;
    color: #6b7280;
  }

  .net-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 1rem;
  }

  .net-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .net-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
  }

  .net-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #111827;
    font-variant-numeric: tabular-nums;
  }

  .net-value.small {
    font-size: 0.8rem;
    font-weight: 400;
    word-break: break-all;
    line-height: 1.3;
  }

  .net-value.green {
    color: #16a34a;
  }

  .net-value.red {
    color: #dc2626;
  }

  .face-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    margin-bottom: 0.5rem;
  }

  .face-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1.25rem;
  }

  .face-icon {
    font-size: 1.3rem;
    flex-shrink: 0;
  }

  .face-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .face-name {
    font-weight: 600;
    color: #111827;
  }

  .face-date {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .edit-input {
    flex: 1;
    padding: 0.4rem 0.6rem;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-size: 0.9rem;
  }

  .icon-btn {
    background: none;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    font-size: 0.9rem;
    color: #374151;
    line-height: 1;
    flex-shrink: 0;
  }

  .icon-btn:hover {
    background: #f3f4f6;
  }

  .icon-btn.small {
    padding: 0.3rem 0.5rem;
    font-size: 0.8rem;
  }

  .icon-btn.green {
    color: #16a34a;
    border-color: #bbf7d0;
  }

  .icon-btn.green:hover {
    background: #f0fdf4;
  }

  .icon-btn.red {
    color: #dc2626;
    border-color: #fca5a5;
  }

  .icon-btn.red:hover {
    background: #fef2f2;
  }

  .icon-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .icon-btn:disabled:hover {
    background: none;
  }

  .add-face-section {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #fff;
    overflow: hidden;
  }

  .collapse-toggle {
    width: 100%;
    padding: 0.75rem 1.25rem;
    background: none;
    border: none;
    font-size: 0.9rem;
    font-weight: 600;
    color: #374151;
    cursor: pointer;
    text-align: left;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .collapse-toggle:hover {
    background: #f9fafb;
  }

  .add-face-body {
    padding: 0 1.25rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .add-face-body input[type="text"] {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .add-face-body button {
    padding: 0.5rem;
    font-size: 0.9rem;
    border: none;
    border-radius: 6px;
    background: #4f46e5;
    color: #fff;
    cursor: pointer;
  }

  .add-face-body button:disabled {
    opacity: 0.5;
  }

  .face-card input[type="text"] {
    flex: 1;
    padding: 0.4rem 0.6rem;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    font-size: 0.9rem;
  }

  .block-form {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .block-form input[type="text"],
  .block-form input[type="number"],
  .block-form select {
    padding: 0.5rem 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .block-form input[type="text"] {
    flex: 1;
  }

  .block-form .port-input {
    width: 100px;
    flex: none;
  }

  .block-form select {
    width: 100px;
    flex: none;
  }

  .block-form button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    background: #dc2626;
    color: #fff;
    font-size: 0.9rem;
    cursor: pointer;
    flex-shrink: 0;
  }

  .block-form button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .block-list {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
  }

  .block-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 1.25rem;
    border-bottom: 1px solid #f3f4f6;
  }

  .block-row:last-child {
    border-bottom: none;
  }

  .block-domain {
    flex: 1;
    font-weight: 500;
    color: #111827;
    font-size: 0.9rem;
  }

  .block-date {
    font-size: 0.75rem;
    color: #6b7280;
    white-space: nowrap;
  }

  .proto-tag {
    display: inline-block;
    font-size: 0.65rem;
    background: #e0e7ff;
    color: #4338ca;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
    vertical-align: middle;
    margin-left: 0.25rem;
  }

  .msg {
    font-size: 0.8rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
    padding: 0.35rem 0.75rem;
    background: #f0fdf4;
    border-radius: 5px;
    display: inline-block;
  }

  .ip-form {
    flex-wrap: wrap;
  }
</style>
