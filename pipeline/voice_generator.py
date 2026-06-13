import os
import requests
from config import ELEVENLABS_API_KEY

OUTPUT_DIR = "tmp"

# "Rachel" — available on free tier, clear and natural female voice
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
MODEL_ID = "eleven_turbo_v2_5"

VOICE_SETTINGS = {
    "stability": 0.45,
    "similarity_boost": 0.82,
    "style": 0.35,
    "use_speaker_boost": True,
}


def generate_voiceover(script_text: str, output_filename: str = "voiceover.mp3") -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    if not ELEVENLABS_API_KEY:
        from gtts import gTTS
        tts = gTTS(text=script_text, lang="en", slow=False)
        tts.save(output_path)
        return output_path

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": script_text,
        "model_id": MODEL_ID,
        "voice_settings": VOICE_SETTINGS,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")

    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path


if __name__ == "__main__":
    test = "AI automation is changing how businesses operate. Here is how you can use it to make real money online."
    path = generate_voiceover(test)
    print(f"Generated: {path}")
