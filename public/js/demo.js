/* RingBack AI — demo client.
   Streams mic audio to the AssemblyAI Voice Agent WebSocket (via a temporary
   token minted by our server), plays the agent's speech, renders the live
   transcript + tool activity, and pumps every outcome into the owner
   dashboard in real time. */

(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const state = {
    config: null,
    call: null,
    scenario: null,
    ws: null,
    audioCtx: null,
    worklet: null,
    source: null,
    stream: null,
    ready: false,
    startedAt: 0,
    aaSessionId: null,
    transcript: [],
    playQueue: [],
    currentSource: null,
    feedTimer: null,
    dashTimer: null,
    micLvlTimer: null,
    capped: false,
  };

  const WS_URL = "wss://agents.assemblyai.com/v1/ws?token=";
  const POLL_MS = 1200;
  const DASH_MS = 4000;

  // ------------------------------------------------------------------ utils
  function esc(s) {
    return (s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, opts) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const d = (data && data.detail) ? data.detail : res.statusText;
      throw new Error(typeof d === "string" ? d : JSON.stringify(d));
    }
    return data;
  }

  function base64FromBytes(bytes) {
    let s = "";
    const CH = 0x8000;
    for (let i = 0; i < bytes.length; i += CH) {
      s += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
    }
    return btoa(s);
  }

  function bytesFromBase64(b64) {
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return arr;
  }

  function fmtTime(dateStr) {
    const d = new Date(dateStr.replace(" ", "T"));
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function setStatus(text, cls) {
    const pill = $("status-pill");
    pill.textContent = text;
    pill.className = "status-pill" + (cls ? " " + cls : "");
  }

  // ------------------------------------------------------------------ boot
  async function boot() {
    try {
      state.config = await api("/api/config");
    } catch (e) {
      showOverlay("Server unreachable", "Restart `uvicorn app.main:app` and reload. " + e.message);
      return;
    }
    if (!state.config.aa_configured) {
      showOverlay("AssemblyAI key missing", "Set ASSEMBLYAI_API_KEY (and PUBLIC_BASE_URL for tools) in your .env, restart the server, and reload.");
    }
    renderScenarios();
    refreshDash();
    state.dashTimer = setInterval(refreshDash, DASH_MS);
    $("aa-status").textContent = state.config.aa_configured
      ? "AssemblyAI API: connected"
      : "AssemblyAI API: not configured";
  }

  function renderScenarios() {
    const wrap = $("scenario-list");
    wrap.innerHTML = "";
    state.config.scenarios.forEach((s, i) => {
      const biz = state.config.businesses.find((b) => b.id === s.business_id);
      const el = document.createElement("div");
      el.className = "scenario" + (i === 0 ? " sel" : "");
      el.dataset.id = s.id;
      el.innerHTML =
        '<div class="s-title"><span>' + esc(s.title) + "</span><small>" +
        esc(biz ? biz.name : "") + "</small></div><p>" + esc(s.description) + "</p>";
      el.addEventListener("click", () => selectScenario(s.id));
      wrap.appendChild(el);
    });
    const first = state.config.scenarios[0];
    state.scenario = first;
    renderBusinessCard(first);
  }

  function selectScenario(id, sync = true) {
    document.querySelectorAll(".scenario").forEach((el) => el.classList.toggle("sel", el.dataset.id === id));
    const s = state.config.scenarios.find((x) => x.id === id);
    if (s) { state.scenario = s; if (sync) renderBusinessCard(s); }
  }

  function renderBusinessCard(s) {
    const biz = state.config.businesses.find((b) => b.id === s.business_id);
    $("biz-name").textContent = biz ? biz.name + " — RingBack answering" : "—";
    $("biz-meta").textContent = biz ? biz.services.join(" · ") + " · " + (biz.tagline || "") : "";
    $("dash-business").textContent = biz ? biz.name + " · live" : "live";
  }

  // ------------------------------------------------------------------ call start
  $("btn-start").addEventListener("click", startCall);
  $("btn-end").addEventListener("click", endCall);

  async function startCall() {
    if (!state.scenario) return;
    disableStart(true);

    const s = state.scenario;
    $("caller-avatar").textContent = (s.customer_name || "?").charAt(0).toUpperCase();
    $("caller-name").textContent = s.customer_name;
    $("caller-phone").textContent = s.phone;
    clearTranscript();

    addFeed({ t: new Date().toISOString(), type: "missed", title: "Missed call detected", detail: s.phone + " tried the business line · rang 12s" });
    setStatus("ringing", "live");
    $("rings").classList.add("on");
    $("mic-hint").textContent = "RingBack dialing the caller…";

    try {
      const call = await api("/api/simulate-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: s.id, customer_name: s.customer_name, phone: s.phone }),
      });
      state.call = call;

      setTimeout(async () => {
        try {
          const answered = await api("/api/calls/" + call.id + "/answer", { method: "POST" });
          state.call = answered;
        } catch (_e) { /* ignore, still proceed */ }
        addScriptBubble("You", s.first_line);
        $("rings").classList.remove("on");
        $("mic-hint").textContent = "Connected — please speak after the agent.";
        connectVoice(call);
      }, 1500);
    } catch (e) {
      showOverlay("Could not start the simulated call", esc(e.message));
      disableStart(false);
      setStatus("idle", "");
    }
  }

  async function connectVoice(call) {
    setStatus("connecting");
    showOverlay("Connecting the voice agent…", "Minting a secure one-time AssemblyAI token");
    try {
      const t = await api("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ business_id: call.business_id }),
      });

      const biz = state.config.businesses.find((b) => b.id === call.business_id);
      if (biz && !biz.agent_ready) renderBusinessCard(state.scenario);

      state.token = t.token;
      state.ws = new WebSocket(WS_URL + encodeURIComponent(t.token));
      state.inlineSession = t.inline_session || null;
      state.usedInline = false;
      openSocket(call, t.agent_id);
      hideOverlay();
    } catch (e) {
      hideOverlay();
      showOverlay("Voice agent setup failed", esc(e.message) + " — check your AssemblyAI key and that the agent was provisioned.");
      setStatus("error");
      disableStart(false);
      endCallCleanup();
    }
  }

  function openSocket(call, agentId, useInline = false) {
    state.ws = new WebSocket(WS_URL + encodeURIComponent(state.token));
    wireWs(state.ws, call, agentId, useInline);
    state.startedAt = Date.now();
  }

  function wireWs(ws, call, agentId, useInline = false) {
    ws.onopen = () => {
      const session = useInline && state.inlineSession ? Object.assign({}, state.inlineSession) : { agent_id: agentId };
      ws.send(JSON.stringify({ type: "session.update", session }));
    };
    ws.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (_) { return; }
      handleWsMessage(m, call);
    };
    ws.onerror = () => {
      showOverlay("WebSocket error", "The AssemblyAI voice agent connection dropped. Reload and try again.");
      setStatus("error");
    };
    ws.onclose = () => { /* nothing */ };
  }

  function handleWsMessage(m, call) {
    switch (m.type) {
      case "session.ready":
        state.aaSessionId = m.session && m.session.id ? m.session.id : null;
        setStatus("talking", "live");
        $("btn-end").disabled = false;
        startMic();
        startPolling(call.id);
        break;

      case "transcript.user":
        addTranscriptTurn("user", m.text, call);
        break;
      case "transcript.agent":
        addTranscriptTurn("agent", m.text, call);
        break;

      case "reply.audio":
        if (m.audio) enqueueAudio(m.audio);
        setStatus("talking", "live");
        break;

      case "tool.call":
        setStatus("tool", "tool");
        break;

      case "interrupted":
        haltPlayback();
        break;

      case "session.error":
        const errCode = m.error && m.error.code;
        if (errCode === "agent_not_found" && state.inlineSession && !state.usedInline) {
          state.usedInline = true;
          try { if (state.ws) state.ws.close(); } catch (_e) { /* */ }
          openSocket(state.call, null, true);
          return;
        }
        showOverlay("Session error", esc((m.error && m.error.message) || JSON.stringify(m)));
        setStatus("error");
        break;

      case "session.ended":
        finishCall(call);
        break;

      default:
        break;
    }
  }

  // ------------------------------------------------------------------ transcript
  function addScriptBubble(who, text) {
    const tr = $("transcript");
    const el = document.createElement("div");
    el.className = "bubble user";
    el.innerHTML = "<div class='who'>" + esc(who) + " · on script</div>" + esc(text);
    tr.appendChild(el);
    tr.scrollTop = tr.scrollHeight;
  }

  function addTranscriptTurn(role, text, call) {
    if (!text || !text.trim()) return;
    const who = role === "user" ? "You" : "RingBack";
    state.transcript.push({ role: who, text: text.trim() });

    const tr = $("transcript");
    const empty = $("transcript-empty");
    if (empty) empty.remove();
    const last = tr.lastElementChild;
    const startsWithLast = last && last.classList.contains("bubble") &&
      last.classList.contains(role === "user" ? "user" : "agent") && text.startsWith(last.dataset.base || "");
    const el = document.createElement("div");
    el.className = "bubble " + (role === "user" ? "user" : "agent");
    el.dataset.base = text.trim().slice(0, 40);
    el.innerHTML = "<div class='who'>" + esc(who) + "</div>" + esc(text.trim());
    if (startsWithLast) { last.replaceWith(el); } else { tr.appendChild(el); }
    tr.scrollTop = tr.scrollHeight;
  }

  function clearTranscript() {
    $("transcript").innerHTML = '<div class="muted small" id="transcript-empty">Start a call to begin. Wear headphones and allow microphone access.</div>';
    state.transcript = [];
  }

  // ------------------------------------------------------------------ mic + audio
  async function startMic() {
    try {
      state.audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      await state.audioCtx.resume();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 24000 },
      });
      await state.audioCtx.audioWorklet.addModule("/pcm-processor.js");
      state.worklet = new AudioWorkletNode(state.audioCtx, "ringback-pcm");
      state.source = state.audioCtx.createMediaStreamSource(stream);
      state.source.connect(state.worklet);
      state.worklet.connect(state.audioCtx.destination);

      state.worklet.port.onmessage = (e) => {
        if (!state.ready || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
        state.ws.send(JSON.stringify({ type: "input.audio", audio: base64FromBytes(new Uint8Array(e.data.buffer)) }));
        meter(e.data);
      };
      state.ready = true;
      state.stream = stream;
      $("mic-hint").textContent = "You're live — talk naturally. RingBack can interrupt and be interrupted.";
    } catch (e) {
      $("mic-hint").textContent = "Mic unavailable: " + e.message;
      state.ready = false;
    }
  }

  function meter(pcm) {
    let sum = 0;
    for (let i = 0; i < pcm.length; i++) { const v = pcm[i] / 32768; sum += v * v; }
    const rms = Math.sqrt(sum / pcm.length);
    $("mic-lvl").textContent = Math.min(100, Math.round(rms * 400)) + "%";
  }

  function enqueueAudio(b64) {
    if (!state.audioCtx) return;
    const bytes = bytesFromBase64(b64);
    const pcm = new Int16Array(bytes.buffer, bytes.byteOffset, bytes.length >> 1);
    const buf = state.audioCtx.createBuffer(1, pcm.length, 24000);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
    state.playQueue.push(buf);
    ensurePlaying();
  }

  function ensurePlaying() {
    if (state.currentSource || !state.playQueue.length || !state.audioCtx) return;
    const node = state.audioCtx.createBufferSource();
    node.buffer = state.playQueue.shift();
    node.connect(state.audioCtx.destination);
    node.onended = () => { state.currentSource = null; ensurePlaying(); };
    state.currentSource = node;
    node.start();
  }

  function haltPlayback() {
    if (state.currentSource) {
      try { state.currentSource.stop(); } catch (_) { /* */ }
      state.currentSource = null;
    }
    state.playQueue = [];
  }

  // ------------------------------------------------------------------ feed + polling
  function startPolling(callId) {
    state.feedTimer = setInterval(() => refreshCall(callId), POLL_MS);
    refreshCall(callId);
    addFeed({ t: new Date().toISOString(), type: "connect", title: "Caller answered — voice agent live", detail: "Streaming via AssemblyAI Voice Agent API (Universal-3.5 Pro Realtime)" });
  }

  async function refreshCall(callId) {
    if (state.capped) return;
    try {
      const c = await api("/api/calls/" + callId);
      state.call = c;
      renderFeed(c);
      renderSummary(c);
    } catch (_e) { /* transient */ }
  }

  async function refreshDash() {
    try {
      const d = await api("/api/dashboard");
      $("m-orders").textContent = d.orders;
      $("m-quotes").textContent = d.quotes;
      $("m-calls").textContent = d.calls_handled;
      $("m-revenue").textContent = "$" + (d.revenue_saved || 0).toLocaleString();
    } catch (_e) { /* transient */ }
  }

  function renderFeed(c) {
    const wrap = $("feed");
    wrap.innerHTML = "";
    const items = []
      .concat((c.events || []).map((e) => ({ ...e, k: "ev" + e.t + e.title })))
      .concat((c.tool_calls || []).map((tc) => ({ t: tc.t, type: "tool", title: "Tool: " + tc.name, detail: JSON.stringify(tc.args).slice(0, 120), k: "tc" + tc.t + tc.name })));
    items.sort((a, b) => String(a.t).localeCompare(String(b.t)));
    const COLORS = { missed: "var(--warn)", callback: "var(--accent-1)", connect: "var(--good)", tool: "var(--good)", booking: "var(--good)", quote: "var(--warn)", order: "var(--accent-1)", escalation: "var(--bad)", note: "var(--muted)", complete: "var(--good)", analytics: "var(--accent-2)", context: "var(--muted)" };
    if (!items.length) { wrap.innerHTML = '<div class="muted small">No activity yet.</div>'; return; }
    items.slice(-14).forEach((it) => {
      const el = document.createElement("div");
      el.className = "feed-item";
      el.innerHTML =
        '<span class="fi-dot" style="background:' + (COLORS[it.type] || "var(--muted)") + '"></span>' +
        '<div><span class="fi-time">' + (it.t ? fmtTime(it.t) : "") + "</span>" +
        "<strong>" + esc(it.title) + "</strong><p>" + esc(it.detail || "") + "</p></div>";
      wrap.appendChild(el);
    });
    wrap.scrollTop = wrap.scrollHeight;
  }

  // ------------------------------------------------------------------ summary
  function renderSummary(c) {
    const wrap = $("summary-wrap");
    const finished = c.status === "completed" || c.status === "escalated";
    if (!finished) {
      if (c.status === "talking") {
        wrap.innerHTML = '<div class="summary-card"><h4>Awaiting results</h4><div class="skeleton" style="width:70%"></div><div class="skeleton" style="width:90%;margin-top:8px"></div></div>';
      }
      return;
    }
    if (c.summary) {
      const sent = c.sentiment || "neutral";
      const sentCls = { positive: "pos", neutral: "neu", negative: "neg" }[sent] || "neu";
      const actions = (c.action_items || []).map((a) => "<li>" + esc(a) + "</li>").join("");
      wrap.innerHTML =
        '<div class="summary-card">' +
        '<h4>Post-call intelligence · AssemblyAI LLM Gateway</h4>' +
        '<p class="small">' + esc(c.summary) + "</p>" +
        '<div class="tags">' +
        '<span class="badge">' + esc(c.intent || "call") + "</span>" +
        '<span class="sent ' + sentCls + '">&#9679; ' + esc(sent) + "</span>" +
        (c.needs_human ? '<span class="badge" style="background:rgba(248,113,113,0.12);color:var(--bad);border-color:rgba(248,113,113,0.3)">needs human</span>' : "") +
        (c.order_id ? '<span class="tool-chip">✓ order ' + esc(c.order_id) + "</span>" : "") +
        (c.quote_id ? '<span class="tool-chip">✓ quote ' + esc(c.quote_id) + "</span>" : "") +
        "</div>" +
        (actions ? "<ul>" + actions + "</ul>" : "") +
        "</div>";
      $("aa-session-link").classList.remove("hidden");
      $("aa-session-link").href = "/api/sessions/" + (c.aa_session_id || "");
    }
  }

  function addFeed(fake) {
    const wrap = $("feed");
    const first = wrap.children[0];
    const stale = first && first.textContent.includes("No activity yet");
    if (stale) wrap.innerHTML = "";
    const el = document.createElement("div");
    el.className = "feed-item";
    const COLORS = { missed: "var(--warn)", callback: "var(--accent-1)", connect: "var(--good)", escalation: "var(--bad)", order: "var(--good)", quote: "var(--warn)", note: "var(--muted)" };
    el.innerHTML = '<span class="fi-dot" style="background:' + (COLORS[fake.type] || "var(--accent-1)") + '"></span><div><span class="fi-time">' + fmtTime(fake.t) + "</span><strong>" + esc(fake.title) + "</strong>" + (fake.detail ? "<p>" + esc(fake.detail) + "</p>" : "") + "</div>";
    wrap.insertBefore(el, wrap.firstChild);
  }

  // ------------------------------------------------------------------ end call
  async function endCall() {
    disableStart(false);
    $("btn-end").disabled = true;
    if (state.ws && state.ready && state.ws.readyState === WebSocket.OPEN) {
      try { state.ws.send(JSON.stringify({ type: "session.end" })); } catch (_) { /* */ }
    } else {
      finishCall(state.call);
    }
  }

  async function finishCall(call) {
    if (!call) return;
    state.ready = false;
    $("rings").classList.remove("on");
    setStatus("completed");

    const duration = (Date.now() - state.startedAt) / 1000;
    try {
      if (state.transcript.length) {
        await api("/api/calls/" + call.id + "/transcript", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transcript: state.transcript,
            aa_session_id: state.aaSessionId || "",
            duration_s: Math.round(duration),
          }),
        });
      }
    } catch (_e) { /* */ }

    stopMedia();
    state.capped = true;
    await refreshCall(call.id);
    disableStart(false);
    $("transcript-empty") && $("transcript-empty").remove();
    addFeedValue("Call ended — transcript + analytics saved");

    // poll for the LLM Gateway summary to land
    const deadline = Date.now() + 20000;
    const t = setInterval(async () => {
      if (Date.now() > deadline) { clearInterval(t); state.capped = false; refreshDash(); return; }
      await refreshCall(call.id);
      if (state.call && state.call.summary) {
        clearInterval(t); state.capped = false; refreshDash();
      }
    }, 2500);
  }

  function addFeedValue(text) {
    const wrap = $("feed");
    const el = document.createElement("div");
    el.className = "feed-item";
    el.innerHTML = '<span class="fi-dot" style="background:var(--good)"></span><div><strong>' + esc(text) + "</strong></div>";
    wrap.insertBefore(el, wrap.firstChild);
  }

  function endCallCleanup() {
    stopMedia();
    state.ready = false;
    if (state.ws) { try { state.ws.close(); } catch (_) { /* */ } }
    $("rings").classList.remove("on");
    if (state.feedTimer) clearInterval(state.feedTimer);
    if (state.dashTimer) clearInterval(state.dashTimer);
  }

  function stopMedia() {
    if (state.stream && state.stream.getTracks) state.stream.getTracks().forEach((t) => t.stop());
    if (state.audioCtx) try { state.audioCtx.close(); } catch (_) { /* */ }
    state.source = null; state.worklet = null; state.audioCtx = null; state.stream = null;
    haltPlayback();
    if (state.ws && state.ws.readyState === WebSocket.OPEN) { try { state.ws.close(); } catch (_) { /* */ } }
  }

  // ------------------------------------------------------------------ ui helpers
  function disableStart(dis) {
    $("btn-start").disabled = dis;
    if (!dis) $("btn-end").disabled = true;
  }

  function showOverlay(title, sub) {
    $("overlay-title").textContent = title;
    $("overlay-sub").textContent = sub || "";
    $("overlay").style.display = "grid";
  }
  function hideOverlay() { $("overlay").style.display = "none"; }

  window.addEventListener("beforeunload", () => {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      try { state.ws.send(JSON.stringify({ type: "session.end" })); } catch (_) { /* */ }
    }
  });

  boot();
})();