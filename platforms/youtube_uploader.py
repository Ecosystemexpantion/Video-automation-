import json
import os
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import YOUTUBE_CLIENT_SECRETS_JSON, WHATSAPP_INVITE_LINK

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_youtube_service():
    if not YOUTUBE_CLIENT_SECRETS_JSON:
        raise RuntimeError("YouTube not configured — skipping")
    secrets = json.loads(YOUTUBE_CLIENT_SECRETS_JSON)
    # Support both flat {"client_id":...} and nested {"installed":{"client_id":...}} formats
    s = secrets.get("installed", secrets)

    creds = Credentials(
        token=s.get("token"),
        refresh_token=s.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=s["client_id"],
        client_secret=s["client_secret"],
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: str,
    title: str,
    description: str,
    hashtags: list[str],
    topic: str = "",
) -> str:
    youtube = _get_youtube_service()

    tags = hashtags + ["AIAutomation", "Shorts", "MakeMoneyWithAI"]
    full_description = (
        f"{description}\n\n"
        f"🔥 Join our FREE WhatsApp community for daily AI money tips:\n"
        f"{WHATSAPP_INVITE_LINK}\n\n"
        f"#{' #'.join(tags)}"
    )

    body = {
        "snippet": {
            "title": f"{title} #Shorts",
            "description": full_description,
            "tags": tags,
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return f"https://www.youtube.com/shorts/{video_id}"
