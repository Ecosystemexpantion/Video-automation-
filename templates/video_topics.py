TOPICS = [
    "How to make $500/month using ChatGPT to write content for clients",
    "The AI automation tool that freelancers are using to 10x their income",
    "5 ways to use AI to start a business with zero capital",
    "How to build a passive income chatbot using free AI tools",
    "Make money reselling AI-generated content — step by step",
    "Top 3 AI tools that replace a full-time employee in your business",
    "How I automated my entire social media with free AI tools",
    "Build an AI-powered email list that sells for you 24/7",
    "Use ChatGPT to write and sell digital products online",
    "The AI side hustle making people $1000/week in 2025",
    "How to use AI to create and sell online courses fast",
    "Make money as an AI automation consultant — no coding needed",
    "Free AI tools that generate images for your business",
    "How to use AI to run a faceless YouTube channel profitably",
    "Automate your WhatsApp business replies with free AI",
    "The AI business model that works even while you sleep",
    "How to use Gemini AI to write proposals and win clients",
    "Turn AI into your personal money-making assistant",
    "3 AI automation businesses you can start this weekend",
    "How to use AI to generate leads for any business for free",
    "AI tools that will save you 10 hours every week",
    "How to sell AI services without being a tech expert",
    "Use AI to start a dropshipping business in 24 hours",
    "The AI-powered affiliate marketing strategy that actually works",
    "How businesses in Africa are using AI to make more money",
    "Free AI tools vs paid — which ones actually make you money",
    "How to use AI to write a high-converting sales page in 10 minutes",
    "Start an AI automation agency with zero experience",
    "Use AI to run your business while traveling",
    "How to make money teaching others to use AI tools",
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
