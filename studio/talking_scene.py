#!/usr/bin/env python3
"""
Talking scenes with natural voices and lip sync, rendered on the owner's free Kaggle GPU.

Usage (from any directory):
  python /path/to/studio/talking_scene.py scenes.json OUT_DIR

scenes.json:
{
  "scenes": [
    {
      "image": "/abs/path/start_frame.jpg",      # one or two people, faces clearly visible
      "resolution": "480x832",                   # WxH; 480x832 vertical or 832x480 landscape
      "prompt": "a woman talking to camera in a bright kitchen, warm natural light",
      "lines": [
        {"speaker": "left", "voice": "female", "text": "Hello!", "emotion": 0.6}
      ]
    }
  ]
}
"speaker" is the person's side of the frame ("left"/"right"; a single person uses "left").
"voice" is "male" or "female". "emotion" 0.3 calm .. 0.9 very expressive.
Writes OUT_DIR/scene_<n>.mp4 with the lip-synced audio. Batch every talking shot into ONE call:
each call costs ~15 min of setup, then roughly 5-6 minutes per second of speech.
"""
import base64, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLUG = "davis-talking-scenes"


def kokoro_refs(tmp: Path) -> dict:
    """Short reference clips that give Chatterbox one stable male and one stable female voice."""
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    k = Kokoro(str(HERE.parent / "kokoro-v1.0.onnx") if (HERE.parent / "kokoro-v1.0.onnx").exists() else "kokoro-v1.0.onnx",
               str(HERE.parent / "voices-v1.0.bin") if (HERE.parent / "voices-v1.0.bin").exists() else "voices-v1.0.bin")
    text = "Honestly, I think this is one of the best ideas we have had in a long time, and I am excited to get started."
    out = {}
    for name, voice in (("male", "am_michael"), ("female", "af_heart")):
        s, r = k.create(text, voice=voice, speed=1.0, lang="en-us")
        p = tmp / f"ref_{name}.wav"
        sf.write(p, np.asarray(s, dtype="float32"), r)
        out[p.name] = base64.b64encode(p.read_bytes()).decode()
    return out


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    spec = json.load(open(sys.argv[1]))
    out_dir = Path(sys.argv[2]); out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_kaggle"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()

    files = kokoro_refs(tmp)
    scenes = []
    for i, sc in enumerate(spec["scenes"]):
        img = Path(sc["image"])
        name = f"scene{i}{img.suffix.lower() or '.jpg'}"
        files[name] = base64.b64encode(img.read_bytes()).decode()
        scenes.append({**sc, "image": name})
    job = {"scenes": scenes, "files": files, "steps": spec.get("steps", 6)}
    script = (HERE / "talk" / "kernel_template.py").read_text().replace("__JOB_JSON__", json.dumps(job))
    (tmp / "talk.py").write_text(script)

    user = run([sys.executable, "-c", "from kaggle.api.kaggle_api_extended import KaggleApi as K; a=K(); a.authenticate(); print(a.get_config_value('username') or '')"]).stdout.strip()
    (tmp / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{SLUG}", "title": SLUG, "code_file": "talk.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True}))
    push = run(["kaggle", "kernels", "push", "-p", str(tmp)])
    print(push.stdout, push.stderr)
    if push.returncode != 0:
        sys.exit("Could not start the Kaggle GPU job")

    time.sleep(60)
    while True:
        st = run(["kaggle", "kernels", "status", f"{user}/{SLUG}"]).stdout
        print(time.strftime("%H:%M"), st.strip(), flush=True)
        if any(w in st for w in ("COMPLETE", "ERROR", "CANCEL")):
            break
        time.sleep(30)

    res = tmp / "result"
    run(["kaggle", "kernels", "output", f"{user}/{SLUG}", "-p", str(res)])
    made = sorted(res.glob("out/scene_*.mp4")) or sorted(res.glob("scene_*.mp4"))
    for f in made:
        shutil.copy(f, out_dir / f.name)
        print("wrote", out_dir / f.name)
    if not made:
        log = next(res.glob("*.log"), None)
        if log:
            print(log.read_text()[-4000:])
        sys.exit("No talking scenes were produced")


if __name__ == "__main__":
    main()
