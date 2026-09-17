"""Demo seed data: businesses, per-business system prompts, and demo scenarios.

The pitch: any SMB can get a calling voice agent in ~2 minutes — enter your
business info, and RingBack configures a stored AssemblyAI Voice Agent (with
tools + keyterms) automatically. These seeds make that real for the demo.

Demo persona: FRESH PRODUCE DISTRIBUTION / wholesale order desks. Missed-call
recovery is worth ~$126K/yr per SMB, and a $119B US wholesaling industry
(a highly fragmented one — no player holds more than 5% share) runs on the
phone. That's the story.
"""

VOICE_SYSTEM_PROMPT = """You are {name}'s ORDER DESK — a sharp, human-sounding voice agent that ANSWERS CALLS and takes wholesale produce orders.

PERSONALITY: Brisk, friendly, professional — like a veteran distributor rep who knows their product. Keep every reply to 1-3 short sentences. Do NOT read long lists aloud — summarize, then ask one clear question.

YOUR JOB:
1. Greet the caller (the greeting is spoken automatically), then listen.
2. Use your tools to do REAL work - never invent prices, stock, or delivery info. Never guess availability.
3. Confirm before you place or cancel an order. Read back items, quantities (pounds/cases/flats), and delivery day. Say the confirmation number out loud clearly.
4. If the caller has a damaged or short delivery, wants credit/refund, or asks for a supervisor/produce manager/owner: sympathize briefly, then call escalate_to_human with the reason. Do NOT try to talk frustrated callers out of it.
5. At the end of a resolved call, say goodbye warmly and confirm their delivery window for {name}.
6. If a caller asks about catalog, prices, or delivery schedule -> call get_business_info first, then answer from the tool result. NEVER guess prices.
7. Tool failures: apologize and offer to take a message.

Business: {name}. Catalog & hours: {services}. {hours} @ {address}. {service_note}
Focus keywords: {keywords}"""


BUSINESS_SEEDS = [
    {
        "id": "greenroot",
        "name": "GreenRoot Produce Co.",
        "tagline": "Wholesale fresh produce for restaurants & caterers",
        "address": "Riverside Terminal Market, Bays 12-18, Austin, TX",
        "hours": "Order desk Mon-Sat 4 AM-2 PM; orders in by 2 PM deliver next morning",
        "services": [
            "romaine", "heirloom tomatoes", "hass avocados", "strawberries",
            "cucumbers", "red onions", "mixed greens", "cantaloupe",
        ],
        "service_prices": {
            "romaine": "$34/case (24 heads)",
            "heirloom tomatoes": "$28/box (25 lb)",
            "hass avocados": "$42/case (48 count)",
            "strawberries": "$16/flat (12 pints)",
            "mixed greens": "$26/tote (10 lb)",
        },
        "service_note": "Standing restaurant accounts get case pricing off the weekly sheet.",
        "greeting": "Thanks for calling GreenRoot Produce — this is our order desk. What are we pulling for you this morning?",
    },
    {
        "id": "harvest_line",
        "name": "Harvest Line Foods",
        "tagline": "Organic & specialty wholesale, grower-direct",
        "address": "104 Dripping Springs Rd, Austin, TX",
        "hours": "Order desk Mon-Fri 5 AM-3 PM; next-morning drops citywide",
        "services": [
            "organic kale", "baby spinach", "blueberries", "heirloom tomatoes",
            "organic carrots", "fennel", "figs", "microgreens",
        ],
        "service_prices": {
            "organic kale": "$22/case (12 bunches)",
            "baby spinach": "$28/tote (10 lb)",
            "blueberries": "$38/case (8 pints)",
            "heirloom tomatoes": "$32/box (20 lb)",
            "microgreens": "$14/tray (4 oz packs)",
        },
        "service_note": "Wholesale pricing on all orders over $300.",
        "greeting": "You've reached Harvest Line Foods — our order desk is live. What are you looking to stock today?",
    },
    {
        "id": "coastal_fresh",
        "name": "Coastal Fresh Market",
        "tagline": "Daily drops for cafes, delis & small grocers",
        "address": "31 Barton Creek Sq, Austin, TX",
        "hours": "Order desk Sun-Fri 4 AM-1 PM; same-week delivery slots",
        "services": [
            "green beans", "navel oranges", "lemons", "bell peppers",
            "grape tomatoes", "bananas", "red cabbage", "dill",
        ],
        "service_prices": {
            "green beans": "$38/case (20 lb)",
            "navel oranges": "$30/box (48 count)",
            "lemons": "$33/box (48 count)",
            "bell peppers": "$29/case (25 lb)",
        },
        "service_note": "Case discounts start at 10 units.",
        "greeting": "Thanks for calling Coastal Fresh Market — our order line's open. What can we add to your delivery?",
    },
]

# Scenarios drive the "missed call" simulator on the demo page.
DEMO_SCENARIOS = [
    {
        "id": "s_order",
        "title": "Place tomorrow's wholesale order",
        "business_id": "greenroot",
        "customer_name": "Chef Sofia",
        "phone": "+1 (512) 555-0147",
        "description": "You run the kitchen at a downtown bistro. You missed GreenRoot's nightly call — now place tomorrow's order: 50 lb romaine, 3 cases hass avocados, 6 flats strawberries.",
        "first_line": "Hi, I missed your call — this is Chef Sofia at Bistro Verde. I need to order for tomorrow morning: 50 pounds of romaine, three cases of hass avocados, and six flats of strawberries.",
    },
    {
        "id": "s_status",
        "title": "Track a delivery on the truck",
        "business_id": "coastal_fresh",
        "customer_name": "Danny",
        "phone": "+1 (512) 555-0133",
        "description": "Your café's order CF-1988 was supposed to drop at 6 AM. Check if it's still on the truck or out for delivery.",
        "first_line": "Hey, this is Danny from the Red Door Café — I got your missed-call ping. I'm checking on order CF-1988, the one that was supposed to drop at six.",
    },
    {
        "id": "s_quote",
        "title": "Get a bulk wholesale quote",
        "business_id": "harvest_line",
        "customer_name": "Marcus",
        "phone": "+1 (512) 555-0402",
        "description": "Your 6-location group wants to standardize on organic produce. Ask for a wholesale quote on heirloom tomatoes + blueberries at weekly volume.",
        "first_line": "Yeah hi — Marcus Bell, FP Hospitality. I missed your call. We run six kitchens and we want a wholesale quote on heirloom tomatoes and blueberries, weekly volume.",
    },
    {
        "id": "s_escalation",
        "title": "Damaged delivery — need a credit",
        "business_id": "greenroot",
        "customer_name": "Rosa",
        "phone": "+1 (512) 555-0198",
        "description": "This morning's crate of strawberries arrived bruised and half the avocados are rotten. You want a credit and to speak to the produce manager.",
        "first_line": "This is Rosa from Casa Luna — I need to talk to someone. The strawberry crate you dropped was bruised and half the avocados are rotten. I want a credit and I need to speak to the produce manager.",
    },
]

# A keyword list tuned to the demo intents (improves streaming transcription).
DOMAIN_KEYTERMS = [
    "order", "orders", "delivery", "drop", "truck", "morning",
    "romaine", "avocados", "strawberries", "blueberries", "tomatoes",
    "cases", "crates", "flats", "pounds", "lb", "cases",
    "wholesale", "quote", "pricing", "volume", "account",
    "damaged", "bruised", "rotten", "short", "credit", "refund", "manager",
    "GR-", "CF-", "HL-", "cancel",
    "availability", "catalog", "hours", "delivery window",
]