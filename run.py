#!/usr/bin/env python3
import argparse
import os
import sys
import time
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


def _upload_with_retry(fn, *args, retries=2, **kwargs):
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except RuntimeError as e:
            # Credential/config errors — no point retrying
            raise
        except Exception as e:
            if attempt < retries:
                wait = 2 ** attempt
                print(f"    Retry {attempt + 1}/{retries} in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def run_pipeline(dry_run: bool = False, platforms: list[str] = None):
    if platforms is None:
        platforms = ["youtube", "instagram", "facebook"]

    print("\n" + "=" * 45)
    print("  Davis Video Pipeline")
    print("=" * 45)

    topic_row = get_next_topic()
    if not topic_row:
        print("[WARN] No topics in DB — seeding...")
        seed_topics(TOPICS)
        topic_row = get_next_topic()

    topic = topic_row["topic"]
    topic_id = topic_row["id"]
    print(f"\n[1/6] Topic selected:\n      {topic}")

    if dry_run:
        print(f"\n[DRY RUN] Would generate script, voice, footage, video")
        print(f"[DRY RUN] Would post to: {', '.join(platforms)}")
        print("\n[DRY RUN] Pipeline test complete — no real actions taken.\n")
        return

    print("\n[2/6] Generating script with Claude...")
    script = generate_script(topic)
    mark_topic_used(topic_id)
    print(f"      Title: {script['title']}")

    print("\n[3/6] Generating voiceover...")
    audio_path = generate_voiceover(script["full_script"])
    print(f"      Saved: {audio_path}")

    keywords = get_pexels_keywords(topic)
    print(f"\n[4/6] Fetching background footage ({keywords[0]})...")
    footage_path = fetch_background_footage(keywords[0])
    print(f"      Saved: {footage_path}")

    print("\n[5/6] Assembling video...")
    video_path = assemble_video(
        footage_path=footage_path,
        audio_path=audio_path,
        title=script["title"],
        full_script=script["full_script"],
    )
    print(f"      Saved: {video_path}")

    print("\n[6/6] Uploading to platforms...")
    results = {}
    real_errors = []

    for platform in platforms:
        try:
            if platform == "youtube":
                url = _upload_with_retry(
                    upload_short,
                    video_path=video_path,
                    title=script["title"],
                    description=script["description"],
                    hashtags=script["hashtags"],
                    topic=topic,
                )
            elif platform == "instagram":
                url = _upload_with_retry(
                    upload_reel,
                    video_path=video_path,
                    caption=f"{script['title']}\n\n{script['description']}",
                    hashtags=script["hashtags"],
                )
            elif platform == "facebook":
                url = _upload_with_retry(
                    post_video,
                    video_path=video_path,
                    title=script["title"],
                    description=script["description"],
                    hashtags=script["hashtags"],
                )
            else:
                continue

            log_post(platform, topic, script["title"], video_url=url, status="success")
            results[platform] = "success"
            print(f"      [{platform.upper()}] OK — {url}")

        except RuntimeError as e:
            msg = str(e)
            if "not configured" in msg or "skipping" in msg:
                print(f"      [{platform.upper()}] SKIPPED — {msg}")
                results[platform] = "skipped"
            else:
                log_post(platform, topic, script.get("title", topic), status="failed", error=msg)
                results[platform] = f"failed: {msg}"
                real_errors.append(f"{platform}: {msg}")
                print(f"      [{platform.upper()}] FAILED — {msg}")

        except Exception as e:
            msg = str(e)
            log_post(platform, topic, script.get("title", topic), status="failed", error=msg)
            results[platform] = f"failed: {msg}"
            real_errors.append(f"{platform}: {msg}")
            print(f"      [{platform.upper()}] FAILED — {msg}")

    successes = sum(1 for v in results.values() if v == "success")
    print(f"\n{'=' * 45}")
    print(f"  Pipeline complete — {successes}/{len(platforms)} platforms posted")
    print(f"{'=' * 45}\n")

    # Only fail the build if there were real (non-credential) errors
    if real_errors:
        sys.exit(1)


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
        help="Which platform to post to (default: all)",
    )
    args = parser.parse_args()

    selected = None if args.platform == "all" else [args.platform]
    run_pipeline(dry_run=args.dry_run, platforms=selected)
