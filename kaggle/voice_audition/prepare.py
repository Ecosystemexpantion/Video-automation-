"""Builds the voice audition kernel: Kokoro baseline + reference clips, embedded into the Kaggle script."""
import base64, json, os, subprocess, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
RATE = 24000
LINES = [
    ("man", "Did you see what happened at the market today?"),
    ("woman", "No, tell me everything. Was it the new shop?"),
    ("man", "Yes! They sold out of everything in one hour."),
    ("woman", "Then we are going there first thing tomorrow."),
]
VOICE = {"man": "am_michael", "woman": "af_heart"}

kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
gap = np.zeros(int(RATE * 0.35), dtype=np.float32)
parts = []
for who, text in LINES:
    s, r = kokoro.create(text, voice=VOICE[who], speed=1.0, lang="en-us")
    parts += [np.asarray(s, dtype=np.float32), gap]
sf.write(f"{OUT}/kokoro.wav", np.concatenate(parts), RATE)

# Short reference clips so Chatterbox keeps one consistent male and female voice.
refs = {
    "man": "Honestly, I think this is one of the best ideas we have had in a long time, and I am excited to get started.",
    "woman": "I love that you said that, because I have been thinking about it all week and I am really excited too.",
}
for who, text in refs.items():
    s, r = kokoro.create(text, voice=VOICE[who], speed=1.0, lang="en-us")
    sf.write(f"{OUT}/ref_{who}.wav", np.asarray(s, dtype=np.float32), RATE)

def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()

job = {"lines": LINES, "files": {f"ref_{w}.wav": b64(f"{OUT}/ref_{w}.wav") for w in refs}}
here = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(here, "kernel_template.py")).read().replace("__JOB_JSON__", json.dumps(job))
os.makedirs(f"{OUT}/kernel", exist_ok=True)
open(f"{OUT}/kernel/voice_audition.py", "w").write(script)
print("Kernel script size: %d KB" % (len(script) // 1024))
