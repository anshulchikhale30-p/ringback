# RingBack AI — Missed-Call Recovery on Autopilot

**Small businesses miss 1 in 5 inbound calls. RingBack calls those customers back
in seconds and actually gets the job done — booking appointments, capturing
quotes, checking orders, escorting unhappy callers to a human — while the owner
watches everything happen live.**

Built for the **AssemblyAI Voice Agent Hackathon** (Sept 1–30, 2026).
Deep on the AssemblyAI stack: **Voice Agent API** (single-WebSocket speech-to-
speech agent with server-side HTTP tools), **LLM Gateway** (structured post-call
analytics on the live transcript), **Session History** (recordings + timelines),
and secure **stored agents + one-time tokens**.

---

## Why this wins

- **Real business value, not a toy.** Missed-call recovery is a measured,
  painful SMB problem. Every recovered call ≈ $100–$300 of revenue.
- **The AI does real work.** The agent calls server-side tools on *our* app
  that create actual bookings, quotes, and human-escalation tasks. Judges hear
  confirmation numbers read back out loud.
- **Deep sponsor usage.** Voice Agent API, Grocery-grade streaming STT, LLM
  Gateway analytics, Session History — all AssemblyAI, all used meaningfully.
- **A demo anyone can click and talk to in 30 seconds.** No Twilio or signup
  needed.

---

## Quickstart (local)

```bash
git clone https://github.com/<you>/ringback  # or use your copy
cd ringback
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

| Variable | Why |
| --- | --- |
| `ASSEMBLYAI_API_KEY` | Your key from https://www.assemblyai.com/app |
| `PUBLIC_BASE_URL` | Public HTTPS URL of this server — AssemblyAI calls tools on it |

> `PUBLIC_BASE_URL` is required for the voice agent's **HTTP tools**. Locally,
> run `ngrok http 8000` and paste the `https://…` URL into `.env`. In
> production it's your Render/Railway/Fly URL.

Then:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 → landing, http://localhost:8000/demo → live demo.

On boot the server auto-provisions one **stored AssemblyAI voice agent** per
demo business (Bloom Dental, FixIt Plumbing, Terra Café, Summit Auto Repair)
with its own system prompt, greeting, keyterms, and tool set.

### Demo script (what to say)

1. Open `/demo`, pick a scenario (e.g. *"Book / reschedule an appointment"*).
2. Click **Call back** — you are the customer. Read the on-screen opening line
   into your mic:
   > *"Hi, I missed a call from you folks — I need to reschedule my cleaning for Thursday morning if possible."*
3. RingBack's agent books it, reads back the confirmation number, and the
   **owner dashboard** on the right fills in live: events, booking record,
   then summary + sentiment + action items via LLM Gateway.

---

## Deploy (free tier)

### Render (recommended)
1. Push this repo to GitHub.
2. Render → **New → Blueprint** → point at the repo (uses `render.yaml`).
3. In the dashboard set the `ASSEMBLYAI_API_KEY` secret.
4. If Render assigned a different URL, update `PUBLIC_BASE_URL` env var and redeploy.

### Railway / Fly.io
Railway: `railway up` with `PORT` auto-injected.
Fly: `fly launch` + `fly secrets set ASSEMBLYAI_API_KEY=… PUBLIC_BASE_URL=https://…`.

---

## Architecture

```
Browser (demo page)
   │  ① POST /api/simulate-call  ② POST /api/token (one-time token)
   │  ③ WebSocket → wss://agents.assemblyai.com/v1/ws?token=…
   ▼
┌───────────────────────────────  AssemblyAI  ───────────────────────────────┐
│  Voice Agent WebSocket (session.update with agent_id)                      │
│   · streaming STT (Universal-3.5 Pro Realtime), turn detection, barge-in   │
│   · reply.audio (24k PCM16) streamed back to the browser                   │
│   · model calls HTTP tools → POST https://you/tools/<name>?business_id=…   │
└─────────────────────────────────────────────────────────────────────────────┘
   ▼                                                            ▼
RingBack server (FastAPI)                                    AssemblyAI
   /tools/*  — real actions: book_appointment, create_quote,  · Session History
               check_order, escalate_to_human, …              · LLM Gateway
   /api/*    — call lifecycle, dashboard, token minting       · (analytics)
   data/store.json — bookings, quotes, tasks, call records
```

Key implementation notes

- **Tools are server-side HTTP tools.** Each tool URL pins `business_id` as a
  query param (the platform merges pinned query params with the model's JSON
  args). The tool resolves the *active call* for that business to log a live
  event, so the owner dashboard animates while the call is still running.
- **No API key ever touches the browser.** The server mints a one-time
  temporary token (`GET /v1/token`) with short expiry.
- **Analytics degrade gracefully.** If the LLM Gateway call fails, the call
  still completes and the transcript is saved; the summary just appears later
  or not at all.

### API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | health check (Render uses this) |
| `GET /api/config` | businesses + demo scenarios (public) |
| `POST /api/agents` | provision a NEW business's voice agent in one call |
| `GET /api/agents` | provisioning status per business |
| `POST /api/token` | mint one-time Voice Agent token |
| `POST /api/simulate-call` | create a "missed call" record |
| `POST /api/calls/{id}/answer` | mark answered / agent live |
| `POST /api/calls/{id}/transcript` | close the call, save transcript → triggers analytics |
| `GET /api/calls{/?limit}` | recent calls |
| `GET /api/dashboard` | aggregate stats (bookings, quotes, revenue saved) |
| `GET /api/bookings` `/api/quotes` `/api/tasks` | records |
| `GET /api/sessions` `…/{id}` | AssemblyAI session history + artifacts |
| `POST /tools/*` | HTTP tools the voice agent calls |

---

## Project layout

```
app/
  main.py         FastAPI app, routes, agent provisioning, analytics trigger
  assemblyai.py   thin client: agents, tokens, sessions, LLM Gateway
  tools.py        server-side HTTP tool handlers (business actions)
  demo_data.py    seed businesses, system prompts, demo scenarios
  store.py        JSON-file store (bookings, quotes, calls, dashboard)
  config.py       env-driven settings
public/
  index.html      landing page
  demo.html       live voice demo + owner dashboard
  js/demo.js      WebSocket + mic + transcript + dashboard client
  pcm-processor.js AudioWorklet (Float32 → PCM16 @ 24 kHz)
  styles.css      shared design system
render.yaml       Render Blueprint (free tier)
Dockerfile        container build
```

---

## License

Hackathon submission — MIT.