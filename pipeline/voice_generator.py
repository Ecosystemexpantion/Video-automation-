from gtts import gTTS
import os

OUTPUT_DIR = "tmp"


def generate_voiceover(script_text: str, output_filename: str = "voiceover.mp3") -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    tts = gTTS(text=script_text, lang="en", slow=False)
    tts.save(output_path)
    return output_path


if __name__ == "__main__":
    test_script = "AI automation is changing how businesses operate. Here is how you can use it to grow your digital business."
    path = generate_voiceover(test_script)
    print(f"Generated: {path}")
