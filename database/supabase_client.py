from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from datetime import datetime, timezone

_client = None

def get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def get_next_topic():
    db = get_client()
    result = (
        db.table("topics")
        .select("*")
        .order("used_count", desc=False)
        .order("used_at", desc=False, nullsfirst=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def mark_topic_used(topic_id: int):
    db = get_client()
    db.table("topics").update({
        "used_at": datetime.now(timezone.utc).isoformat(),
        "used_count": db.table("topics").select("used_count").eq("id", topic_id).execute().data[0]["used_count"] + 1
    }).eq("id", topic_id).execute()


def log_post(platform: str, topic: str, title: str, post_id: str = None,
             video_url: str = None, status: str = "success", error: str = None):
    db = get_client()
    db.table("posts").insert({
        "platform": platform,
        "topic": topic,
        "title": title,
        "post_id": post_id,
        "video_url": video_url,
        "status": status,
        "error_message": error,
    }).execute()


def get_todays_posts():
    db = get_client()
    today = datetime.now(timezone.utc).date().isoformat()
    result = (
        db.table("posts")
        .select("*")
        .gte("created_at", today)
        .execute()
    )
    return result.data or []


def get_recent_posts(limit: int = 10):
    db = get_client()
    result = (
        db.table("posts")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def seed_topics(topics: list[str]):
    db = get_client()
    rows = [{"topic": t, "used_count": 0} for t in topics]
    db.table("topics").upsert(rows, on_conflict="topic").execute()
