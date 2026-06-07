# Davis — AI Automation Lead Engine

Automatically generates short-form videos about AI money-making, posts them to YouTube, Instagram, and Facebook 4× per day, and drives viewers straight to your WhatsApp group. 100% free. No server needed. Talk to it by saying **"Hey Davis"** in the web app.

---

## What It Does

- Generates a unique 30–45 second video every 6 hours using Google Gemini AI
- Adds a professional voiceover using Microsoft Edge TTS (free)
- Fetches relevant background footage from Pexels (free)
- Posts to YouTube Shorts, Instagram Reels, and Facebook automatically
- Logs all activity to Supabase
- Submits your WhatsApp group to 8 directories (one-time, passive members)
- **Davis web app**: Say "Hey Davis" → get a spoken report on your leads

---

## Setup (One Time Only)

### Step 1 — Get Your Free API Keys

| Service | URL | What you do |
|---|---|---|
| Google Gemini | https://aistudio.google.com | Sign in → Get API Key (free) |
| Pexels | https://www.pexels.com/api | Register → Get API Key (free) |
| Supabase | https://supabase.com | Create project → Settings → API → copy URL + service_role key |
| YouTube | https://console.cloud.google.com | Create project → Enable YouTube Data API v3 → Create OAuth credentials → follow auth flow to get refresh token |
| Instagram/Facebook | https://developers.facebook.com | Create app → Add Instagram Graph API → generate long-lived access token |

### Step 2 — Set Up Supabase Database

1. Open your Supabase project → SQL Editor
2. Paste and run the contents of `database/schema.sql`
3. Done — tables are created

### Step 3 — Add GitHub Secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add each of these:

| Secret Name | Value |
|---|---|
| `WHATSAPP_INVITE_LINK` | Your WhatsApp group invite link |
| `GEMINI_API_KEY` | From Google AI Studio |
| `PEXELS_API_KEY` | From Pexels |
| `YOUTUBE_CLIENT_SECRETS_JSON` | JSON with `token`, `refresh_token`, `client_id`, `client_secret` |
| `INSTAGRAM_ACCESS_TOKEN` | From Facebook Developers |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Your Instagram Business account ID |
| `FB_ACCESS_TOKEN` | From Facebook Developers |
| `FB_PAGE_ID` | Your Facebook Page ID |
| `SUPABASE_URL` | From Supabase dashboard |
| `SUPABASE_SERVICE_KEY` | From Supabase dashboard (service_role key) |

### Step 4 — Deploy Davis Web App to Vercel

1. Go to https://vercel.com → Import Git Repository → select this repo
2. Set Root Directory to: `davis_app`
3. Add Environment Variables:
   - `NEXT_PUBLIC_SUPABASE_URL` = your Supabase URL
   - `SUPABASE_SERVICE_KEY` = your Supabase service key
4. Deploy → you'll get a URL like `https://davis-app.vercel.app`

### Step 5 — Submit to WhatsApp Directories (One Time)

1. Go to your GitHub repo → **Actions** tab
2. Find "Submit to WhatsApp Directories" → click **Run workflow**
3. Done — your group is submitted to 8 directories automatically

### Step 6 — Test the Pipeline

1. Go to **Actions → Davis Video Pipeline → Run workflow**
2. Set `dry_run` to `true` to test without posting
3. Then run with `dry_run = false` to post a real video
4. Check your YouTube/Instagram/Facebook — video should appear within 5 minutes

---

## Automatic Schedule

Once secrets are set, the pipeline runs automatically at:
- 6:00 AM WAT
- 12:00 PM WAT  
- 6:00 PM WAT
- 12:00 AM WAT

= **4 videos/day × 3 platforms = 12 posts/day**, every single day, for free.

---

## Talking to Davis

Open your Vercel app URL in Chrome (desktop or mobile).

- Say **"Hey Davis"** → Davis activates and asks what you want to know
- Ask any of these:
  - *"How many leads today?"*
  - *"How many posts this week?"*
  - *"Which platform is working best?"*
  - *"Any failures?"*
  - *"Give me a report"*

Davis will speak the answer back to you.

---

## Updating Your WhatsApp Group Count

Davis can't auto-detect WhatsApp members (WhatsApp has no API for this). To track your member count:

1. Go to Supabase → Table Editor → `leads` table
2. Insert a row: `source = "manual"`, `whatsapp_member_count = [your current count]`
3. Davis will now report the correct number

Or run this SQL in Supabase:
```sql
INSERT INTO leads (source, whatsapp_member_count) 
VALUES ('manual', 150);  -- replace 150 with your actual count
```

---

## File Structure

```
Video-automation-/
├── .github/workflows/          # Automated scheduling
├── pipeline/                   # Video generation (script, voice, footage, assembly)
├── platforms/                  # Platform uploaders (YouTube, Instagram, Facebook)
├── database/                   # Supabase schema + client
├── davis_app/                  # Voice-controlled web dashboard
├── templates/                  # 30 AI money-making video topics
├── config.py                   # Environment variable loader
└── run.py                      # Main pipeline runner
```
