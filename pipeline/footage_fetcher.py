import os
import requests
import random
from config import PEXELS_API_KEY

PEXELS_API = "https://api.pexels.com/videos/search"
CACHE_DIR = "footage_cache"
PORTRAIT_MIN_RATIO = 0.4
PORTRAIT_MAX_RATIO = 0.7


def fetch_background_footage(search_query: str, min_duration: int = 30, max_duration: int = 60) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_key = search_query.replace(" ", "_").lower()
    cached = [f for f in os.listdir(CACHE_DIR) if f.startswith(cache_key)]
    if cached:
        return os.path.join(CACHE_DIR, random.choice(cached))

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": search_query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 15,
    }

    response = requests.get(PEXELS_API, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    videos = data.get("videos", [])
    if not videos:
        raise ValueError(f"No Pexels videos found for query: {search_query}")

    random.shuffle(videos)

    for video in videos:
        duration = video.get("duration", 0)
        if duration < min_duration:
            continue

        video_files = video.get("video_files", [])
        portrait_files = [
            f for f in video_files
            if f.get("width", 0) > 0 and
            PORTRAIT_MIN_RATIO <= (f.get("width", 1) / max(f.get("height", 1), 1)) <= PORTRAIT_MAX_RATIO and
            f.get("quality") in ("hd", "sd")
        ]

        if not portrait_files:
            portrait_files = [f for f in video_files if f.get("height", 0) >= f.get("width", 0)]

        if not portrait_files:
            continue

        portrait_files.sort(key=lambda f: f.get("width", 0) * f.get("height", 0), reverse=True)
        video_url = portrait_files[0]["link"]

        filename = f"{cache_key}_{video['id']}.mp4"
        filepath = os.path.join(CACHE_DIR, filename)

        with requests.get(video_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return filepath

    raise ValueError(f"No suitable portrait video found for: {search_query}")


if __name__ == "__main__":
    path = fetch_background_footage("artificial intelligence")
    print(f"Downloaded: {path}")
