# Davis Studio drama engine on a Kaggle GPU.
#   MODE "images": character designs, location plates and a start frame per shot (FLUX.2 Klein 4B)
#   MODE "render": voices (Chatterbox) + lip-synced dialogue (InfiniteTalk) + motion shots (Wan2.1 i2v FusioniX)
import base64, glob, json, math, os, shutil, subprocess, sys, textwrap, time
from pathlib import Path

CFG = json.loads(r'''__CFG_JSON__''')
MODE, SHARD, SHARDS = CFG["mode"], CFG.get("shard", 0), CFG.get("shards", 1)
SP = CFG["screenplay"]
WORK = Path("/kaggle/working"); OUT = WORK / "out"; OUT.mkdir(exist_ok=True)
ASSETS = next((Path(p).parent for p in sorted(glob.glob("/kaggle/input/**/refs", recursive=True))), None)
print("ASSETS dir:", ASSETS, glob.glob("/kaggle/input/**", recursive=True)[:40])
t0 = time.time()
W, H = 832, 480

def log(m): print(f"[{(time.time()-t0)/60:6.1f} min] {m}", flush=True)
def sh(c):
    log("$ " + c); return subprocess.run(c, shell=True).returncode

chars = {c["id"]: c for c in SP["characters"]}
locs = {l["id"]: l for l in SP["locations"]}
STYLE = SP.get("style", "high-end 3D animated feature film style, soft cinematic lighting")

def speech_cost(s):
    return sum(len(l["text"].split()) for l in s.get("lines") or []) / 2.6 or 3.2

# ---------------- voices first (Chatterbox uses the GPU, then frees it) ----------------
my_shots = []
if MODE == "render":
    ordered = sorted(SP["shots"], key=speech_cost, reverse=True)
    loads = [0.0] * SHARDS
    owner = {}
    for s in ordered:
        k = loads.index(min(loads)); owner[s["id"]] = k; loads[k] += speech_cost(s)
    my_shots = [s for s in SP["shots"] if owner[s["id"]] == SHARD]
    log(f"shard {SHARD}/{SHARDS}: {len(my_shots)} shots, ~{loads[SHARD]:.0f}s of footage")
    (WORK / "my_shots.json").write_text(json.dumps(my_shots))
    (WORK / "chars.json").write_text(json.dumps(chars))
    sh("pip install -q --no-deps chatterbox-tts")
    sh("pip install -q s3tokenizer conformer resemble-perth librosa diffusers safetensors omegaconf pyloudnorm")
    vp = WORK / "voices.py"
    vp.write_text(textwrap.dedent(f'''
        import json, torch, torchaudio as ta
        from chatterbox.tts import ChatterboxTTS
        shots = json.load(open("{WORK}/my_shots.json")); chars = json.load(open("{WORK}/chars.json"))
        model = ChatterboxTTS.from_pretrained(device="cuda"); sr = model.sr
        for s in shots:
            if not s.get("lines"): continue
            tr = {{"left": [], "right": []}}
            for ln in s["lines"]:
                ref = "{ASSETS}/refs/" + chars[s[ln["speaker"]]]["id"] + ".wav"
                wav = model.generate(ln["text"], audio_prompt_path=ref,
                                     exaggeration=float(ln.get("emotion", 0.55)), cfg_weight=0.4)
                other = "right" if ln["speaker"] == "left" else "left"
                tr[ln["speaker"]] += [wav, torch.zeros(1, int(sr * 0.3))]
                tr[other] += [torch.zeros_like(wav), torch.zeros(1, int(sr * 0.3))]
            for side in ("left", "right"):
                ta.save(f"{WORK}/shot{{s['id']}}_{{side}}.wav", torch.cat(tr[side], dim=1), sr)
            print("voiced shot", s["id"], flush=True)
    '''))
    assert sh(f"{sys.executable} {vp}") == 0, "voices failed"

# ---------------- Wan2GP ----------------
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
session = init(root=SRC, output_dir=WORK / "tmp_out", cli_args=["--attention", "sdpa", "--profile", "4", "--fp16"])

def generate(settings, dest: Path):
    tmp = WORK / "tmp_out"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    job = session.submit_task(settings)
    for _ in job.events.iter(timeout=1.0): pass
    res = job.result()
    files = sorted([f for f in glob.glob(str(tmp / "**" / "*"), recursive=True) if os.path.isfile(f)], key=os.path.basename)
    files += [f for f in res.generated_files if os.path.exists(f)]
    if not res.success or not files:
        log(f"FAILED {dest.name}: {[e.message for e in res.errors]}")
        return False
    best = sorted(files, key=lambda f: (os.path.splitext(f)[1] != dest.suffix, os.path.basename(f)))
    pick = [f for f in best if f.endswith(dest.suffix)] or best
    shutil.copy(sorted(pick, key=os.path.basename)[-1], dest)
    log(f"made {dest.name}")
    return True

