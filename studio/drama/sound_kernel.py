# Davis Studio drama sound stage on a Kaggle GPU.
#   MMAudio (hkchengrex/MMAudio): picture-synced sound effects + ambience for every shot
#   MusicGen (facebook/musicgen-medium): an original background score
import glob, json, os, subprocess, sys, time
from pathlib import Path

SP = json.loads(r'''__CFG_JSON__''')["screenplay"]
WORK = Path("/kaggle/working"); OUT = WORK / "out"; OUT.mkdir(exist_ok=True)
SHOTS = Path(sorted(glob.glob("/kaggle/input/**/shot_*.mp4", recursive=True))[0]).parent
t0 = time.time()
def log(m): print(f"[{(time.time()-t0)/60:6.1f} min] {m}", flush=True)
def sh(c):
    log("$ " + c); return subprocess.run(c, shell=True).returncode

# ---------- MMAudio sound effects ----------
sh("git clone -q --depth 1 https://github.com/hkchengrex/MMAudio.git /tmp/MMAudio")
sh("pip install -q --no-deps -e /tmp/MMAudio")
sh("pip install -q torchdiffeq einops hydra-core hydra_colorlog colorlog nitrous-ema tensordict "
   "open_clip_torch 'av>=14' timm python-dotenv gitpython librosa torchcodec")
mood = SP.get("title", "")
for s in SP["shots"]:
    v = SHOTS / f"shot_{s['id']}.mp4"
    if not v.exists():
        continue
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                               capture_output=True, text=True).stdout or 3)
    talk = bool(s.get("lines"))
    prompt = ("quiet cozy kitchen room tone at night, soft fridge hum, subtle movement foley" if talk else
              f"cartoon foley sound effects: {s.get('visual','')} {s.get('motion','')}. squishy fruit bumps, "
              "rolling, thuds, whooshes, playful slapstick impacts, cozy kitchen ambience")
    out = WORK / f"mm_{s['id']}"
    rc = sh(f"cd /tmp/MMAudio && {sys.executable} demo.py --video '{v}' --duration {dur:.2f} "
            f"--prompt \"{prompt.replace(chr(34), '')}\" --negative_prompt 'speech, talking, voice, music' "
            f"--output '{out}' --skip_video_composite")
    flacs = glob.glob(str(out / "*.flac"))
    if rc == 0 and flacs:
        os.replace(flacs[0], OUT / f"sfx_{s['id']}.flac"); log(f"sfx shot {s['id']}")
    else:
        log(f"sfx FAILED shot {s['id']}")

# ---------- MusicGen score ----------
sh("pip install -q transformers scipy")
import torch, numpy as np, scipy.io.wavfile as wf
from transformers import AutoProcessor, MusicgenForConditionalGeneration
proc = AutoProcessor.from_pretrained("facebook/musicgen-medium")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-medium", torch_dtype=torch.float16).to("cuda")
sr = model.config.audio_encoder.sampling_rate
cues = {
    "calm": "gentle whimsical orchestral animated film score, pizzicato strings, warm celesta, cozy night, light and playful",
    "fight": "comedic slapstick chase music, fast pizzicato, bouncy brass stabs, cartoon action, animated film",
    "warm": "heartwarming uplifting orchestral finale, soft strings and piano, animated film ending, gentle and happy",
}
for name, text in cues.items():
    inp = proc(text=[text], padding=True, return_tensors="pt").to("cuda")
    with torch.no_grad():
        audio = model.generate(**inp, max_new_tokens=1500, do_sample=True, guidance_scale=3.5)
    wf.write(OUT / f"music_{name}.wav", sr, audio[0, 0].float().cpu().numpy())
    log(f"music {name}")
log("sound done")
