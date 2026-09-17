# RingBack AI — Ready-to-Submit Package (lablab.ai · AssemblyAI Voice Agent Hackathon)

Everything you need to actually submit, in one file. Submit deadline: **Sep 30, 2026**.

---

## 1. One-pager (paste into the submission form)

**Title** — RingBack AI: Missed-Call Recovery for Produce Distribution
**Tagline** — "You missed their order call. RingBack already took it."

**Problem.** **62% of inbound business calls go unanswered** — only 37.8% reach a
live person (411 Locals 2024 study of 85 SMBs over 30 days). The US fruit &
vegetable wholesaling industry — a **$119B market** (IBISWorld NAICS 42448,
2026), so fragmented no company holds more than 5% share — runs on the phone.
When an order-desk line drops at 5:40 AM, that chef dials the other distributor.
One missed order call costs **$125–350** in immediate lost revenue; the average
small business loses **~$126K/yr** to unanswered calls.

**Solution.** RingBack pairs every distributor with a dedicated AssemblyAI voice
agent. The moment a call goes unanswered, RingBack calls the buyer back in
seconds, has a natural conversation, and **does the work** — confirms stock and
today's market prices, takes wholesale orders, quotes bulk pricing, tracks
deliveries, and calmly escorts angry callers to the produce manager. The owner
gets a live dashboard, a full transcript, AI summary/sentiment/action items, and
a link to the recorded session.

**Why AI is required.** Handling human-level conversations, real-time
transcription, tool calling mid-call, and post-call intelligence are impossible
without modern voice AI. That's the point: **AssemblyAI's entire stack is the product.**

**Market.** $119B US fruit & vegetable wholesaling (IBISWorld, 2026, +2.2% YoY).
Fragmented, phone-first, thin-staffed order desks. Beachhead: regional produce
distributors, restaurant supply, grower-direct. Pricing $49–$99/location/month.
A distributor recovering 30 lost order calls/mo at $125 each recovers
~$3,750/mo — before repeat orders.

**Demo link:** `<deployed URL>`  ·  **Code:** `<git repo>`

---

## 2. Demo video script — 4 minutes (matches lablab's winning structure)

| Time | Segment | What happens on screen |
| --- | --- | --- |
| 0:00–0:35 | **Problem** | Narration over stat cards: "62% of business calls go unanswered. The $119B produce-wholesaling industry runs on the phone — and when the order desk drops a call at 6 AM, that chef calls your competitor. Introducing RingBack." |
| 0:35–1:00 | **Product intro** | Show `/demo`, the scenario picker. "No Twilio needed — one click, and the phone rings. You ARE the missed buyer." |
| 1:00–2:30 | **Live demo** | Click **Call back**. Read Chef Sofia's line into the mic: *"I missed your call — this is Chef Sofia, I need to order tomorrow: 50 lb romaine, three cases avocados, six flats strawberries."* Agent confirms stock + prices, places the order, reads back the confirmation number. Point at the owner dashboard populating *live* — events feed, order chip, then post-call summary/sentiment/action items. |
| 2:30–3:10 | **Tech depth** | Show the WS URL + `session.update`, the server-side HTTP tools being called (`/tools/place_order`, `/tools/check_stock`), the LLM Gateway JSON result, and the AssemblyAI session record. "One WebSocket in, real wholesale orders out." |
| 3:10–4:00 | **Business + next steps** | $119B market, fragmentation, $49–99/mo pricing, roadmap: Twilio inbound, ERP/CRM sync, multi-line distributors, self-serve onboarding. Team + thank you. |

**Production tips:** Screen-record at 1080p. Use headphones. Narrate over the
live parts; don't edit away the "fail" paths — handling the bruised-strawberry
complaint (escalation scenario) is your most impressive clip. Add captions.

---

## 3. Pitch deck — 10 slides

1. **Title** — RingBack AI, tagline, AssemblyAI badge.
2. **Problem** — 62% unanswered calls + the missed-order leak in a $119B market.
3. **Solution** — miss → callback → order taken → owner informed (3-step flow).
4. **Live demo screenshot** — phone + dashboard mid-order.
5. **Tech** — Voice Agent API + HTTP tools; LLM Gateway JSON; Session History.
6. **Market** — $119B produce wholesaling (IBISWorld), phone-first & fragmented
   (<5% max share); beachhead persona: regional distributors / restaurant supply.
7. **Revenue** — $49–99/location/mo; 30 recovered calls/mo ≈ $3.7K; channel
   (produce industry events, wholesale buying groups, POS partners).
8. **Why now / moat** — AI-native, deep AssemblyAI integration, data flywheel
   (every call tunes better prompts + pricing scoring).
9. **Roadmap** — Twilio line, ERP/CRM sync, self-serve onboarding.
10. **Team + ask** — who we are, what we'd do with the prize.

---

## 4. Judging-rubric crosswalk (reverse-engineered)

- **Presentation** — script above follows lablab's 4-part video structure; 10
  slides; demo is the centerpiece.
- **Business value** — specific buyer (produce wholesalers / order desks), TAM
  figure ($119B, IBISWorld, 2026), revenue model ($49–99/mo), why-AI argument.
  Real sourced stats throughout.
- **Application of technology** — deployed clickable demo; real git commits
  across the event window; AssemblyAI used at four levels (Voice Agent API,
  HTTP tool calling, LLM Gateway analytics, Session History). Not a wrapper.
- **Originality** — missed-call recovery as an *autonomous business process*, not
  a chatbot; the live owner dashboard is the differentiator.

## 5. What's real vs simulated (be honest, it scores well)

- **Real:** the entire voice conversation, order/quote/stock/delivery/
  escalation tools, transcript, LLM Gateway analytics, session history, browser
  audio.
- **Simulated for the demo:** the *inbound* side (browser instead of a PBX) and
  the order-book entries (GR-2045, CF-1988, …). The Twilio/SIP integration is
  our roadmap item #1 — the platform supports inbound SIP out of the box.

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