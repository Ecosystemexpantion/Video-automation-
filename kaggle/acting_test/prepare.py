"""
Prepares the acting test on GitHub Actions (CPU): a photo of two people,
their voiced dialogue as two parallel tracks, and the Kaggle kernel script
that renders them with InfiniteTalk through Wan2GP.
"""

import base64
import io
import json
import os
import sys

import numpy as np
import requests
import soundfile as sf
from PIL import Image

OUT = sys.argv[1]
W, H = 832, 480
RATE = 24000
GAP = 0.35

LINES = [
    ("left", "am_michael", "Did you see what happened at the market today?"),
    ("right", "af_heart", "No, tell me everything. Was it the new shop?"),
    ("left", "am_michael", "Yes! They sold out of everything in one hour."),
    ("right", "af_heart", "Then we are going there first thing tomorrow."),
]
PROMPT = ("A man on the left and a woman on the right sit at a cafe table having a lively, "
          "friendly conversation, natural facial expressions, subtle head movements, cinematic lighting")


def fetch_photo() -> Image.Image:
    for query in ["man and woman talking cafe", "two friends talking table", "couple conversation"]:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": os.environ["PEXELS_API_KEY"]},
            params={"query": query, "orientation": "landscape", "per_page": 10},
            timeout=30,
        )
        r.raise_for_status()
        for photo in r.json().get("photos", []):
            img = Image.open(io.BytesIO(requests.get(photo["src"]["large2x"], timeout=60).content)).convert("RGB")
            scale = max(W / img.width, H / img.height)
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
            left, top = (img.width - W) // 2, (img.height - H) // 2
            print("Photo:", photo["url"])
            return img.crop((left, top, left + W, top + H))
    raise RuntimeError("No photo found")


CONFIG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")))
LINES = LINES[: CONFIG.get("lines", len(LINES))]


def voice_tracks():
    from kokoro_onnx import Kokoro

    kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
    left, right = [], []
    gap = np.zeros(int(RATE * GAP), dtype=np.float32)
    for side, voice, text in LINES:
        samples, rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        assert rate == RATE
        samples = np.asarray(samples, dtype=np.float32)
        silence = np.zeros_like(samples)
        left += [samples if side == "left" else silence, gap]
        right += [samples if side == "right" else silence, gap]
    return np.concatenate(left), np.concatenate(right)


def man_side(path: str) -> str:
    """Ask Claude which side of the photo the man is on, so each voice goes to the right face."""
    import anthropic

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    msg = anthropic.Anthropic().messages.create(
        model="claude-opus-4-8",
        max_tokens=50,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
            {"type": "text", "text": "Two main people are in the foreground of this photo. Is the man on the left or the right? Answer with one word: left or right."},
        ]}],
    )
    answer = "".join(b.text for b in msg.content if b.type == "text").strip().lower()
    print("Claude says the man is on the:", answer)
    return "right" if "right" in answer else "left"


def main():
    os.makedirs(OUT, exist_ok=True)
    photo = fetch_photo()
    photo.save(os.path.join(OUT, "scene.jpg"), quality=85)
    side = man_side(os.path.join(OUT, "scene.jpg"))
    a, b = voice_tracks()
    sf.write(os.path.join(OUT, "speaker1.wav"), a, RATE)
    sf.write(os.path.join(OUT, "speaker2.wav"), b, RATE)
    import subprocess
    for n in ("speaker1", "speaker2"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, n + ".wav"),
                        "-b:a", "64k", os.path.join(OUT, n + ".mp3")], check=True)
    seconds = len(a) / RATE
    print(f"Dialogue length: {seconds:.1f}s")

    def b64(name):
        with open(os.path.join(OUT, name), "rb") as f:
            return base64.b64encode(f.read()).decode()

    job = {
        "prompt": PROMPT,
        "steps": CONFIG.get("steps", 10),
        # Speaker 1 (the man, first track) is listed first.
        "speakers_locations": "0:50 50:100" if side == "left" else "50:100 0:50",
        "seconds": seconds,
        "files": {name: b64(name) for name in ("scene.jpg", "speaker1.mp3", "speaker2.mp3")},
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "kernel_template.py")) as f:
        script = f.read().replace("__JOB_JSON__", json.dumps(job))
    print("Kernel script size: %d KB" % (len(script) // 1024))
    run_dir = os.path.join(OUT, "kernel")
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "acting_test.py"), "w") as f:
        f.write(script)


if __name__ == "__main__":
    main()
