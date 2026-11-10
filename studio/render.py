"""
Renders a blueprint into a finished 1080x1920 video:
one voice-over line, one stock clip and synced captions per scene.
"""

import os
import subprocess

import numpy as np
import requests
import soundfile as sf
from PIL import Image as PILImage, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop

W, H, FPS = 1080, 1920, 30
SAMPLE_RATE = 24000
SCENE_PAUSE = 0.15  # seconds of silence after each scene's line
CAPTION_FONT = 68
HEADLINE_FONT = 50

VOICES = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_adam", "am_fenrir",
          "bf_emma", "bm_george"]

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


# ---------- voice ----------

def _gtts_samples(text: str, work_dir: str, index: int) -> np.ndarray:
    from gtts import gTTS

    mp3 = os.path.join(work_dir, f"line_{index}.mp3")
    wav = os.path.join(work_dir, f"line_{index}.wav")
    gTTS(text=text, lang="en", slow=False).save(mp3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                    "-ar", str(SAMPLE_RATE), "-ac", "1", wav], check=True)
    samples, _ = sf.read(wav, dtype="float32")
    return samples


def synthesize(scenes: list, voice: str, work_dir: str) -> tuple:
    """Speak every scene. Returns (wav_path, [speech_seconds per scene])."""
    kokoro = None
    try:
        from kokoro_onnx import Kokoro

        kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        if voice not in VOICES:
            voice = "af_heart"
    except Exception as e:
        print(f"  [voice] Kokoro unavailable ({e}); using fallback voice")

    pause = np.zeros(int(SAMPLE_RATE * SCENE_PAUSE), dtype=np.float32)
    parts, speech_durations = [], []
    for i, scene in enumerate(scenes):
        if kokoro is not None:
            samples, rate = kokoro.create(scene["narration"], voice=voice, speed=1.0, lang="en-us")
            samples = np.asarray(samples, dtype=np.float32)
            if rate != SAMPLE_RATE:
                raise RuntimeError(f"Unexpected voice sample rate {rate}")
        else:
            samples = _gtts_samples(scene["narration"], work_dir, i)
        speech_durations.append(len(samples) / SAMPLE_RATE)
        parts.extend([samples, pause])

    wav_path = os.path.join(work_dir, "voice.wav")
    sf.write(wav_path, np.concatenate(parts), SAMPLE_RATE)
    return wav_path, speech_durations


# ---------- footage ----------

def _search_pexels(query: str) -> list:
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": os.environ["PEXELS_API_KEY"]},
        params={"query": query, "orientation": "portrait", "per_page": 15},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("videos", [])


def _best_file(video: dict):
    files = [f for f in video.get("video_files", [])
             if f.get("width") and f.get("height") and f["height"] >= f["width"]]
    if not files:
        return None
    # Closest to 1080 wide without going far below it.
    files.sort(key=lambda f: (f["width"] < 720, abs(f["width"] - 1080)))
    return files[0]


def fetch_clip(query: str, min_seconds: float, used_ids: set, cache_dir: str):
    """Download a portrait stock clip for a scene. Returns a path or None."""
    os.makedirs(cache_dir, exist_ok=True)
    attempts = [query, " ".join(query.split()[:2]), query.split()[0] if query.split() else "", "technology"]
    for q in dict.fromkeys(a for a in attempts if a):
        try:
            videos = _search_pexels(q)
        except Exception as e:
            print(f"  [footage] Search failed for '{q}': {e}")
            continue
        # Prefer clips long enough to cover the scene without looping.
        videos.sort(key=lambda v: v.get("duration", 0) < min_seconds)
        for video in videos:
            if video["id"] in used_ids:
                continue
            chosen = _best_file(video)
            if not chosen:
                continue
            path = os.path.join(cache_dir, f"{video['id']}.mp4")
            try:
                if not os.path.exists(path):
                    with requests.get(chosen["link"], stream=True, timeout=120) as r:
                        r.raise_for_status()
                        with open(path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1 << 16):
                                f.write(chunk)
                used_ids.add(video["id"])
                return path
            except Exception as e:
                print(f"  [footage] Download failed for {video['id']}: {e}")
    return None


# ---------- text ----------

