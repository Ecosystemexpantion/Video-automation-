import requests
import os
from config import FB_ACCESS_TOKEN, FB_PAGE_ID, WHATSAPP_INVITE_LINK

GRAPH_API = "https://graph.facebook.com/v21.0"


def post_video(video_path: str, title: str, description: str, hashtags: list[str]) -> str:
    tag_str = " ".join(f"#{h}" for h in hashtags)
    full_description = (
        f"{title}\n\n"
        f"{description}\n\n"
        f"🔥 Join our FREE WhatsApp community for daily AI tips & money-making strategies:\n"
        f"{WHATSAPP_INVITE_LINK}\n\n"
        f"{tag_str} #AIAutomation #MakeMoneyOnline"
    )

    upload_url = f"{GRAPH_API}/{FB_PAGE_ID}/videos"

    with open(video_path, "rb") as video_file:
        response = requests.post(
            upload_url,
            data={
                "description": full_description,
                "title": title,
                "published": "true",
                "access_token": FB_ACCESS_TOKEN,
            },
            files={"source": video_file},
            timeout=120,
        )

    response.raise_for_status()
    video_id = response.json().get("id")
    return f"https://www.facebook.com/video/{video_id}"
