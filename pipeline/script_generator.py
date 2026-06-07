import google.generativeai as genai
import json
import re
import sys
from config import GEMINI_API_KEY, WHATSAPP_INVITE_LINK

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are a viral short-form video script writer specializing in AI automation and money-making content.
Your videos are 30-45 seconds long, high energy, and drive people to join a WhatsApp community.
Always write in clear, simple English that works for a global audience."""

SCRIPT_PROMPT = """Write a viral short-form video script (30-45 seconds) about this topic:
"{topic}"

The audience wants to learn how to use AI to make money.
Include these elements:
1. HOOK (0-3 seconds): One shocking or curious opening line that stops scrolling
2. BODY (3-40 seconds): 3 quick, specific, actionable tips or steps
3. CTA (40-45 seconds): Tell them to join the WhatsApp community for more: {whatsapp_link}

Format your response as JSON with these exact keys:
{{
  "title": "Video title (max 60 chars, no hashtags)",
  "hook": "The first 3-second line",
  "body": "The main content (3 tips, each on a new line, short sentences)",
  "cta": "Join our free WhatsApp community for more tips: {whatsapp_link}",
  "description": "YouTube/Instagram description (150 chars max)",
  "hashtags": ["AI", "MakeMoneyOnline", "AIAutomation", "SideHustle", "Entrepreneur"],
  "full_script": "Complete script from hook to CTA as one flowing text",
  "pexels_search": "2-3 word search term for background video (e.g. 'artificial intelligence')"
}}"""


def generate_script(topic: str) -> dict:
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = SCRIPT_PROMPT.format(topic=topic, whatsapp_link=WHATSAPP_INVITE_LINK)

    response = model.generate_content(
        [SYSTEM_PROMPT, prompt],
        generation_config=genai.GenerationConfig(temperature=0.8)
    )

    text = response.text.strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())

    raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    topic = "How to make $500/month using ChatGPT to write content for clients"

    if dry_run:
        print(f"[DRY RUN] Would generate script for topic: {topic}")
        print(f"[DRY RUN] WhatsApp link: {WHATSAPP_INVITE_LINK}")
    else:
        result = generate_script(topic)
        print(json.dumps(result, indent=2))
