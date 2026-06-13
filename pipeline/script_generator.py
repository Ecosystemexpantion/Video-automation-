import anthropic
import json
import re
import sys
import time
from config import ANTHROPIC_API_KEY, WHATSAPP_INVITE_LINK

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert viral short-form video script writer specializing in AI automation and money-making content for African audiences.
Your videos are 30-45 seconds long, high energy, and drive viewers to join a WhatsApp community.
Write in clear, simple English that works globally. Be specific, practical, and urgent.
Always respond with valid JSON only — no markdown, no explanation."""

SCRIPT_PROMPT = """Write a viral short-form video script (30-45 seconds) about:
"{topic}"

Target audience: People who want to use AI to earn money online.
Goal: Get them excited and compel them to join the WhatsApp group for more.

Return ONLY a JSON object with exactly these keys:
{{
  "title": "Video title (max 60 chars, punchy, no hashtags)",
  "hook": "First 3-second line — shocking, curious, or bold",
  "body": "Main content: 3 short actionable tips, each on a new line. Use numbers. Be specific.",
  "cta": "Call to action — tell them to join: {whatsapp_link}",
  "description": "Platform description for YouTube/Instagram (max 150 chars, includes WhatsApp link)",
  "hashtags": ["AI", "MakeMoneyOnline", "AIAutomation", "SideHustle", "Entrepreneur"],
  "full_script": "Complete flowing script from hook through body to CTA, as it would be spoken",
  "pexels_search": "2-3 word search term for background footage (e.g. 'artificial intelligence laptop')",
  "demo_steps": [
    {{
      "action": "goto",
      "url": "https://example.com",
      "narration": "exact words spoken at this moment"
    }},
    {{
      "action": "click",
      "description": "what to click (e.g. Sign Up button, search bar)",
      "narration": "exact words spoken at this moment"
    }},
    {{
      "action": "type",
      "text": "text to type",
      "narration": "exact words spoken at this moment"
    }},
    {{
      "action": "scroll",
      "direction": "down",
      "narration": "exact words spoken at this moment"
    }}
  ]
}}

For demo_steps: create 4-8 steps that show the actual process on real websites relevant to the topic.
For abstract topics (not tied to one website), use ChatGPT (chat.openai.com) or Google as the demo site to show the AI tool being used.
The demo must visually match what is being narrated — each step's narration = what the voiceover says during that moment."""


def generate_script(topic: str) -> dict:
    prompt = SCRIPT_PROMPT.format(topic=topic, whatsapp_link=WHATSAPP_INVITE_LINK)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            text = next(b.text for b in response.content if b.type == "text").strip()

            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            raise ValueError(f"No JSON found in response: {text[:200]}")

        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            if attempt < 2:
                wait = 2 ** attempt
                print(f"  [Haiku] Rate limit / API error, retrying in {wait}s: {e}")
                time.sleep(wait)
                continue
            raise
        except json.JSONDecodeError as e:
            if attempt < 2:
                print(f"  [Haiku] JSON parse error, retrying: {e}")
                time.sleep(1)
                continue
            raise ValueError(f"Claude returned invalid JSON after 3 attempts: {e}")

    raise RuntimeError("Script generation failed after all retries")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    topic = "How to make $500/month using ChatGPT to write content for clients"

    if dry_run:
        print(f"[DRY RUN] Would generate script for: {topic}")
        print(f"[DRY RUN] WhatsApp link: {WHATSAPP_INVITE_LINK}")
        print("[DRY RUN] Model: claude-haiku-4-5")
    else:
        print(f"Generating script for: {topic}")
        result = generate_script(topic)
        print(json.dumps(result, indent=2))