def _font(size: int):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_width: int) -> list:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _text_image(text: str, size: int, color: tuple, box: bool = False) -> np.ndarray:
    font = _font(size)
    max_width = W - 140
    probe = ImageDraw.Draw(PILImage.new("RGBA", (10, 10)))
    lines = _wrap(probe, text, font, max_width)

    pad = 28
    line_h = int(size * 1.25)
    img_w = W - 80
    img_h = line_h * len(lines) + pad * 2
    img = PILImage.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if box:
        draw.rounded_rectangle([0, 0, img_w - 1, img_h - 1], radius=28, fill=(0, 0, 0, 165))

    outline = max(3, size // 14)
    for i, line in enumerate(lines):
        x = (img_w - draw.textlength(line, font=font)) / 2
        y = pad + i * line_h
        draw.text((x, y), line, font=font, fill=(*color, 255),
                  stroke_width=outline, stroke_fill=(0, 0, 0, 255))
    return np.array(img)


def _text_clip(text, size, color, start, duration, y_center, box=False):
    arr = _text_image(text, size, color, box)
    y = int(y_center - arr.shape[0] / 2)
    return (ImageClip(arr).set_start(start).set_duration(duration)
            .set_position(((W - arr.shape[1]) // 2, max(20, y))))


def _hex_to_rgb(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _caption_clips(scenes, speech_durations, scene_starts, style) -> list:
    y_center = {"top": 0.24, "center": 0.50, "bottom": 0.72}[style["position"]] * H
    highlight = _hex_to_rgb(style["color"])
    per = style["words_per_caption"]

    clips, n = [], 0
    for scene, speech, scene_start in zip(scenes, speech_durations, scene_starts):
        words = scene["narration"].split()
        chunks = [" ".join(words[i:i + per]) for i in range(0, len(words), per)]
        total_chars = sum(len(c) for c in chunks) or 1
        t = scene_start
        for chunk in chunks:
            duration = speech * len(chunk) / total_chars
            text = chunk.upper() if style["uppercase"] else chunk
            color = highlight if n % 2 else (255, 255, 255)
            clips.append(_text_clip(text, CAPTION_FONT, color, t, duration, y_center))
            t += duration
            n += 1
    return clips


# ---------- assembly ----------

def _fit(clip):
    if clip.w / clip.h > W / H:
        clip = clip.resize(height=H)
        return crop(clip, width=W, x_center=clip.w / 2)
    clip = clip.resize(width=W)
    return crop(clip, height=H, y_center=clip.h / 2)


def _scene_background(path, duration):
    if path is None:
        return ColorClip(size=(W, H), color=(12, 18, 24)).set_duration(duration)
    clip = VideoFileClip(path, audio=False)
    if clip.duration < duration:
        clip = concatenate_videoclips([clip] * (int(duration / clip.duration) + 1))
    return _fit(clip.subclip(0, duration))


def _shade(duration):
    """Soft dark fade at the top and bottom so text stays readable."""
    alpha = np.zeros((H, W), dtype=np.float64)
    for y in range(H):
        t = y / H
        if t < 0.25:
            alpha[y, :] = 0.40 * (1 - t / 0.25)
        elif t > 0.70:
            alpha[y, :] = 0.50 * ((t - 0.70) / 0.30)
    shade = ImageClip(np.zeros((H, W, 3), dtype=np.uint8)).set_duration(duration)
    return shade.set_mask(ImageClip(alpha, ismask=True).set_duration(duration))


def render(blueprint: dict, voice: str, work_dir: str, on_progress=lambda step, pct: None) -> dict:
    """Build the video. Returns {video, thumb, duration}."""
    os.makedirs(work_dir, exist_ok=True)
    scenes = blueprint["scenes"]

    on_progress("Recording the voice-over", 45)
    wav_path, speech = synthesize(scenes, voice, work_dir)
    scene_durations = [s + SCENE_PAUSE for s in speech]
    scene_starts = [sum(scene_durations[:i]) for i in range(len(scenes))]
    total = sum(scene_durations)

    on_progress("Finding footage for each scene", 55)
    used, backgrounds = set(), []
    for scene, duration in zip(scenes, scene_durations):
        path = fetch_clip(scene["visual_query"], duration, used, os.path.join(work_dir, "clips"))
        if path is None:
            print(f"  [footage] No clip for '{scene['visual_query']}', using plain background")
        backgrounds.append(_scene_background(path, duration))

    on_progress("Editing the video", 70)
    layers = [concatenate_videoclips(backgrounds), _shade(total)]
    layers += _caption_clips(scenes, speech, scene_starts, blueprint["caption_style"])

    headline_y = 0.13 * H if blueprint["caption_style"]["position"] != "top" else 0.86 * H
    for scene, start, duration in zip(scenes, scene_starts, scene_durations):
        if scene["on_screen_text"]:
            layers.append(_text_clip(scene["on_screen_text"], HEADLINE_FONT, (255, 255, 255),
                                     start, duration, headline_y, box=True))

    audio = AudioFileClip(wav_path)
    final = CompositeVideoClip(layers, size=(W, H)).set_duration(total).set_audio(audio)

    video_path = os.path.join(work_dir, "output.mp4")
    final.write_videofile(
        video_path, fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k",
        preset="medium", threads=4,
        temp_audiofile=os.path.join(work_dir, "temp_audio.m4a"), remove_temp=True,
        ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None,
    )

    thumb_path = os.path.join(work_dir, "thumb.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", video_path,
                    "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", thumb_path])
    return {
        "video": video_path,
        "thumb": thumb_path if os.path.exists(thumb_path) else None,
        "duration": round(total, 1),
    }
