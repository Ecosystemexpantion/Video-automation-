import asyncio
import edge_tts
import os
from config import TTS_VOICE

OUTPUT_DIR = "tmp"


async def _generate_async(text: str, output_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_voiceover(script_text: str, output_filename: str = "voiceover.mp3") -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    asyncio.run(_generate_async(script_text, output_path, TTS_VOICE))
    return output_path


def get_available_voices() -> list[str]:
    async def _list():
        voices = await edge_tts.list_voices()
        return [v["ShortName"] for v in voices if "en" in v["ShortName"].lower()]
    return asyncio.run(_list())


if __name__ == "__main__":
    test_script = "Did you know ChatGPT can write 10 client emails in 5 minutes? Here's how to make money with it. First, find businesses that need email marketing. Second, use ChatGPT to write the emails. Third, charge them $50 per email. Join our free WhatsApp community for more tips."
    path = generate_voiceover(test_script)
    print(f"Generated: {path}")
