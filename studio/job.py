#!/usr/bin/env python3
"""
Runs one Davis Studio job end to end and reports progress to the app.

Modes:
  replicate  analyse an uploaded reference video and recreate it
  topic      make a new video from a topic
  remix      make a fresh variation of an earlier job
"""

import argparse
import os
import sys
import time
import traceback

from studio import store


def _fail_message(e: Exception) -> str:
    text = str(e).strip() or e.__class__.__name__
    if "credit balance" in text or "billing" in text.lower():
        return "The Claude API key has no credit left. Add credit or update ANTHROPIC_API_KEY in the repo secrets."
    if "authentication_error" in text or "invalid x-api-key" in text:
        return "The Claude API key in the repo secrets is invalid. Update ANTHROPIC_API_KEY."
    return text[:400]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--mode", choices=["replicate", "topic", "remix"], required=True)
    parser.add_argument("--topic", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--source-job", default="")
    args = parser.parse_args()

    work_dir = os.path.abspath(os.path.join("tmp", args.job_id))
    os.makedirs(work_dir, exist_ok=True)

    job = store.read_json(f"jobs/{args.job_id}.json") or {}
    job.update({
        "id": args.job_id,
        "created_at": job.get("created_at") or int(time.time()),
        "mode": args.mode,
        "topic": args.topic or job.get("topic") or "",
        "notes": args.notes,
        "voice": args.voice,
        "source_job": args.source_job,
        "title": job.get("title") or (args.topic[:60] if args.topic else "New video"),
        "error": None,
        "video_url": None,
        "thumb_url": None,
        "run_url": "{}/{}/actions/runs/{}".format(
            os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
            os.environ.get("GITHUB_REPOSITORY", ""),
            os.environ.get("GITHUB_RUN_ID", ""),
        ),
    })

    def progress(step: str, pct: int, status: str = "running"):
        print(f"[{pct:3d}%] {step}")
        job.update({"status": status, "step": step, "progress": pct})
        store.save_job(job)

    try:
        progress("Starting", 5)

        # Imported here so a missing dependency is reported to the app as a job error.
        from studio import analyze, blueprint, render

        if args.mode == "replicate":
            progress("Fetching your reference video", 10)
            reference_path = store.download_reference(args.job_id, os.path.join(work_dir, "reference"))

            progress("Studying the reference: scenes, frames and speech", 18)
            analysis = analyze.analyze_reference(reference_path, work_dir)
            job["reference"] = {
                "duration": analysis["duration"],
                "width": analysis["width"],
                "height": analysis["height"],
                "scene_count": len(analysis["scene_starts"]),
                "transcript": " ".join(s["text"] for s in analysis["transcript"])[:3000],
            }

            progress("Claude is designing the replication blueprint", 30)
            bp = blueprint.from_reference(analysis, args.notes)
            store.delete_reference(args.job_id)

        elif args.mode == "remix":
            source = store.read_json(f"jobs/{args.source_job}.json")
            if not source or not source.get("blueprint"):
                raise RuntimeError("The original video's blueprint could not be found")
            job["reference"] = source.get("reference")
            progress("Claude is writing a fresh version", 30)
            bp = blueprint.remix(source["blueprint"], args.notes)

        else:
            if not args.topic.strip():
                raise RuntimeError("No topic was given")
            progress("Claude is designing the video", 30)
            bp = blueprint.from_topic(args.topic, args.notes)

        job["blueprint"] = bp
        job["title"] = bp["title"]
        job["topic"] = bp["topic"]
        progress("Blueprint ready", 40)

        result = render.render(bp, args.voice, work_dir, on_progress=progress)

        progress("Publishing the finished video", 92)
        job["duration"] = result["duration"]
        job["video_url"] = store.upload_to_release(result["video"], f"{args.job_id}.mp4")
        if result["thumb"]:
            job["thumb_url"] = store.upload_to_release(result["thumb"], f"{args.job_id}.jpg")

        progress("Done", 100, status="done")

    except Exception as e:
        traceback.print_exc()
        job.update({"status": "failed", "error": _fail_message(e)})
        try:
            store.save_job(job)
        except Exception:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
