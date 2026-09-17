# RingBack AI — Missed-Call Recovery for Produce Distribution

**62% of inbound business calls go unanswered. RingBack calls those buyers back in
seconds and actually gets the job done — taking wholesale produce orders,
confirming stock and today's market prices, quoting bulk pricing, tracking
deliveries, escorting angry callers to the produce manager — while the owner
watches everything happen live.**

Built for the **AssemblyAI Voice Agent Hackathon** (Sept 1–30, 2026).
Deep on the AssemblyAI stack: **Voice Agent API** (single-WebSocket speech-to-
speech agent with server-side HTTP tools), **LLM Gateway** (structured post-call
analytics on the live transcript), **Session History** (recordings + timelines),
and secure **stored agents + one-time tokens**.

---

## Why this wins

- **Real business value, not a toy.** The US fruit & vegetable wholesaling
  industry is a **$119B market** (IBISWorld, NAICS 42448, 2026) that runs on the
  phone — and it's fragmented enough that no company holds more than 5% share.
  Waitstaff-thin order desks miss calls, and one missed order call costs
  **$125–350** in immediate lost revenue.
- **The AI does real work.** The agent calls server-side tools on *our* app
  that create actual orders, price quotes, and manager-escalation tasks. Judges
  hear confirmation numbers read back out loud.
- **Deep sponsor usage.** Voice Agent API, streaming STT, LLM Gateway analytics,
  Session History — all AssemblyAI, all used meaningfully.
- **A demo anyone can click and talk to in 30 seconds.** No Twilio or signup
  needed.

---

## Quickstart (local)

```bash
git clone <your-repo-url>  # or use your copy
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
demo business (GreenRoot Produce Co., Harvest Line Foods, Coastal Fresh Market)
with its own system prompt, greeting, keyterms, and tool set.

### Demo script (what to say)

1. Open `/demo`, pick a scenario (e.g. *"Place tomorrow's wholesale order"*).
2. Click **Call back** — you are the customer. Read the on-screen opening line
   into your mic:
   > *"Hi, I missed your call — this is Chef Sofia at Bistro Verde. I need to order for tomorrow morning: 50 pounds of romaine, three cases of hass avocados, and six flats of strawberries."*
3. RingBack's agent confirms stock + today's pricing, places the order, reads
   back the confirmation number, and the **owner dashboard** on the right fills
   in live: events, order record, then summary + sentiment + action items via
   LLM Gateway.

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
   /tools/*  — real actions: check_stock, place_order,        · Session History
               get_pricing_quote, check_order, cancel_order,  · LLM Gateway
               escalate_to_human, notify_owner, …             · (analytics)
   /api/*    — call lifecycle, dashboard, token minting
   data/store.json — orders, quotes, tasks, call records
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
| `GET /api/dashboard` | aggregate stats (orders, quotes, revenue saved) |
| `GET /api/orders` `/api/quotes` `/api/tasks` | records |
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
  store.py        JSON-file store (orders, quotes, calls, dashboard)
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