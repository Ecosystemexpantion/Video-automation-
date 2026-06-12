TOPICS = [
    # Technical tutorials
    "How to set up a Telegram bot in under 10 minutes — full walkthrough",
    "Building your first digital product on Selar: step-by-step guide",
    "How to deploy a Next.js site on GitHub Pages for free",
    "Setting up Supabase for your first web project — beginner guide",
    "How to connect a Telegram bot to Supabase: a practical tutorial",
    "Building an automated WhatsApp reply system — how it actually works",
    "How to use Claude AI to write sales copy — with real examples",
    "GitHub Actions explained: how to automate tasks without a server",
    "How to create and host a digital product funnel using free tools",
    "Step-by-step: building a lead capture bot with no coding experience",

    # EEM26 methodology / AAM / SRE systems
    "The 4-Day Amara Onboarding Bot — how it works (full walkthrough)",
    "What is the AAM system and how does it help digital creators?",
    "How the SRE framework can help you structure your online business",
    "Breaking down the EEM26 curriculum: what students actually learn",
    "How automated onboarding can help you serve more students consistently",

    # Student case studies (educational framing)
    "How one student built their first digital funnel in 4 days — case study",
    "What I learned watching 30 students go through their first product launch",
    "Common mistakes new digital creators make (and how to avoid them)",
    "How a student with no tech background set up their first Telegram bot",
    "What worked and what didn't: lessons from running an online cohort",

    # Mindset / business building
    "Why learning to automate one task can free up hours in your week",
    "The difference between building a system and just staying busy",
    "How to think about digital products as a long-term skill investment",
    "Why documentation is the most underrated skill in digital business",
    "How to test an idea before building the full product — practical steps",

    # Honest effort / process-focused
    "I spent 6 months building this onboarding system — here is how it works",
    "What building a real automation workflow actually looks like day-to-day",
    "How to go from idea to first paying customer: a realistic timeline",
    "The tools I use to run a digital education business — honest review",
    "Why most automation projects fail in month two (and how to avoid it)",
]

PEXELS_KEYWORDS_MAP = {
    "ChatGPT": ["artificial intelligence", "computer technology", "typing laptop"],
    "passive income": ["money", "financial freedom", "business success"],
    "automation": ["robot technology", "automation", "digital workflow"],
    "freelancer": ["freelancer working", "remote work", "laptop coffee"],
    "business": ["business success", "entrepreneur", "startup office"],
    "social media": ["social media", "phone scrolling", "content creation"],
    "YouTube": ["youtube creator", "video content", "filming studio"],
    "WhatsApp": ["messaging app", "smartphone communication", "mobile business"],
    "default": ["technology", "artificial intelligence", "digital future"],
}


def get_pexels_keywords(topic: str) -> list[str]:
    for keyword, terms in PEXELS_KEYWORDS_MAP.items():
        if keyword.lower() in topic.lower():
            return terms
    return PEXELS_KEYWORDS_MAP["default"]
