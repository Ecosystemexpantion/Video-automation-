# Davis Studio voice audition: the same dialogue spoken by Dia and by Chatterbox on a Kaggle GPU.
import base64, json, os, subprocess, sys, textwrap, time
from pathlib import Path

JOB = json.loads(r'''__JOB_JSON__''')
WORK = Path("/kaggle/working")
OUT = WORK / "out"
OUT.mkdir(exist_ok=True)
for name, data in JOB["files"].items():
    (WORK / name).write_bytes(base64.b64decode(data))
(WORK / "job.json").write_text(json.dumps(JOB))
t0 = time.time()

def sh(cmd):
    print(f"[{(time.time()-t0)/60:4.1f} min] $ {cmd}", flush=True)
    return subprocess.run(cmd, shell=True).returncode

def run_py(name, code):
    path = WORK / f"{name}.py"
    path.write_text(textwrap.dedent(code))
    rc = sh(f"{sys.executable} {path}")
    print(f"{name}: {'OK' if rc == 0 else 'FAILED'}", flush=True)

# --- Dia: one pass for the whole two-person dialogue ---
sh("pip install -q -U 'transformers>=4.56' accelerate soundfile")
run_py("run_dia", '''
    import json, torch
    from transformers import AutoProcessor, DiaForConditionalGeneration
    job = json.load(open("/kaggle/working/job.json"))
    tag = {"man": "[S1]", "woman": "[S2]"}
    text = " ".join(f"{tag[w]} {t}" for w, t in job["lines"])
    print("Dia script:", text)
    mid = "nari-labs/Dia-1.6B-0626"
    processor = AutoProcessor.from_pretrained(mid)
    model = DiaForConditionalGeneration.from_pretrained(mid, torch_dtype=torch.float16).to("cuda")
    for seed in (7, 21):
        torch.manual_seed(seed)
        inputs = processor(text=[text], padding=True, return_tensors="pt").to("cuda")
        out = model.generate(**inputs, max_new_tokens=3072, guidance_scale=3.0, temperature=1.8, top_p=0.90, top_k=45)
        processor.save_audio(processor.batch_decode(out), f"/kaggle/working/out/dia_take{seed}.wav")
        print("saved dia take", seed)
''')

# --- Chatterbox: each line with a consistent male / female voice ---
sh("pip install -q chatterbox-tts")
run_py("run_chatterbox", '''
    import json, torch, torchaudio as ta
    from chatterbox.tts import ChatterboxTTS
    job = json.load(open("/kaggle/working/job.json"))
    model = ChatterboxTTS.from_pretrained(device="cuda")
    pieces = []
    for who, text in job["lines"]:
        wav = model.generate(text, audio_prompt_path=f"/kaggle/working/ref_{who}.wav",
                             exaggeration=0.6, cfg_weight=0.4)
        pieces += [wav, torch.zeros(1, int(model.sr * 0.35))]
    ta.save("/kaggle/working/out/chatterbox.wav", torch.cat(pieces, dim=1), model.sr)
    print("saved chatterbox")
''')
sh("ls -la /kaggle/working/out")
