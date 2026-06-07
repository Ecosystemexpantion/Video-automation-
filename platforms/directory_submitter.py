import asyncio
import time
from playwright.async_api import async_playwright
from config import WHATSAPP_INVITE_LINK

DIRECTORIES = [
    {
        "name": "GroupSor",
        "url": "https://groupsor.link/group/addgroup",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
            "category": "Education",
            "description": "Join thousands learning to make money with AI automation tools. Free daily tips, strategies, and community support.",
            "country": "Nigeria",
        },
    },
    {
        "name": "77Links",
        "url": "https://77links.com/",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
            "category": "Education",
            "description": "Learn how to use AI tools to make money online. Free community.",
        },
    },
    {
        "name": "ImagesPlatform",
        "url": "https://www.imagesplatform.com/add-whatsapp-group-link",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
        },
    },
    {
        "name": "WhatsGroupJoinLinks",
        "url": "https://www.whatsgroupjoinlinks.com/submit-whatsapp-group/",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
        },
    },
    {
        "name": "TheWhatsGroupLink",
        "url": "https://thewhatsgrouplink.com/submit/",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
        },
    },
    {
        "name": "WappGroupLinks",
        "url": "https://wappgrouplinks.com/submit/",
        "fields": {
            "invite_link": WHATSAPP_INVITE_LINK,
            "group_name": "AI Automation Money-Making Community",
        },
    },
]

GROUP_NAME = "AI Automation Money-Making Community"
GROUP_DESCRIPTION = "Learn how to make money using AI automation tools. Free daily tips and strategies for entrepreneurs. Join thousands already using AI to earn online."
GROUP_CATEGORY = "Education"


async def _submit_one(page, directory: dict) -> dict:
    result = {"name": directory["name"], "status": "unknown"}
    try:
        await page.goto(directory["url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        for selector in ['input[name*="link"]', 'input[placeholder*="link"]',
                         'input[placeholder*="WhatsApp"]', 'input[type="url"]']:
            el = await page.query_selector(selector)
            if el:
                await el.fill(WHATSAPP_INVITE_LINK)
                break

        for selector in ['input[name*="name"]', 'input[placeholder*="name"]',
                         'input[placeholder*="group"]']:
            el = await page.query_selector(selector)
            if el:
                await el.fill(GROUP_NAME)
                break

        for selector in ['textarea[name*="desc"]', 'textarea[placeholder*="desc"]',
                         'textarea']:
            el = await page.query_selector(selector)
            if el:
                await el.fill(GROUP_DESCRIPTION)
                break

        for selector in ['button[type="submit"]', 'input[type="submit"]',
                         'button:has-text("Submit")', 'button:has-text("Add")']:
            el = await page.query_selector(selector)
            if el:
                await el.click()
                await asyncio.sleep(3)
                break

        result["status"] = "submitted"

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)

    return result


async def submit_to_all_directories() -> list[dict]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )

        for directory in DIRECTORIES:
            page = await context.new_page()
            result = await _submit_one(page, directory)
            results.append(result)
            print(f"[Directory] {result['name']}: {result['status']}")
            await page.close()
            await asyncio.sleep(30)

        await browser.close()

    return results


def run():
    return asyncio.run(submit_to_all_directories())


if __name__ == "__main__":
    results = run()
    for r in results:
        print(r)
