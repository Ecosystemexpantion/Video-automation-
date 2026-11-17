#!/usr/bin/env python3
"""Claude writes a shot-by-shot screenplay for a short animated drama. Usage: write_script.py <brief> <out.json>"""
import json, re, sys, time
import anthropic

SCHEMA = r"""Return ONE JSON object, no markdown:
{
  "title": "...",
  "style": "one sentence art style used for EVERY image, e.g. 'high-end 3D animated feature film style, Pixar-like, soft cinematic lighting'",
  "characters": [
    {"id": "mango", "name": "Mango", "voice": "male_warm | male_deep | male_young | female_warm | female_bright | female_british | male_british",
     "look": "very specific visual description: fruit type, colour, size, eyes, eyebrows, a clearly visible mouth with lips, arms/legs, clothing or accessory. Same words reused for every shot."}
  ],
  "locations": [
    {"id": "kitchen", "description": "detailed environment description, lighting, time of day"}
  ],
  "shots": [
    {"id": 1, "type": "establish | dialogue | action", "location": "kitchen",
     "left": "character id or null", "right": "character id or null",
     "framing": "wide | medium two-shot | close-up",
     "visual": "what the frame shows: poses, expressions, props",
     "motion": "for establish/action: what moves during the 3 seconds, e.g. 'Mango shoves Pineapple, Pineapple stumbles back'",
     "lines": [{"speaker": "left | right", "text": "...", "emotion": 0.3}]}
  ]
}
Rules:
- 2 or 3 characters, all anthropomorphic fruits with expressive faces and clearly visible mouths (needed for lip sync).
- Total runtime about 120 seconds. Dialogue is spoken at a natural pace (~2.6 words per second); establish and action shots last 3.2 seconds each.
- 22 to 30 shots: open with 1-2 establish shots, build the conflict through dialogue, escalate into a SMALL comedic fight of 4-6 action shots (pushing, a slap with a leaf, rolling, food thrown, no gore), then a resolution in dialogue, end with 1 establish/action shot.
- Dialogue shots have 1 to 3 lines and 4 to 12 seconds of speech. In a two-shot both characters are in frame ("left" and "right"); a close-up has one character as "left" and right null, and only that character speaks.
- Every line's speaker must be a character actually in that shot. Action shots have no lines.
- Use 1 or 2 locations only, so the environment stays consistent.
- emotion: 0.3 calm, 0.6 animated, 0.9 shouting."""


def main():
    brief, out = sys.argv[1], sys.argv[2]
    client = anthropic.Anthropic()
    for attempt in range(3):
        msg = client.messages.create(
            model="claude-opus-4-8", max_tokens=16000, thinking={"type": "adaptive"},
            system="You are an award-winning animation screenwriter and director. You write tight, funny, emotional short films that an automated renderer will produce shot by shot.",
            messages=[{"role": "user", "content": f"Write this short film:\n{brief}\n\n{SCHEMA}"}],
        )
        if msg.stop_reason == "refusal":
            sys.exit("Claude declined the brief")
        text = "".join(b.text for b in msg.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            sp = json.loads(m.group())
            chars = {c["id"] for c in sp["characters"]}
            for s in sp["shots"]:
                for line in s.get("lines") or []:
                    assert s.get(line["speaker"]) in chars, f"shot {s['id']}: speaker not in frame"
            json.dump(sp, open(out, "w"), indent=1)
            words = sum(len(l["text"].split()) for s in sp["shots"] for l in s.get("lines") or [])
            silent = sum(1 for s in sp["shots"] if not s.get("lines"))
            print(f"{sp['title']}: {len(sp['shots'])} shots, ~{words/2.6 + silent*3.2:.0f}s")
            return
        except Exception as e:
            print("retrying:", e)
            time.sleep(3)
    sys.exit("Could not get a valid screenplay")


if __name__ == "__main__":
    main()
