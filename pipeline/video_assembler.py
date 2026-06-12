import os
import numpy as np
from PIL import Image as PILImage
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, ImageClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop
from pipeline.caption_generator import split_into_captions, estimate_timings
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, WHATSAPP_INVITE_LINK

OUTPUT_DIR = "tmp"

TITLE_FONT_SIZE = 50
CAPTION_FONT_SIZE = 46
CTA_FONT_SIZE = 34
BRAND_FONT_SIZE = 26
FONT = "DejaVu-Sans-Bold"
TEXT_COLOR = "white"
SHADOW_COLOR = "black"
CTA_GREEN = (37, 211, 102)


def _make_text_clip(text: str, fontsize: int, duration: float,
                    position, color: str = TEXT_COLOR,
                    stroke_width: int = 2) -> TextClip:
    return (
        TextClip(
            text,
            fontsize=fontsize,
            color=color,
            font=FONT,
            method="caption",
            size=(VIDEO_WIDTH - 80, None),
            align="center",
            stroke_color=SHADOW_COLOR,
            stroke_width=stroke_width,
        )
        .set_duration(duration)
        .set_position(position)
    )


def _make_gradient_overlay(width: int, height: int, duration: float) -> ImageClip:
    """Bottom-heavy gradient overlay — transparent at top, 75% black at bottom."""
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        t = y / height
        if t < 0.3:
            alpha = int(80 * (t / 0.3))
        elif t < 0.6:
            alpha = 80
        else:
            alpha = int(80 + 120 * ((t - 0.6) / 0.4))
        arr[y, :, :3] = 0
        arr[y, :, 3] = min(alpha, 200)

    img = PILImage.fromarray(arr, "RGBA").convert("RGB")
    return ImageClip(np.array(img)).set_duration(duration)


def _make_cta_box(duration: float) -> CompositeVideoClip:
    """Green pill background + white text for the WhatsApp CTA."""
    box_w = VIDEO_WIDTH - 60
    box_h = 90

    bg = (
        ColorClip(size=(box_w, box_h), color=CTA_GREEN)
        .set_opacity(0.92)
        .set_duration(duration)
        .set_position(("center", VIDEO_HEIGHT - 230))
    )

    short_link = WHATSAPP_INVITE_LINK.replace("https://", "").replace("chat.whatsapp.com/", "wa.me/")
    label = TextClip(
        f"JOIN FREE  {short_link}",
        fontsize=CTA_FONT_SIZE,
        color="white",
        font=FONT,
        method="caption",
        size=(box_w - 40, None),
        align="center",
        stroke_color=(0, 80, 40),
        stroke_width=1,
    ).set_duration(duration).set_position(("center", VIDEO_HEIGHT - 215))

    return [bg, label]


def assemble_video(
    footage_path: str,
    audio_path: str,
    title: str,
    full_script: str,
    output_path: str = None,
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "output.mp4")

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    raw_video = VideoFileClip(footage_path)
    if raw_video.duration < duration:
        loops = int(duration / raw_video.duration) + 1
        raw_video = concatenate_videoclips([raw_video] * loops)
    raw_video = raw_video.subclip(0, duration)

    raw_ratio = raw_video.w / raw_video.h
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    if raw_ratio > target_ratio:
        raw_video = raw_video.resize(height=VIDEO_HEIGHT)
        raw_video = crop(raw_video, width=VIDEO_WIDTH, x_center=raw_video.w / 2)
    else:
        raw_video = raw_video.resize(width=VIDEO_WIDTH)
        raw_video = crop(raw_video, height=VIDEO_HEIGHT, y_center=raw_video.h / 2)

    gradient = _make_gradient_overlay(VIDEO_WIDTH, VIDEO_HEIGHT, duration)

    title_clip = _make_text_clip(title, TITLE_FONT_SIZE, duration=min(5.0, duration), position=("center", 100))

    captions = split_into_captions(full_script, words_per_caption=6)
    timed_captions = estimate_timings(captions, duration)
    caption_clips = [
        _make_text_clip(text, CAPTION_FONT_SIZE, duration=end - start, position=("center", "center"))
        .set_start(start)
        for start, end, text in timed_captions
    ]

    cta_start = max(0, duration - 8)
    cta_duration = duration - cta_start
    cta_clips = [
        c.set_start(cta_start) for c in _make_cta_box(cta_duration)
    ]

    brand_clip = _make_text_clip(
        "AI Automation Tips",
        BRAND_FONT_SIZE,
        duration=duration,
        position=("center", VIDEO_HEIGHT - 50),
        color="#AAAAAA",
        stroke_width=1,
    )

    all_clips = [raw_video, gradient, title_clip] + caption_clips + cta_clips + [brand_clip]
    final = CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio)

    final.write_videofile(
        output_path,
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="tmp/temp_audio.m4a",
        remove_temp=True,
        preset="fast",
        ffmpeg_params=["-profile:v", "baseline", "-level", "3.0"],
        logger=None,
    )

    return output_path
