# Davis Studio talking scenes: Chatterbox voices + InfiniteTalk lip sync on a Kaggle GPU.
import base64, glob, json, math, os, shutil, subprocess, sys, textwrap, time
from pathlib import Path

JOB = json.loads(r'''__JOB_JSON__''')
WORK = Path("/kaggle/working")
INP, OUT = WORK / "inputs", WORK / "out"
INP.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
for name, data in JOB["files"].items():
    (INP / name).write_bytes(base64.b64decode(data))
(WORK / "job.json").write_text(json.dumps(JOB))
t0 = time.time()

def log(m): print(f"[{(time.time()-t0)/60:5.1f} min] {m}", flush=True)
def sh(c):
    log("$ " + c); return subprocess.run(c, shell=True).returncode

# ---------- 1. voices (Chatterbox, keeping Kaggle's torch) ----------
sh("pip install -q --no-deps chatterbox-tts")
sh("pip install -q s3tokenizer conformer resemble-perth librosa diffusers safetensors omegaconf pyloudnorm")
voice_py = WORK / "make_voices.py"
voice_py.write_text(textwrap.dedent('''
    import json, torch, torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    job = json.load(open("/kaggle/working/job.json"))
    model = ChatterboxTTS.from_pretrained(device="cuda")
    sr, gap = model.sr, 0.35
    for i, scene in enumerate(job["scenes"]):
        tracks = {"left": [], "right": []}
        for line in scene["lines"]:
            ref = f"/kaggle/working/inputs/ref_{line.get('voice', 'female')}.wav"
            wav = model.generate(line["text"], audio_prompt_path=ref,
                                 exaggeration=float(line.get("emotion", 0.55)), cfg_weight=0.4)
            silence = torch.zeros_like(wav)
            side = line.get("speaker", "left")
            other = "right" if side == "left" else "left"
            tracks[side] += [wav, torch.zeros(1, int(sr * gap))]
            tracks[other] += [silence, torch.zeros(1, int(sr * gap))]
        for side in ("left", "right"):
            ta.save(f"/kaggle/working/inputs/scene{i}_{side}.wav", torch.cat(tracks[side], dim=1), sr)
        print("voiced scene", i)
'''))
assert sh(f"{sys.executable} {voice_py}") == 0, "voice generation failed"

# ---------- 2. lip sync (InfiniteTalk via Wan2GP) ----------
SRC = Path("/tmp/Wan2GP")
sh(f"git clone -q --depth 1 https://github.com/deepbeepmeep/Wan2GP.git {SRC}")
skip = ("torch", "torchvision", "torchaudio", "torchcodec", "onnxruntime", "--extra-index-url", "xformers", "flash", "sage", "triton")
reqs = [l.strip() for l in (SRC / "requirements.txt").read_text().splitlines()
        if l.strip() and not l.strip().startswith("#") and not l.strip().lower().startswith(skip)]
(WORK / "reqs.txt").write_text("\n".join(reqs))
if sh(f"pip install -q -r {WORK/'reqs.txt'}") != 0:
    for r in reqs: sh(f"pip install -q '{r}'")
os.chdir(SRC); sys.path.insert(0, str(SRC))
from shared.api import init
import soundfile as sf

FUSIONX = "https://huggingface.co/DeepBeepMeep/Wan2.1/resolve/main/loras_accelerators/Wan2.1_I2V_14B_FusionX_LoRA.safetensors"
for i, scene in enumerate(JOB["scenes"]):
    sides = {l.get("speaker", "left") for l in scene["lines"]}
    two = len(sides) == 2
    left = INP / f"scene{i}_left.wav"
    right = INP / f"scene{i}_right.wav"
    solo = left if "left" in sides else right
    seconds = sf.info(str(left)).duration
    scene_out = OUT / f"scene{i}"
    scene_out.mkdir(exist_ok=True)
    session = init(root=SRC, output_dir=scene_out, cli_args=["--attention", "sdpa", "--profile", "4", "--fp16"])
    settings = {
        "model_type": "infinitetalk_multi" if two else "infinitetalk",
        "prompt": scene.get("prompt", "natural conversation, subtle head movements, cinematic lighting"),
        "resolution": scene.get("resolution", "480x832"),
        "image_prompt_type": "T", "video_prompt_type": "0KI",
        "image_refs": [str(INP / scene["image"])],
        "audio_prompt_type": "PAB" if two else "A",
        "audio_guide": str(left if two else solo),
        "video_length": int(math.ceil(seconds * 25)) + 1,
        "sliding_window_size": 81,
        "num_inference_steps": int(JOB.get("steps", 6)),
        "guidance_scale": 1, "audio_guidance_scale": 1,
        "activated_loras": [FUSIONX], "loras_multipliers": "1", "seed": 42,
    }
    if two:
        settings.update({"audio_guide2": str(right), "speakers_locations": "0:50 50:100"})
    log(f"scene {i}: {settings['video_length']} frames, {'two speakers' if two else 'one speaker'}")
    job = session.submit_task(settings)
    for ev in job.events.iter(timeout=1.0):
        pass
    res = job.result()
    log(f"scene {i} success={res.success} {[e.message for e in res.errors] if not res.success else ''}")
    finals = sorted(glob.glob(str(scene_out / "*.mp4")), key=os.path.basename)
    if finals:
        shutil.copy(finals[-1], OUT / f"scene_{i}.mp4")
log("done")
