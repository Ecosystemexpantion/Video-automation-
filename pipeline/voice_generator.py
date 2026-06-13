import os
import numpy as np

OUTPUT_DIR = "tmp"


def generate_voiceover(script_text: str, output_filename: str = "voiceover.mp3") -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        _kokoro(script_text, output_path)
    except Exception as e:
        print(f"  [Voice] Kokoro failed ({e}), falling back to gTTS")
        _gtts(script_text, output_path)

    return output_path


def _kokoro(text: str, output_path: str):
    from kokoro_onnx import Kokoro
    import soundfile as sf

    # af_heart = warm American female, very natural
    kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
    samples, sample_rate = kokoro.create(text, voice="af_heart", speed=1.05, lang="en-us")
    sf.write(output_path, samples, sample_rate)


def _gtts(text: str, output_path: str):
    from gtts import gTTS
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)


if __name__ == "__main__":
    test = "AI automation is changing how businesses operate. Here is how you can use it to make real money online."
    path = generate_voiceover(test)
    print(f"Generated: {path}")
