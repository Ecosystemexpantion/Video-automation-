"""Report drama progress to the Davis Studio app (app-data branch).
Usage: JOB_ID=... job_status.py <status> <pct> <step> [video_path]
Does nothing when job_id is empty (runs started outside the app)."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import store

job_id = os.environ.get("JOB_ID", "")
status, pct, step = sys.argv[1:4]
video = sys.argv[4] if len(sys.argv) > 4 else ""
if not job_id:
    sys.exit(0)
job = store.read_json(f"jobs/{job_id}.json") or {"id": job_id, "created_at": int(time.time()), "mode": "drama"}
job.update({"id": job_id, "mode": "drama", "status": status, "progress": int(pct), "step": step,
            "run_url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY','')}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"})
if os.environ.get("JOB_TITLE"):
    job["title"] = os.environ["JOB_TITLE"][:60]
if status == "failed":
    job["error"] = step
if video and os.path.exists(video):
    thumb = video + ".jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "5", "-i", video, "-frames:v", "1", "-vf", "scale=360:-2", thumb])
    job["video_url"] = store.upload_to_release(video, f"{job_id}.mp4")
    if os.path.exists(thumb):
        job["thumb_url"] = store.upload_to_release(thumb, f"{job_id}.jpg")
store.save_job(job)
print("job", job_id, status, pct, step)
