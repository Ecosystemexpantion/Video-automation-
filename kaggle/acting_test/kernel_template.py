# Davis Studio acting test: renders two people talking with InfiniteTalk (Wan2GP) on a Kaggle GPU.
import base64
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

JOB = json.loads(r'''__JOB_JSON__''')
WORK = Path("/kaggle/working")
INP = WORK / "inputs"
OUT = WORK / "out"
INP.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
for name, data in JOB["files"].items():
    (INP / name).write_bytes(base64.b64decode(data))

t0 = time.time()
def log(msg):
    print(f"[{(time.time() - t0) / 60:5.1f} min] {msg}", flush=True)

def sh(cmd):
    log("$ " + cmd)
    return subprocess.run(cmd, shell=True)

log(f"Python {sys.version.split()[0]}")
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh("free -g; df -h /kaggle/working /tmp | tail -2")

SRC = Path("/kaggle/temp/Wan2GP") if Path("/kaggle/temp").exists() else Path("/tmp/Wan2GP")
if not SRC.exists():
    sh(f"git clone -q --depth 1 https://github.com/deepbeepmeep/Wan2GP.git {SRC}")

# Keep Kaggle's own torch build; install the rest best-effort.
skip = ("torch", "torchvision", "torchaudio", "torchcodec", "onnxruntime", "--extra-index-url",
        "xformers", "flash", "sage", "triton")
reqs = []
for line in (SRC / "requirements.txt").read_text().splitlines():
    s = line.strip()
    if not s or s.startswith("#") or s.lower().startswith(skip):
        continue
    reqs.append(s)
(WORK / "reqs.txt").write_text("\n".join(reqs))
if sh(f"pip install -q -r {WORK / 'reqs.txt'}").returncode != 0:
    log("Bulk install failed; installing one by one")
    for r in reqs:
        if sh(f"pip install -q '{r}'").returncode != 0:
            log(f"  could not install: {r}")
sh("pip list 2>/dev/null | grep -i -E '^(torch|numpy|diffusers|transformers|optimum-quanto|gradio) '")
log("Install done")

os.chdir(SRC)
sys.path.insert(0, str(SRC))
from shared.api import init

session = init(
    root=SRC,
    output_dir=OUT,
    cli_args=["--attention", "sdpa", "--profile", "4", "--fp16"],
)
log("WanGP session ready")

frames = int(math.ceil(JOB["seconds"] * 25)) + 1
settings = {
    "model_type": "infinitetalk_multi",
    "prompt": JOB["prompt"],
    "resolution": "832x480",
    "image_prompt_type": "T",
    "video_prompt_type": "0KI",
    "image_refs": [str(INP / "scene.jpg")],
    "audio_prompt_type": "PAB",
    "audio_guide": str(INP / "speaker1.mp3"),
    "audio_guide2": str(INP / "speaker2.mp3"),
    "speakers_locations": "0:50 50:100",
    "video_length": frames,
    "sliding_window_size": 81,
    "num_inference_steps": JOB.get("steps", 10),
    "guidance_scale": 1,
    "audio_guidance_scale": 1,
    "activated_loras": ["https://huggingface.co/DeepBeepMeep/Wan2.1/resolve/main/loras_accelerators/Wan2.1_I2V_14B_FusionX_LoRA.safetensors"],
    "loras_multipliers": "1",
    "seed": 42,
}
log(f"Rendering {frames} frames")
job = session.submit_task(settings)
last = 0
for event in job.events.iter(timeout=1.0):
    if event.kind == "progress":
        p = event.data
        if time.time() - last > 60:
            log(f"progress {p.phase} step {p.current_step}/{p.total_steps}")
            last = time.time()
    elif event.kind == "stream":
        line = event.data
        if line.text.strip():
            print(f"  [{line.stream}] {line.text}", flush=True)
result = job.result()
log(f"Success: {result.success}")
if not result.success:
    for e in result.errors:
        print("ERROR:", e.message, flush=True)
for f in result.generated_files:
    log(f"Generated: {f}")
    if not str(f).startswith(str(OUT)):
        shutil.copy(f, OUT)
shutil.copy(INP / "scene.jpg", OUT / "scene.jpg")
log("Done")
