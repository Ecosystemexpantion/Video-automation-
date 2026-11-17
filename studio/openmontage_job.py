#!/usr/bin/env python3
"""
Runs one OpenMontage production unattended: Claude Code drives OpenMontage's
pipelines in ./OpenMontage, then the final render is published for the app.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import threading
import time
import traceback

from studio import store

OM_DIR = os.path.abspath("OpenMontage")

PROMPT = """You are running OpenMontage fully unattended in a cloud job for the owner of this system.
The owner has pre-authorized the entire production run. As your first pipeline action, record that
as a decision_log entry with category "approval_policy" (full-run pre-authorization from the owner),
then proceed through every gate yourself: choose the strongest option at each creative decision,
log it, and keep going. Never end your turn waiting for approval and never ask questions.

Brief from the owner:
{brief}
{reference}
Delivery requirements:
- Vertical 9:16 short-form video (TikTok / Reels / Shorts) unless the brief says otherwise.
- Use only tools that are actually available in this environment. No paid generation APIs are configured;
  PEXELS_API_KEY is available for free stock footage. Prefer real motion footage over animated stills.
- Natural narration and word-level captions.
- Finish with projects/<project>/renders/final.mp4 that passes OpenMontage's post-render self-review.
- If a preferred path is blocked, pick the best available alternative, log the decision, and continue.

When the render is done, reply with one short paragraph: the title, the pipeline used, and what the video shows."""


def _latest_render():
    files = glob.glob(os.path.join(OM_DIR, "projects", "*", "renders", "final*.mp4"))
    files += glob.glob(os.path.join(OM_DIR, "projects", "*", "renders", "*.mp4"))
    files = [f for f in files if os.path.getsize(f) > 0]
    return max(files, key=os.path.getmtime) if files else None


def _stage_hint():
    """Best-effort current stage from OpenMontage checkpoint files."""
    best = None
    for path in glob.glob(os.path.join(OM_DIR, "projects", "*", "**", "*checkpoint*.json"), recursive=True):
        try:
            mtime = os.path.getmtime(path)
            data = json.load(open(path))
            stage = data.get("stage") or data.get("current_stage")
            if stage and (best is None or mtime > best[0]):
                best = (mtime, f"{stage} ({data.get('status', '')})".strip())
        except Exception:
            continue
    return best[1] if best else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--reference", default="")
    args = p.parse_args()

    job = store.read_json(f"jobs/{args.job_id}.json") or {}
    job.update({
        "id": args.job_id,
        "created_at": job.get("created_at") or int(time.time()),
        "mode": "openmontage",
        "topic": args.brief[:300],
        "title": job.get("title") or args.brief[:60],
        "error": None, "video_url": None, "thumb_url": None,
        "run_url": "{}/{}/actions/runs/{}".format(
            os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
            os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", "")),
    })

    def progress(step, pct, status="running"):
        print(f"[{pct:3d}%] {step}", flush=True)
        job.update({"status": status, "step": step, "progress": pct})
        store.save_job(job)

    try:
        progress("OpenMontage is planning the video", 10)
        reference = ""
        if args.reference:
            ref_dir = os.path.join(OM_DIR, "inputs")
            ref = store.download_reference(args.job_id, ref_dir)
            reference = f"\nReference video to study and build from (keep its pacing, hook and structure): {ref}\n"

        done = threading.Event()

        def heartbeat():
            pct = 15
            while not done.wait(90):
                pct = min(85, pct + 3)
                hint = _stage_hint()
                progress(f"OpenMontage: {hint}" if hint else "OpenMontage is producing the video", pct)

        threading.Thread(target=heartbeat, daemon=True).start()
        result = subprocess.run(
            ["claude", "-p", PROMPT.format(brief=args.brief, reference=reference),
             "--model", "opus", "--output-format", "json",
             "--dangerously-skip-permissions", "--max-turns", "400"],
            cwd=OM_DIR, capture_output=True, text=True, timeout=5 * 3600,
        )
        done.set()
        summary = ""
        try:
            data = json.loads(result.stdout)
            summary = str(data.get("result") or "")
            print("Claude Code:", summary[:2000])
            print("Cost (USD):", data.get("total_cost_usd"), "turns:", data.get("num_turns"))
        except json.JSONDecodeError:
            print(result.stdout[-4000:], result.stderr[-4000:])

        render = _latest_render()
        if not render:
            raise RuntimeError("OpenMontage finished without a rendered video. " + summary[:300])

        progress("Publishing the finished video", 92)
        job["summary"] = summary[:1500]
        job["video_url"] = store.upload_to_release(render, f"{args.job_id}.mp4")
        thumb = os.path.join(os.path.dirname(render), "thumb.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", render,
                        "-frames:v", "1", "-vf", "scale=360:-2", thumb])
        if os.path.exists(thumb):
            job["thumb_url"] = store.upload_to_release(thumb, f"{args.job_id}.jpg")
        progress("Done", 100, status="done")
    except Exception as e:
        traceback.print_exc()
        job.update({"status": "failed", "error": str(e)[:400]})
        try:
            store.save_job(job)
        except Exception:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
