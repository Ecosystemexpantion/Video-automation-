"""
Turns a reference analysis (or a plain topic) into a shot-by-shot blueprint
using Claude. The blueprint drives voice, footage and captions in render.py.
"""

import json
import os
import re
import time

import anthropic

MODEL = "claude-opus-4-8"

SYSTEM = """You are a senior short-form video director. You design vertical videos (Shorts, Reels, TikTok) as precise shot-by-shot blueprints that an automated renderer will follow exactly.

The renderer works like this: each scene's narration is spoken by a voice-over, a stock-footage clip found with the scene's visual_query plays for exactly as long as that narration lasts, and captions of the narration appear in sync. So pacing is controlled by narration length: a short line makes a fast cut, a long line makes a slow scene.

Respond with one valid JSON object only. No markdown fences, no commentary."""

SCHEMA = """Return exactly this JSON shape:
{
  "title": "max 60 characters, no hashtags",
  "topic": "one line: what this video is about",
  "style_analysis": ["4-7 short bullets describing the style you are following: hook type, pacing, visuals, captions, tone"],
  "hook": "the opening line",
  "scenes": [
    {
      "narration": "what the voice says in this scene (natural spoken English, 4-25 words)",
      "visual_query": "2-4 word stock footage search for what is on screen, concrete and filmable (e.g. 'woman typing laptop', 'city night traffic')",
      "on_screen_text": "optional short headline shown at the top during this scene, or empty string"
    }
  ],
  "caption_style": {
    "color": "#RRGGBB highlight colour for captions",
    "uppercase": true,
    "position": "top | center | bottom",
    "words_per_caption": 3
  },
  "description": "platform description, max 150 characters",
  "hashtags": ["5 to 8 tags without the # sign"]
}

Rules:
- 6 to 14 scenes. Total narration 70 to 130 words unless the reference is clearly shorter or longer.
- The first scene is the hook and must be short and arresting.
- visual_query must describe real-world footage a stock library would have. Never abstract ideas, logos, brand names or text.
- Write original wording. Never copy the reference's sentences."""


def _client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _ask(content) -> dict:
    last_error = None
    for attempt in range(3):
        try:
            response = _client().messages.create(
                model=MODEL,
                max_tokens=8000,
                thinking={"type": "adaptive"},
                system=SYSTEM,
                messages=[{"role": "user", "content": content}],
            )
            if response.stop_reason == "refusal":
                raise RuntimeError("Claude declined to work with this video")
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON in response: {text[:200]}")
            return _validate(json.loads(match.group()))
        except (anthropic.RateLimitError, anthropic.APIConnectionError,
                anthropic.InternalServerError, ValueError) as e:
            last_error = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Could not get a valid blueprint from Claude: {last_error}")


def _validate(bp: dict) -> dict:
    scenes = [
        s for s in bp.get("scenes", [])
        if isinstance(s, dict) and str(s.get("narration", "")).strip()
    ]
    if len(scenes) < 2:
        raise ValueError("Blueprint has fewer than 2 usable scenes")
    for s in scenes:
        s["narration"] = str(s["narration"]).strip()
        s["visual_query"] = str(s.get("visual_query") or "technology").strip()
        s["on_screen_text"] = str(s.get("on_screen_text") or "").strip()
    bp["scenes"] = scenes

    style = bp.get("caption_style") or {}
    color = str(style.get("color") or "#FFDE21")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = "#FFDE21"
    position = style.get("position")
    if position not in ("top", "center", "bottom"):
        position = "bottom"
    try:
        words = min(6, max(1, int(style.get("words_per_caption") or 3)))
    except (TypeError, ValueError):
        words = 3
    bp["caption_style"] = {
        "color": color,
        "uppercase": bool(style.get("uppercase", True)),
        "position": position,
        "words_per_caption": words,
    }

    bp["title"] = str(bp.get("title") or "Untitled video")[:80]
    bp["topic"] = str(bp.get("topic") or bp["title"])
    bp["style_analysis"] = [str(x) for x in (bp.get("style_analysis") or [])][:8]
    bp["hook"] = str(bp.get("hook") or scenes[0]["narration"])
    bp["description"] = str(bp.get("description") or bp["title"])[:300]
    bp["hashtags"] = [str(h).lstrip("#") for h in (bp.get("hashtags") or [])][:10]
    return bp


def _direction(notes: str) -> str:
    notes = (notes or "").strip()
    if notes:
        return f"\nThe creator's instructions for the new video (follow them): {notes}\n"
    return ""


def from_reference(analysis: dict, notes: str = "") -> dict:
    """Blueprint that recreates a reference video's style and structure."""
    bounds = analysis["scene_starts"] + [analysis["duration"]]
    cuts = ", ".join(
        f"{bounds[i]:.1f}-{bounds[i + 1]:.1f}s" for i in range(len(analysis["scene_starts"]))
    )
    transcript = "\n".join(
        f"[{s['start']:.1f}-{s['end']:.1f}s] {s['text']}" for s in analysis["transcript"]
    ) or "(no speech detected — the reference relies on visuals, music or on-screen text)"

    content = []
    for frame in analysis["frames"]:
        content.append({"type": "text", "text": f"Frame at {frame['time']:.1f}s:"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame["b64"]},
        })
    content.append({"type": "text", "text": f"""Above are frames from a reference video.

Reference facts:
- Duration: {analysis['duration']:.1f} seconds, {analysis['width']}x{analysis['height']}
- Scene cuts ({len(analysis['scene_starts'])} scenes): {cuts}
- Transcript with timings:
{transcript}

Study how the reference works: how it hooks the viewer, how fast it cuts, what is shown on screen, how the captions look and where they sit, the tone of voice, and how it ends.

Now design a NEW video that recreates this reference: same structure beat for beat, same pacing (mirror the number and rhythm of its scenes), same visual and caption style, same tone. Unless the creator's instructions say otherwise, keep the same subject as the reference but with entirely original wording.
{_direction(notes)}
{SCHEMA}"""})
    return _ask(content)


def from_topic(topic: str, notes: str = "") -> dict:
    """Blueprint for a brand-new video from a topic alone."""
    return _ask(f"""Design a high-retention vertical short video about:
"{topic}"

Use a strong pattern-interrupt hook, fast pacing, one clear idea per scene and a satisfying ending.
{_direction(notes)}
{SCHEMA}""")


def remix(previous: dict, notes: str = "") -> dict:
    """A fresh take on an earlier blueprint, keeping its style."""
    kept = {k: previous.get(k) for k in ("topic", "style_analysis", "caption_style")}
    old_script = " ".join(s.get("narration", "") for s in previous.get("scenes", []))
    return _ask(f"""Here is the style and topic of a video we made earlier:
{json.dumps(kept, indent=1)}

Its script was:
"{old_script}"

Design a NEW version: same topic, same style and pacing, same number of scenes, but a different hook, different wording and different visuals so it feels fresh.
{_direction(notes)}
{SCHEMA}""")
