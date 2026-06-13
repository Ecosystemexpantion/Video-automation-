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

TITLE_FONT_SIZE = 56
CAPTION_FONT_SIZE = 62
CAPTION_YELLOW = (255, 222, 33)
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
        # Center each line horizontally within the image
        line_w = draw.textlength(line, font=font)
        x = (img_w - line_w) // 2
        y = padding + i * line_h
        # Thick outline for readability over any footage
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, -3), (0, 3), (-3, 0), (3, 0)]:
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(*color, 255))

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
    # Semi-transparent dark gradient (darker at top/bottom) so text pops
    # while the footage stays clearly visible in the middle.
    alpha = np.zeros((height, width), dtype=np.float64)
    for y in range(height):
        t = y / height
        if t < 0.25:
            a = 0.45 * (1 - t / 0.25)
        elif t > 0.7:
            a = 0.55 * ((t - 0.7) / 0.3)
        else:
            a = 0.0
        alpha[y, :] = a
    black = np.zeros((height, width, 3), dtype=np.uint8)
    clip = ImageClip(black).set_duration(duration)
    mask = ImageClip(alpha, ismask=True).set_duration(duration)
    return clip.set_mask(mask)


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


def _fit_to_frame(clip):
    """Resize + crop a clip to fill the 1080x1920 vertical frame."""
    raw_ratio = clip.w / clip.h
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    if raw_ratio > target_ratio:
        clip = clip.resize(height=VIDEO_HEIGHT)
        clip = crop(clip, width=VIDEO_WIDTH, x_center=clip.w / 2)
    else:
        clip = clip.resize(width=VIDEO_WIDTH)
        clip = crop(clip, height=VIDEO_HEIGHT, y_center=clip.h / 2)
    return clip


def _build_background(footage_paths: list[str], duration: float):
    """Cut between multiple footage clips so the visuals keep changing."""
    n = len(footage_paths)
    seg_dur = duration / n
    segments = []
    for path in footage_paths:
        raw = VideoFileClip(path)
        if raw.duration < seg_dur:
            loops = int(seg_dur / raw.duration) + 1
            raw = concatenate_videoclips([raw] * loops)
        segments.append(_fit_to_frame(raw.subclip(0, seg_dur)))
    return concatenate_videoclips(segments).subclip(0, duration)


def assemble_video(
    footage_path,
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

    footage_paths = footage_path if isinstance(footage_path, list) else [footage_path]
    raw_video = _build_background(footage_paths, duration)

    gradient = _make_gradient_overlay(VIDEO_WIDTH, VIDEO_HEIGHT, duration)

    title_clip = _text_to_clip(
        title, TITLE_FONT_SIZE,
        duration=min(5.0, duration),
        position=("center", 100)
    )

    captions = split_into_captions(full_script, words_per_caption=4)
    timed_captions = estimate_timings(captions, duration)
    caption_clips = []
    for i, (start, end, text) in enumerate(timed_captions):
        # Alternate white / yellow like popular Shorts caption styles
        color = CAPTION_YELLOW if i % 2 else (255, 255, 255)
        clip = _text_to_clip(
            text.upper(), CAPTION_FONT_SIZE,
            duration=end - start,
            position=("center", int(VIDEO_HEIGHT * 0.62)),
            color=color,
        ).set_start(start)
        caption_clips.append(clip)

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
