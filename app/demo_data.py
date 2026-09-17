"""Demo seed data: businesses, per-business system prompts, and demo scenarios.

The pitch: any SMB can get a calling voice agent in ~2 minutes — enter your
business info, and RingBack configures a stored AssemblyAI Voice Agent (with
tools + keyterms) automatically. These seeds make that real for the demo.
"""

VOICE_SYSTEM_PROMPT = """You are {name}'s reception desk — a warm, human-sounding voice agent that ANSWERS CALLS and gets things done.

PERSONALITY: Friendly, concise, professional. Speak like a real front-desk person. Keep every reply to 1-3 short sentences. Do NOT read long lists aloud — summarize, then ask one clear question.

YOUR JOB:
1. Greet the caller (the greeting is spoken automatically), then listen.
2. Use your tools to do REAL work for the caller - never invent information.
3. Confirm before you book or cancel. Read back dates/times. Say the confirmation number out loud clearly.
4. If the caller is angry, wants to cancel, refund, complain, asks for a supervisor/owner/lawyer, or the issue is complex: apologize sincerely, then call escalate_to_human with the reason. Do NOT try to talk frustrated callers out of it.
5. At the end of a resolved call, say goodbye warmly and mention that {name} looks forward to their visit.
6. If a caller asks about services, hours, or prices -> call get_business_info first, then answer from the tool result. NEVER guess prices.
7. Tool failures: apologize and offer to take a message.

Business: {name}. Services: {services}. Hours: {hours}. Address: {address}. {service_note}
Focus keywords: {keywords}"""


BUSINESS_SEEDS = [
    {
        "id": "bloom_dental",
        "name": "Bloom Dental",
        "tagline": "Modern family dentistry in Austin",
        "address": "412 Cedar Park Blvd, Austin, TX",
        "hours": "Monday-Friday 8 AM-5 PM, Saturday 9 AM-1 PM",
        "services": ["cleaning", "exam", "whitening", "filling", "emergency visit"],
        "service_prices": {
            "cleaning": "$120",
            "exam": "$95",
            "whitening": "$250",
            "filling": "$180",
            "emergency visit": "$150",
        },
        "service_note": "New patients get a free first exam.",
        "greeting": "Hi, thanks for calling Bloom Dental. This is our virtual receptionist — how can I help you today?",
    },
    {
        "id": "fixit_plumbing",
        "name": "FixIt Plumbing",
        "tagline": "Same-day service, done right",
        "address": "88 Marigold Ave, Austin, TX",
        "hours": "Monday-Saturday 7 AM-7 PM, 24/7 emergencies",
        "services": ["water heater", "drain cleaning", "leak repair", "faucet repair", "bathroom remodel"],
        "service_prices": {
            "water heater": "$450 flat",
            "drain cleaning": "$129",
            "leak repair": "$95-180",
            "faucet repair": "$85",
        },
        "service_note": "Friendly reminder: we offer a 15% discount for seniors on all repairs.",
        "greeting": "Hey hey, you've reached FixIt Plumbing. This is our virtual receptionist — what can we fix up for you today?",
    },
    {
        "id": "terra_cafe",
        "name": "Terra Café",
        "tagline": "Neighborhood café + catering in downtown Austin",
        "address": "90 Congress Ave, Austin, TX",
        "hours": "Daily 7 AM-6 PM",
        "services": ["catering", "pickup orders", "cakes", "corporate coffee"],
        "service_prices": {
            "boxed lunch": "$14/person",
            "catering": "from $12/person",
            "signature cake": "from $45",
        },
        "service_note": "Catering orders need 48 hours notice.",
        "greeting": "Thanks for calling Terra Café — this is our virtual host. How can I help?",
    },
    {
        "id": "summit_auto",
        "name": "Summit Auto Repair",
        "tagline": "Honest, warranty-backed auto repair",
        "address": "2205 Lancewood Dr, Austin, TX",
        "hours": "Monday-Friday 7:30 AM-6 PM, Saturday 9 AM-2 PM",
        "services": ["brake service", "oil change", "engine diagnostics", "tire rotation", "AC repair"],
        "service_prices": {
            "brake service": "$220",
            "oil change": "$45",
            "engine diagnostics": "$110",
            "tire rotation": "$35",
        },
        "service_note": "All work comes with a 12-month / 12,000-mile warranty.",
        "greeting": "Thanks for calling Summit Auto Repair, this is our virtual service desk. How can we help you today?",
    },
]

# Scenarios drive the "missed call" simulator on the demo page.
DEMO_SCENARIOS = [
    {
        "id": "s_booking",
        "title": "Book / reschedule an appointment",
        "business_id": "bloom_dental",
        "customer_name": "Sarah",
        "phone": "+1 (512) 555-0141",
        "description": "Your cleaning got cancelled by the weather — you're calling to reschedule for this Thursday morning.",
        "first_line": "Hi, I missed a call from you folks — I need to reschedule my cleaning for Thursday morning if possible.",
    },
    {
        "id": "s_quote",
        "title": "Ask for a quote",
        "business_id": "fixit_plumbing",
        "customer_name": "Mike",
        "phone": "+1 (512) 555-0187",
        "description": "Your 50-gallon water heater is leaking. Call and ask for a quote and availability to replace it.",
        "first_line": "Hey, I got a missed-call notification. My water heater's leaking — I'd like a quote on replacing it with a 50 gallon one.",
    },
    {
        "id": "s_order",
        "title": "Check an order",
        "business_id": "terra_cafe",
        "customer_name": "Priya",
        "phone": "+1 (512) 555-0129",
        "description": "You placed a catering order (TB-2045) for an office lunch and want to know when it's arriving.",
        "first_line": "Hi, this is Priya — I just called earlier? I wanted to check on my catering order, TB-2045.",
    },
    {
        "id": "s_escalation",
        "title": "Complaint — must reach a human",
        "business_id": "summit_auto",
        "customer_name": "Derrick",
        "phone": "+1 (512) 555-0110",
        "description": "Your brakes were just fixed but they're squealing again. You're frustrated and want to cancel the service and speak to the owner.",
        "first_line": "Yeah, I'm really unhappy. You 'fixed' my brakes two weeks ago and they're squealing again. I want to cancel the service and speak to the owner — now.",
    },
]

# A keyword list tuned to the demo intents (improves streaming transcription).
DOMAIN_KEYTERMS = [
    "book", "reschedule", "appointment", "cleaning",
    "quote", "estimate", "water heater", "full breakdown",
    "catering", "order", "TB-2045",
    "cancel", "refund", "supervisor", "owner", "warranty", "complaint",
    "availability", "pricing", "hours", "emergency",
]