def flux(prompt, dest, refs=None, mode="I", res=f"{W}x{H}", seed=7):
    st = {"model_type": "flux2_klein_4b", "prompt": prompt, "resolution": res,
          "num_inference_steps": 4, "embedded_guidance_scale": 1, "seed": seed, "image_mode": 1}
    if refs:
        st.update({"video_prompt_type": mode, "image_refs": [str(r) for r in refs]})
    return generate(st, dest)

# ---------------- MODE images ----------------
if MODE == "images":
    (OUT / "refs").mkdir(exist_ok=True); (OUT / "frames").mkdir(exist_ok=True)
    for c in SP["characters"]:
        flux(f"{STYLE}. Character design sheet, full body, front three-quarter view: {c['look']}. "
             "Expressive friendly face with big eyes and a clearly visible mouth. Plain soft grey studio background.",
             OUT / "refs" / f"char_{c['id']}.png", res="768x768", seed=11)
    for l in SP["locations"]:
        flux(f"{STYLE}. Wide establishing shot, no characters: {l['description']}.", OUT / "refs" / f"loc_{l['id']}.png")
    for s in SP["shots"]:
        cast = [s.get("left"), s.get("right")]
        refs = [OUT / "refs" / f"loc_{s['location']}.png"]
        desc = []
        for side, cid in zip(("left", "right"), cast):
            if cid:
                refs.append(OUT / "refs" / f"char_{cid}.png")
                desc.append(f"On the {side} side of the frame: {chars[cid]['name']}, {chars[cid]['look']}")
        if s.get("left") and not s.get("right"):
            desc = [f"{chars[s['left']]['name']} ({chars[s['left']]['look']}) fills the centre of the frame, facing slightly toward camera"]
        prompt = (f"{STYLE}. {s.get('framing', 'medium shot')} in this location: {locs[s['location']]['description']}. "
                  + " ".join(desc) + f". {s.get('visual', '')}. Faces and mouths clearly visible, cinematic composition.")
        ok = flux(prompt, OUT / "frames" / f"shot_{s['id']}.png", refs=[r for r in refs if r.exists()], mode="KI", seed=100 + s["id"])
        if not ok:
            flux(prompt, OUT / "frames" / f"shot_{s['id']}.png", seed=100 + s["id"])
    log("images done")

# ---------------- MODE render ----------------
if MODE == "render":
    import soundfile as sf
    FUSIONX = "https://huggingface.co/DeepBeepMeep/Wan2.1/resolve/main/loras_accelerators/Wan2.1_I2V_14B_FusionX_LoRA.safetensors"
    talk = [s for s in my_shots if s.get("lines")]
    move = [s for s in my_shots if not s.get("lines")]
    for s in talk:
        frame = ASSETS / "frames" / f"shot_{s['id']}.png"
        left, right = WORK / f"shot{s['id']}_left.wav", WORK / f"shot{s['id']}_right.wav"
        two = bool(s.get("left") and s.get("right"))
        secs = sf.info(str(left)).duration
        st = {"model_type": "infinitetalk_multi" if two else "infinitetalk",
              "prompt": f"{STYLE}. {s.get('visual', '')}. Characters talk with expressive faces and natural mouth movement.",
              "resolution": f"{W}x{H}", "image_prompt_type": "T", "video_prompt_type": "0KI",
              "image_refs": [str(frame)], "audio_prompt_type": "PAB" if two else "A",
              "audio_guide": str(left), "video_length": int(math.ceil(secs * 25)) + 1,
              "sliding_window_size": 81, "num_inference_steps": CFG.get("steps", 6),
              "guidance_scale": 1, "audio_guidance_scale": 1,
              "activated_loras": [FUSIONX], "loras_multipliers": "1", "seed": 42}
        if two:
            st.update({"audio_guide2": str(right), "speakers_locations": "0:50 50:100"})
        log(f"shot {s['id']}: dialogue {secs:.1f}s ({'two-shot' if two else 'single'})")
        generate(st, OUT / f"shot_{s['id']}.mp4")
    for s in move:
        frame = ASSETS / "frames" / f"shot_{s['id']}.png"
        st = {"model_type": "i2v_fusionix",
              "prompt": f"{STYLE}. {s.get('visual', '')}. {s.get('motion', '')}. Dynamic, expressive animation.",
              "resolution": f"{W}x{H}", "image_prompt_type": "S", "image_start": str(frame),
              "video_length": 81, "num_inference_steps": 8, "guidance_scale": 1, "seed": 42}
        log(f"shot {s['id']}: motion")
        generate(st, OUT / f"shot_{s['id']}.mp4")
    log("render done")
