import os
import textwrap
import numpy as np
from PIL import Image as PILImage, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    ColorClip, ImageClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop
from pipeline.caption_generator import split_into_captions, estimate_timings
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, WHATSAPP_INVITE_LINK

OUTPUT_DIR = "tmp"

TITLE_FONT_SIZE = 52
CAPTION_FONT_SIZE = 48
CTA_FONT_SIZE = 32
BRAND_FONT_SIZE = 26
CTA_GREEN = (37, 211, 102)


def _load_font(size: int):
    """Load DejaVu or fallback to default."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _text_to_clip(text: str, fontsize: int, duration: float,
                  position, color=(255, 255, 255),
                  max_width: int = VIDEO_WIDTH - 80,
                  bg_color=None, padding: int = 12) -> ImageClip:
    """Render text with PIL and return an ImageClip."""
    font = _load_font(fontsize)
    # Wrap text
    avg_char_w = fontsize * 0.6
    chars_per_line = max(1, int(max_width / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line) or [text]

    line_h = fontsize + 6
    img_h = line_h * len(lines) + padding * 2
    img_w = max_width + padding * 2

    img = PILImage.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_color:
        draw.rectangle([0, 0, img_w - 1, img_h - 1], fill=bg_color)

    for i, line in enumerate(lines):
        y = padding + i * line_h
        # Shadow
        draw.text((padding + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        # Text
        draw.text((padding, y), line, font=font, fill=(*color, 255))

    arr = np.array(img.convert("RGBA"))
    clip = ImageClip(arr, ismask=False)
    clip = clip.set_duration(duration)

    # Resolve position
    if isinstance(position, tuple):
        x, y = position
        if x == "center":
            x = (VIDEO_WIDTH - img_w) // 2
        if y == "center":
            y = (VIDEO_HEIGHT - img_h) // 2
        clip = clip.set_position((x, y))
    else:
        clip = clip.set_position(position)

    return clip


def _make_gradient_overlay(width: int, height: int, duration: float) -> ImageClip:
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        t = y / height
        if t < 0.3:
            alpha = int(80 * (t / 0.3))
        elif t < 0.6:
            alpha = 80
        else:
            alpha = int(80 + 120 * ((t - 0.6) / 0.4))
        arr[y, :, 3] = min(alpha, 200)
    img = PILImage.fromarray(arr, "RGBA").convert("RGB")
    return ImageClip(np.array(img)).set_duration(duration)


def _make_cta_clips(duration: float) -> list:
    box_w = VIDEO_WIDTH - 60
    box_h = 90
    box_y = VIDEO_HEIGHT - 230

    bg = (
        ColorClip(size=(box_w, box_h), color=CTA_GREEN)
        .set_opacity(0.92)
        .set_duration(duration)
        .set_position(((VIDEO_WIDTH - box_w) // 2, box_y))
    )

    short_link = WHATSAPP_INVITE_LINK.replace("https://", "").replace("chat.whatsapp.com/", "wa.me/")
    label = _text_to_clip(
        f"JOIN FREE  {short_link}",
        CTA_FONT_SIZE,
        duration,
        ("center", box_y + 15),
        color=(255, 255, 255),
        max_width=box_w - 40,
    )
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

    title_clip = _text_to_clip(
        title, TITLE_FONT_SIZE,
        duration=min(5.0, duration),
        position=("center", 100)
    )

    captions = split_into_captions(full_script, words_per_caption=6)
    timed_captions = estimate_timings(captions, duration)
    caption_clips = [
        _text_to_clip(text, CAPTION_FONT_SIZE, duration=end - start, position=("center", "center"))
        .set_start(start)
        for start, end, text in timed_captions
    ]

    cta_start = max(0, duration - 8)
    cta_duration = duration - cta_start
    cta_clips = [
        c.set_start(cta_start) for c in _make_cta_clips(cta_duration)
    ]

    brand_clip = _text_to_clip(
        "AI Automation Tips",
        BRAND_FONT_SIZE,
        duration=duration,
        position=("center", VIDEO_HEIGHT - 60),
        color=(170, 170, 170),
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
