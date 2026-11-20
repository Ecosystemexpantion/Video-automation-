#!/usr/bin/env python3
"""GitHub-side orchestration for the drama engine. Subcommands: refs, push, wait, fetch, dataset, assemble."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VOICE = {"male_warm": "am_michael", "male_deep": "am_fenrir", "male_young": "am_adam",
         "female_warm": "af_heart", "female_bright": "af_bella", "female_british": "bf_emma",
         "male_british": "bm_george"}


def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r


def kuser():
    return sh([sys.executable, "-c", "from kaggle.api.kaggle_api_extended import KaggleApi as K; a=K(); a.authenticate(); print(a.get_config_value('username') or '')"]).stdout.strip()


def refs(sp_path, out_dir):
    """One Kokoro reference clip per character so Chatterbox gives each a distinct, stable voice."""
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(str(ROOT / "kokoro-v1.0.onnx"), str(ROOT / "voices-v1.0.bin"))
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    text = "You will not believe what happened today. I am telling you, this changes everything, so listen carefully."
    for c in json.load(open(sp_path))["characters"]:
        v = VOICE.get(c.get("voice", ""), "am_michael" if "male" in c.get("voice", "") else "af_heart")
        s, r = k.create(text, voice=v, speed=1.0, lang="en-us")
        sf.write(out / f"{c['id']}.wav", np.asarray(s, dtype="float32"), r)
        print("voice ref", c["id"], v)


def push(sp_path, mode, slug, shard=0, shards=1, dataset=""):
    d = Path("kernel_" + slug); shutil.rmtree(d, ignore_errors=True); d.mkdir()
    cfg = {"mode": mode, "shard": shard, "shards": shards, "screenplay": json.load(open(sp_path)), "steps": 4}
    (d / "drama.py").write_text((HERE / {"sound": "sound_kernel.py", "voicetest": "voice_test_kernel.py"}.get(mode, "kernel_template.py")).read_text().replace("__CFG_JSON__", json.dumps(cfg)))
    user = kuser()
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": "drama.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True}
    if dataset:
        meta["dataset_sources"] = [f"{user}/{dataset}"]
    (d / "kernel-metadata.json").write_text(json.dumps(meta))
    print(sh(["kaggle", "kernels", "push", "-p", str(d)]).stdout)


def wait(slugs, max_minutes):
    user, left, start = kuser(), set(slugs), time.time()
    time.sleep(60)
    while left and time.time() - start < max_minutes * 60:
        for s in list(left):
            st = sh(["kaggle", "kernels", "status", f"{user}/{s}"], check=False).stdout.strip()
            print(time.strftime("%H:%M"), st, flush=True)
            if any(w in st for w in ("COMPLETE", "ERROR", "CANCEL")):
                left.discard(s)
        if left:
            time.sleep(60)
    if left:
        sys.exit(f"Still running after {max_minutes} min: {sorted(left)}")


def fetch(slug, out_dir):
    user = kuser(); out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    sh(["kaggle", "kernels", "output", f"{user}/{slug}", "-p", str(out)], check=False)
    for log in out.glob("*.log"):
        try:
            txt = "".join(e.get("data", "") for e in json.load(open(log)))
            print("\n".join(l for l in txt.splitlines() if any(k in l for k in ("FAILED", "made ", "shard ", "Error", "error:", "voiced shot"))))
            print(txt[-4000:])
        except Exception:
            print(log.read_text()[-6000:])


def dataset(src_dir, slug):
    user = kuser(); src = Path(src_dir)
    (src / "dataset-metadata.json").write_text(json.dumps({"title": slug, "id": f"{user}/{slug}", "licenses": [{"name": "CC0-1.0"}]}))
    r = sh(["kaggle", "datasets", "version", "-p", str(src), "-m", "update", "-r", "zip"], check=False)
    if r.returncode != 0:
        print(sh(["kaggle", "datasets", "create", "-p", str(src), "-r", "zip"]).stdout)
    for _ in range(40):
        st = sh(["kaggle", "datasets", "status", f"{user}/{slug}"], check=False).stdout
        print("dataset:", st.strip())
        if "ready" in st.lower():
            return
        time.sleep(15)


def assemble(sp_path, shots_dir, out_path, sound_dir=""):
    """Join every shot in screenplay order with burned-in dialogue subtitles."""
    sp = json.load(open(sp_path)); shots = Path(shots_dir); work = Path("assemble"); work.mkdir(exist_ok=True)
    parts, srt, t, n = [], [], 0.0, 1
    cue_pos = {}
    def ts(x): return f"{int(x//3600):02d}:{int(x%3600//60):02d}:{int(x%60):02d},{int((x%1)*1000):03d}"
    for s in sp["shots"]:
        src = shots / f"shot_{s['id']}.mp4"
        if not src.exists():
            print("missing shot", s["id"]); continue
        norm = work / f"n{s['id']}.mp4"
        # every clip -> 832x480, 25 fps, stereo 44.1k audio (silent if the shot has none)
        has_audio = "audio" in sh(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)]).stdout
        vdur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)]).stdout)
        talk = bool(s.get("lines"))
        idx = sp["shots"].index(s); frac = idx / max(1, len(sp["shots"]) - 1)
        cue = "warm" if frac > 0.8 else ("calm" if talk or frac < 0.2 else "fight")
        snd = Path(sound_dir) if sound_dir else None
        sfx = snd / f"sfx_{s['id']}.flac" if snd else None
        mus = snd / f"music_{cue}.wav" if snd else None
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
        mix, n_in = [], 1
        if has_audio:
            mix.append("[0:a]aresample=44100,aformat=channel_layouts=stereo,volume=1.0[a0]")
        if sfx and sfx.exists():
            cmd += ["-i", str(sfx)]
            mix.append(f"[{n_in}:a]aresample=44100,aformat=channel_layouts=stereo,volume={0.25 if talk else 1.0}[a{n_in}]"); n_in += 1
        if mus and mus.exists():
            off = cue_pos.get(cue, 0.0); cue_pos[cue] = off + vdur
            cmd += ["-stream_loop", "-1", "-ss", f"{off % 29:.2f}", "-i", str(mus)]
            mix.append(f"[{n_in}:a]aresample=44100,aformat=channel_layouts=stereo,volume={0.12 if talk else 0.3}[a{n_in}]"); n_in += 1
        if not mix:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            mix.append("[1:a]anull[a1]"); labels = "[a1]"
        labels = "".join(m[m.rindex("["):] for m in mix)
        fc = ";".join(mix) + f";{labels}amix=inputs={len(mix)}:duration=longest:normalize=0[aout]"
        cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", f"{vdur:.3f}",
                "-vf", "scale=832:480:force_original_aspect_ratio=decrease:flags=lanczos,pad=832:480:(ow-iw)/2:(oh-ih)/2,fps=25",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(norm)]
        sh(cmd)
        dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(norm)]).stdout)
        lines = s.get("lines") or []
        if lines:
            words = sum(len(l["text"].split()) for l in lines) or 1
            lt = t
            for l in lines:
                d = dur * len(l["text"].split()) / words
                name = next(c["name"] for c in sp["characters"] if c["id"] == s[l["speaker"]])
                srt.append(f"{n}\n{ts(lt)} --> {ts(lt + d)}\n{name}: {l['text']}\n"); n += 1; lt += d
        parts.append(norm); t += dur
    (work / "list.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    (work / "subs.srt").write_text("\n".join(srt))
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "list.txt"),
        "-vf", f"subtitles={work / 'subs.srt'}:force_style='FontSize=18,Outline=2,MarginV=18'",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5", "-movflags", "+faststart", out_path])
    print(f"assembled {len(parts)}/{len(sp['shots'])} shots, {t:.1f}s -> {out_path}")


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    if cmd == "refs": refs(*a)
    elif cmd == "push": push(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 0, int(a[4]) if len(a) > 4 else 1, a[5] if len(a) > 5 else "")
    elif cmd == "wait": wait(a[:-1], int(a[-1]))
    elif cmd == "fetch": fetch(*a)
    elif cmd == "dataset": dataset(*a)
    elif cmd == "assemble": assemble(*a)
