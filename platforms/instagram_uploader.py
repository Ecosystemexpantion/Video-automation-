import requests
import time
from config import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID, WHATSAPP_INVITE_LINK

GRAPH_API = "https://graph.facebook.com/v21.0"


def upload_reel(video_path: str, caption: str, hashtags: list[str]) -> str:
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        raise RuntimeError("Instagram not configured — skipping")
    tag_str = " ".join(f"#{h}" for h in hashtags)
    full_caption = (
        f"{caption}\n\n"
        f"🔥 Join our FREE WhatsApp community for daily AI money tips:\n"
        f"{WHATSAPP_INVITE_LINK}\n\n"
        f"{tag_str} #AIAutomation #MakeMoneyOnline #SideHustle"
    )

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    upload_url = f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    init_response = requests.post(
        upload_url,
        data={
            "media_type": "REELS",
            "video_url": "",
            "caption": full_caption,
            "share_to_feed": "true",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if init_response.status_code != 200:
        raise RuntimeError(f"Instagram container init failed: {init_response.text}")

    creation_id = init_response.json()["id"]

    for _ in range(20):
        status_resp = requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN},
            timeout=15,
        )
        status = status_resp.json().get("status_code", "")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram media processing failed")
        time.sleep(10)

    publish_url = f"{GRAPH_API}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    publish_response = requests.post(
        publish_url,
        data={
            "creation_id": creation_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if publish_response.status_code != 200:
        raise RuntimeError(f"Instagram publish failed: {publish_response.text}")

    media_id = publish_response.json()["id"]
    return f"https://www.instagram.com/p/{media_id}/"
