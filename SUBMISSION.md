# RingBack AI — Ready-to-Submit Package (lablab.ai · AssemblyAI Voice Agent Hackathon)

Everything you need to actually submit, in one file. Submit deadline: **Sep 30, 2026**.

---

## 1. One-pager (paste into the submission form)

**Title** — RingBack AI: Missed-Call Recovery on Autopilot
**Tagline** — "The fastest path to a working voice agent: it calls your missed callers back and does the work."

**Problem.** Small businesses miss ~1 in 5 inbound calls. Every missed call is a
customer who calls a competitor next — an average of **$125+ of revenue per
call**, with zero trace of who called or why.

**Solution.** RingBack pairs every SMB with a dedicated AssemblyAI voice agent.
The moment a call goes unanswered, RingBack calls the customer back in seconds,
has a natural conversation, and **does the work** — books appointments, captures
quote requests, checks order status, cancels/reschedules, and calmly escorts
angry callers to a human. The owner gets a live dashboard, a full transcript,
AI summary/sentiment/action items, and link to the recorded session.

**Why AI is required.** Handling human-level conversations, real-time
transcription, tool calling mid-call, and post-call intelligence are impossible
without modern voice AI. That's the point: **AssemblyAI's entire stack is the product.**

**Market.** ~33M US SMBs; ~15M are appointment/job-dependent and miss calls
daily. Pricing $49–$99/location/month. A location recovering 30 lost calls/mo
at $125 each recovers ~$3,750/mo. First integrations: telehealth, salons,
home services, restaurants.

**Demo link:** `<deployed URL>`  ·  **Code:** `<git repo>`

---

## 2. Demo video script — 4 minutes (matches lablab's winning structure)

| Time | Segment | What happens on screen |
| --- | --- | --- |
| 0:00–0:35 | **Problem** | Narration over dashboard stat cards: "Small businesses miss 1 in 5 calls. Each one is revenue walking out the door — with no record of who called or why. Introducing RingBack." |
| 0:35–1:00 | **Product intro** | Show `/demo`, the scenario picker. "No Twilio needed — one click, and the phone rings. You ARE the missed caller." |
| 1:00–2:30 | **Live demo** | Click **Call back**. Read Sarah's line into the mic: *"I missed a call from you folks — I need to reschedule my cleaning for Thursday morning."* Agent books it, reads back the confirmation number. Point at the owner dashboard populating *live* — events feed, booking chip, then post-call summary/sentiment/action items. |
| 2:30–3:10 | **Tech depth** | Show the WS URL + `session.update`, then the server-side HTTP tools being called (`/tools/book_appointment`), the LLM Gateway JSON result, and the AssemblyAI session record. "One WebSocket in, real business actions out." |
| 3:10–4:00 | **Business + next steps** | TAM, $49–99/mo pricing, roadmap: Twilio inbound, Dust/CRM sync, multi-line SMBs, self-serve onboarding. Team + thank you. |

**Production tips:** Screen-record at 1080p. Use headphones. Narrate over the
live parts; don't edit away the "fail" paths — handling an angry caller
(escalation scenario) is your most impressive clip. Add captions.

---

## 3. Pitch deck — 10 slides

1. **Title** — RingBack AI, tagline, AssemblyAI badge.
2. **Problem** — the missed-call stat + competitor walk-away loop.
3. **Solution** — miss → callback → work done → owner informed (3-step flow).
4. **Live demo screenshot** — phone + dashboard mid-book.
5. **Tech** — Voice Agent API + HTTP tools; LLM Gateway JSON; Session History.
6. **Market** — TAM 33M US SMBs; beachhead persona: solo/service businesses.
7. **Revenue** — $49–99/location/mo; unit economics; channel (merchant groups, POS partners).
8. **Why now / moat** — AI-native, deep AssemblyAI integration, data flywheel (every call trains better prompts + scoring).
9. **Roadmap** — Twilio line, Zapier/CRM, self-serve onboarding.
10. **Team + ask** — who we are, what we'd do with the prize.

---

## 4. Judging-rubric crosswalk (reverse-engineered)

- **Presentation** — script above follows lablab's 4-part video structure; 10
  slides; demo is the centerpiece.
- **Business value** — specific buyer (appointment-based SMBs), TAM figure
  (33M SMBs), revenue model ($49–99/mo), why-AI argument. All in the one-pager.
- **Application of technology** — deployed clickable demo; real git commits
  across the event window; AssemblyAI used at four levels (Voice Agent API,
  HTTP tool calling, LLM Gateway analytics, Session History). Not a wrapper.
- **Originality** — missed-call recovery as an *autonomous business process*, not
  a chatbot; the live owner dashboard is the differentiator.

## 5. What's real vs simulated (be honest, it scores well)

- **Real:** the entire voice conversation, booking/quote/order/escalation
  tools, transcript, LLM Gateway analytics, session history, browser audio.
- **Simulated for the demo:** the *inbound* side (browser instead of a PBX) and
  fake order IDs. The Twilio/SIP integration is our roadmap item #1 — the
  platform supports inbound SIP out of the box.

## 6. Submission checklist

- [ ] Deployed URL live on Render/Railway/Fly (`/demo` reachable, HTTPS)
- [ ] `ASSEMBLYAI_API_KEY` secret set server-side (not in repo)
- [ ] `PUBLIC_BASE_URL` == deployed domain
- [ ] 4-min demo video recorded + uploaded
- [ ] 10-slide deck (PDF) uploaded
- [ ] One-pager text in submission form
- [ ] GitHub repo public, commits spread across Sep 1–30
- [ ] Registered/enrolled on lablab + all team members enrolled
- [ ] Tested on a fresh browser (headphones, mic permission, 2 scenarios)