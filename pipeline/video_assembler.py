import os
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop, resize
from pipeline.caption_generator import split_into_captions, estimate_timings
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, WHATSAPP_INVITE_LINK

OUTPUT_DIR = "tmp"

TITLE_FONT_SIZE = 52
CAPTION_FONT_SIZE = 44
CTA_FONT_SIZE = 38
FONT = "DejaVu-Sans-Bold"
TEXT_COLOR = "white"
SHADOW_COLOR = "black"
CAPTION_BG = (0, 0, 0, 160)


def _make_text_clip(text: str, fontsize: int, duration: float,
                    position: tuple, color: str = TEXT_COLOR) -> TextClip:
    clip = TextClip(
        text,
        fontsize=fontsize,
        color=color,
        font=FONT,
        method="caption",
        size=(VIDEO_WIDTH - 80, None),
        align="center",
        stroke_color=SHADOW_COLOR,
        stroke_width=2,
    ).set_duration(duration).set_position(position)
    return clip


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
        loops_needed = int(duration / raw_video.duration) + 1
        raw_video = concatenate_videoclips([raw_video] * loops_needed)

    raw_video = raw_video.subclip(0, duration)
    raw_video_ratio = raw_video.w / raw_video.h
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT

    if raw_video_ratio > target_ratio:
        raw_video = raw_video.resize(height=VIDEO_HEIGHT)
        x_center = raw_video.w / 2
        raw_video = crop(raw_video, width=VIDEO_WIDTH, x_center=x_center)
    else:
        raw_video = raw_video.resize(width=VIDEO_WIDTH)
        y_center = raw_video.h / 2
        raw_video = crop(raw_video, height=VIDEO_HEIGHT, y_center=y_center)

    dark_overlay = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0)
    ).set_opacity(0.45).set_duration(duration)

    title_clip = _make_text_clip(title, TITLE_FONT_SIZE, duration=4.0, position=("center", 80))

    captions = split_into_captions(full_script, words_per_caption=6)
    timed_captions = estimate_timings(captions, duration)
    caption_clips = []
    for start, end, text in timed_captions:
        clip = _make_text_clip(text, CAPTION_FONT_SIZE, duration=end - start, position=("center", "center"))
        clip = clip.set_start(start)
        caption_clips.append(clip)

    cta_start = max(0, duration - 7)
    cta_text = f"JOIN FREE: {WHATSAPP_INVITE_LINK}"
    cta_clip = _make_text_clip(
        cta_text, CTA_FONT_SIZE,
        duration=duration - cta_start,
        position=("center", VIDEO_HEIGHT - 200),
        color="#25D366"
    ).set_start(cta_start)

    branding = _make_text_clip(
        "AI Automation Tips", 30, duration=duration,
        position=("center", VIDEO_HEIGHT - 80),
        color="#AAAAAA"
    )

    all_clips = [raw_video, dark_overlay, title_clip] + caption_clips + [cta_clip, branding]
    final = CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    final = final.set_audio(audio)

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
