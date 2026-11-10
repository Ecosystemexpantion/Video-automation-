"""
Reference video analysis: duration, scene cuts, representative frames and a
timestamped transcript. Everything runs locally with ffmpeg and Whisper.
"""

import base64
import json
import os
import re
import subprocess

MAX_FRAMES = 14


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(video_path: str) -> dict:
    out = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json", video_path,
    ])
    data = json.loads(out.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    duration = float((data.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("Could not read the reference video (unsupported or corrupt file)")
    return {
        "duration": round(duration, 2),
        "width": stream.get("width"),
        "height": stream.get("height"),
    }


def detect_scenes(video_path: str, duration: float) -> list:
    """Return scene start times (seconds), always beginning with 0."""
    out = _run([
        "ffmpeg", "-hide_banner", "-i", video_path,
        "-vf", "select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-",
    ])
    cuts = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", out.stderr)]

    starts = [0.0]
    for t in cuts:
        # Ignore flashes: scenes shorter than 0.6s are merged into the previous one.
        if t - starts[-1] >= 0.6 and duration - t >= 0.4:
            starts.append(round(t, 2))
    return starts


def _frame_times(scene_starts: list, duration: float) -> list:
    bounds = scene_starts + [duration]
    mids = [(bounds[i] + bounds[i + 1]) / 2 for i in range(len(scene_starts))]

    if len(mids) > MAX_FRAMES:
        step = len(mids) / MAX_FRAMES
        mids = [mids[int(i * step)] for i in range(MAX_FRAMES)]
    elif len(mids) < 6:
        # Few or no cuts (e.g. a talking head): sample evenly instead.
        mids = [duration * (2 * i + 1) / 16 for i in range(8)]
    return [round(t, 2) for t in mids]


def extract_frames(video_path: str, scene_starts: list, duration: float, out_dir: str) -> list:
    """Save one JPEG per sampled moment. Returns [{time, path, b64}]."""
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    for i, t in enumerate(_frame_times(scene_starts, duration)):
        path = os.path.join(out_dir, f"frame_{i:02d}.jpg")
        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(t), "-i", video_path, "-frames:v", "1",
            "-vf", "scale='min(640,iw)':-2", "-q:v", "4", path,
        ])
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                frames.append({
                    "time": t,
                    "path": path,
                    "b64": base64.b64encode(f.read()).decode(),
                })
    if not frames:
        raise RuntimeError("Could not extract any frames from the reference video")
    return frames


def transcribe(video_path: str) -> list:
    """Return [{start, end, text}] for the spoken audio; [] if silent or unavailable."""
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(video_path, vad_filter=True)
        return [
            {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments if s.text.strip()
        ]
    except Exception as e:
        print(f"  [analyze] Transcription unavailable: {e}")
        return []


def analyze_reference(video_path: str, work_dir: str) -> dict:
    info = probe(video_path)
    scene_starts = detect_scenes(video_path, info["duration"])
    frames = extract_frames(video_path, scene_starts, info["duration"], os.path.join(work_dir, "frames"))
    transcript = transcribe(video_path)
    return {
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
        "scene_starts": scene_starts,
        "frames": frames,
        "transcript": transcript,
    }
