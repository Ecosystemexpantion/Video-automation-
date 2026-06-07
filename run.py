#!/usr/bin/env python3
import argparse
import os
import sys
import traceback

from database.supabase_client import get_next_topic, mark_topic_used, log_post, seed_topics
from pipeline.script_generator import generate_script
from pipeline.voice_generator import generate_voiceover
from pipeline.footage_fetcher import fetch_background_footage
from pipeline.video_assembler import assemble_video
from platforms.youtube_uploader import upload_short
from platforms.instagram_uploader import upload_reel
from platforms.facebook_poster import post_video
from templates.video_topics import TOPICS, get_pexels_keywords


def run_pipeline(dry_run: bool = False, platforms: list[str] = None):
    if platforms is None:
        platforms = ["youtube", "instagram", "facebook"]

    print("\n=== Davis Video Pipeline Starting ===")

    topic_row = get_next_topic()
    if not topic_row:
        print("[WARN] No topics in DB. Seeding topics...")
        seed_topics(TOPICS)
        topic_row = get_next_topic()

    topic = topic_row["topic"]
    topic_id = topic_row["id"]
    print(f"[1/6] Topic: {topic}")

    if dry_run:
        print(f"[DRY RUN] Would generate script, voice, footage, video, and post to: {platforms}")
        return

    print("[2/6] Generating script with Gemini...")
    script = generate_script(topic)
    mark_topic_used(topic_id)

    print("[3/6] Generating voiceover with Edge TTS...")
    audio_path = generate_voiceover(script["full_script"])

    keywords = get_pexels_keywords(topic)
    print(f"[4/6] Fetching background footage (keywords: {keywords[0]})...")
    footage_path = fetch_background_footage(keywords[0])

    print("[5/6] Assembling video...")
    video_path = assemble_video(
        footage_path=footage_path,
        audio_path=audio_path,
        title=script["title"],
        full_script=script["full_script"],
    )
    print(f"  Video saved: {video_path}")

    print("[6/6] Uploading to platforms...")

    for platform in platforms:
        try:
            if platform == "youtube":
                url = upload_short(
                    video_path=video_path,
                    title=script["title"],
                    description=script["description"],
                    hashtags=script["hashtags"],
                    topic=topic,
                )
                log_post("youtube", topic, script["title"], video_url=url, status="success")
                print(f"  [YouTube] Uploaded: {url}")

            elif platform == "instagram":
                url = upload_reel(
                    video_path=video_path,
                    caption=f"{script['title']}\n\n{script['description']}",
                    hashtags=script["hashtags"],
                )
                log_post("instagram", topic, script["title"], video_url=url, status="success")
                print(f"  [Instagram] Uploaded: {url}")

            elif platform == "facebook":
                url = post_video(
                    video_path=video_path,
                    title=script["title"],
                    description=script["description"],
                    hashtags=script["hashtags"],
                )
                log_post("facebook", topic, script["title"], video_url=url, status="success")
                print(f"  [Facebook] Uploaded: {url}")

        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"  [{platform.upper()}] FAILED: {e}")
            log_post(platform, topic, script.get("title", topic), status="failed", error=str(e))

    _cleanup_tmp()
    print("\n=== Pipeline Complete ===\n")


def _cleanup_tmp():
    import glob
    for f in glob.glob("tmp/*.mp4") + glob.glob("tmp/*.mp3") + glob.glob("tmp/*.m4a"):
        try:
            os.remove(f)
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Davis Video Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument(
        "--platform",
        choices=["youtube", "instagram", "facebook", "all"],
        default="all",
        help="Which platform to post to",
    )
    args = parser.parse_args()

    selected = None if args.platform == "all" else [args.platform]
    run_pipeline(dry_run=args.dry_run, platforms=selected)
