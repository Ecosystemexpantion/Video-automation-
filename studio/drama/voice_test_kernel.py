# Voice shoot-out on a Kaggle GPU: the same fruit-drama scene read by
#   1. Chatterbox (current engine, cloned from Kokoro reference clips)
#   2. OmniVoice voice design (k2-fsa/OmniVoice, the default engine of VoiceStudio)
#   3. OmniVoice voice cloning (same Kokoro references)
# Each engine runs in its own process so one failure does not stop the others.
import glob, json, subprocess, sys, textwrap, time
from pathlib import Path

SP = json.loads(r'''__CFG_JSON__''')["screenplay"]
WORK = Path("/kaggle/working"); OUT = WORK / "out"; OUT.mkdir(exist_ok=True)
REFS = Path(sorted(glob.glob("/kaggle/input/**/refs", recursive=True))[0])
t0 = time.time()
def log(m): print(f"[{(time.time()-t0)/60:5.1f} min] {m}", flush=True)
def sh(c): log("$ " + c); return subprocess.run(c, shell=True).returncode

chars = {c["id"]: c for c in SP["characters"]}
lines = []
for s in SP["shots"]:
    for ln in s.get("lines") or []:
        lines.append({"char": s[ln["speaker"]], "text": ln["text"], "emotion": ln.get("emotion", 0.55)})
lines = lines[:8]  # a ~40 s scene

def design(c):
    v = (c.get("voice", "") + " " + c.get("look", "")).lower()
    if "child" in v or "little" in c["name"].lower() or "young" in v:
        return "female, child, high pitch, american accent"
    if "grump" in v or "old" in v or "low" in v:
        return "male, elderly, low pitch, american accent"
    if "female" in v:
        return "female, young adult, moderate pitch, american accent"
    return "male, middle-aged, moderate pitch, british accent"

(WORK / "job.json").write_text(json.dumps({
    "lines": lines, "refs": {cid: str(REFS / f"{cid}.wav") for cid in chars},
    "design": {cid: design(c) for cid, c in chars.items()}, "out": str(OUT)}))
log("designs: " + json.dumps({chars[k]["name"]: design(v) for k, v in chars.items()}))

COMMON = '''
import json, torch, torchaudio as ta
J = json.load(open("/kaggle/working/job.json"))
def save(name, pieces, sr):
    gap = torch.zeros(1, int(sr * 0.35))
    out = torch.cat([torch.cat([p.reshape(1, -1).float().cpu(), gap], 1) for p in pieces], 1)
    ta.save(f"{J['out']}/{name}.wav", out, sr); print("saved", name, flush=True)
'''

engines = {
 "chatterbox": ("pip install -q --no-deps chatterbox-tts && pip install -q s3tokenizer conformer resemble-perth librosa diffusers safetensors omegaconf pyloudnorm",
  COMMON + '''
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device="cuda")
save("chatterbox", [m.generate(l["text"], audio_prompt_path=J["refs"][l["char"]],
     exaggeration=float(l["emotion"]), cfg_weight=0.4) for l in J["lines"]], m.sr)
'''),
 "omnivoice": ("pip install -q --no-deps omnivoice && python - <<'EOF'\n"
               "import importlib.metadata as md, subprocess, re\n"
               "reqs=[r.split(';')[0] for r in (md.requires('omnivoice') or []) if 'extra ==' not in r]\n"
               "reqs=[r for r in reqs if not re.match(r'\\s*(torch|torchaudio|torchvision)\\b', r)]\n"
               "print(reqs); subprocess.run(['pip','install','-q',*reqs])\nEOF",
  COMMON + '''
from omnivoice import OmniVoice
m = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16)
sr = 24000
def wav(a): return torch.as_tensor(a[0] if isinstance(a, (list, tuple)) else a)
save("omnivoice_design", [wav(m.generate(text=l["text"], instruct=J["design"][l["char"]])) for l in J["lines"]], sr)
try:
    save("omnivoice_clone", [wav(m.generate(text=l["text"], ref_audio=J["refs"][l["char"]])) for l in J["lines"]], sr)
except Exception as e:
    print("clone failed:", e)
'''),
}
for name, (install, code) in engines.items():
    sh(install)
    p = WORK / f"run_{name}.py"; p.write_text(textwrap.dedent(code))
    log(f"{name}: exit {sh(f'{sys.executable} {p}')}")
log("done: " + ", ".join(x.name for x in OUT.glob("*.wav")))
