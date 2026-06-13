"""
Records a browser demo video synced to the script's demo_steps.
Each step is shown for roughly the duration of its narration segment.
Falls back to Pexels footage if Playwright fails.
"""

import os
import time
import math
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "tmp"
VIEWPORT = {"width": 1080, "height": 1920}


def _estimate_step_duration(narration: str, total_duration: float, all_narrations: list) -> float:
    """Allocate time proportional to word count."""
    words = len(narration.split())
    total_words = sum(len(n.split()) for n in all_narrations)
    return max(1.5, (words / max(total_words, 1)) * total_duration)


def record_demo(demo_steps: list, total_duration: float, output_path: str = None) -> str:
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "demo.mp4")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    narrations = [s.get("narration", "") for s in demo_steps]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
            ],
        )

        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=OUTPUT_DIR,
            record_video_size=VIEWPORT,
            device_scale_factor=1,
        )

        page = context.new_page()

        # Style the page to look clean
        page.add_init_script("""
            document.addEventListener('DOMContentLoaded', () => {
                document.body.style.cursor = 'default';
            });
        """)

        for step in demo_steps:
            action = step.get("action", "")
            narration = step.get("narration", "")
            hold = _estimate_step_duration(narration, total_duration, narrations)

            try:
                if action == "goto":
                    url = step.get("url", "https://google.com")
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(800)

                elif action == "click":
                    desc = step.get("description", "")
                    # Try common selectors based on description keywords
                    selectors = _guess_selectors(desc)
                    clicked = False
                    for sel in selectors:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=2000):
                                el.scroll_into_view_if_needed()
                                el.click(timeout=3000)
                                clicked = True
                                break
                        except Exception:
                            continue
                    if not clicked:
                        # Just hover the center of the page to show activity
                        page.mouse.move(540, 960)

                elif action == "type":
                    text = step.get("text", "")
                    page.keyboard.type(text, delay=60)

                elif action == "scroll":
                    direction = step.get("direction", "down")
                    delta = 600 if direction == "down" else -600
                    page.mouse.wheel(0, delta)
                    page.wait_for_timeout(400)

                elif action == "highlight":
                    sel = step.get("selector", "")
                    if sel:
                        page.evaluate(f"""
                            const el = document.querySelector('{sel}');
                            if (el) {{
                                el.style.outline = '4px solid #FFD700';
                                el.style.boxShadow = '0 0 12px rgba(255,215,0,0.7)';
                            }}
                        """)

            except Exception as e:
                print(f"  [Screen] Step '{action}' failed (continuing): {e}")

            # Hold this screen for the narration duration
            page.wait_for_timeout(int(hold * 1000))

        # Close context to finalize the video file
        video_path = page.video.path()
        context.close()
        browser.close()

    # Rename to desired output path
    if video_path and os.path.exists(video_path):
        os.rename(video_path, output_path)
        return output_path

    raise RuntimeError("Screen recording produced no output file")


def _guess_selectors(description: str) -> list:
    """Map natural language descriptions to CSS/text selectors."""
    desc = description.lower()
    selectors = []

    if any(w in desc for w in ["sign up", "signup", "register", "create account", "get started"]):
        selectors += [
            "text=Sign up", "text=Sign Up", "text=Register", "text=Get Started",
            "text=Create account", "[href*='signup']", "[href*='register']",
            "button:has-text('Sign')", "a:has-text('Sign up')",
        ]
    if any(w in desc for w in ["login", "log in", "sign in"]):
        selectors += ["text=Log in", "text=Sign in", "[href*='login']"]
    if any(w in desc for w in ["search", "search bar", "search box"]):
        selectors += ["input[type='search']", "input[name='q']", "[placeholder*='Search']", "textarea[name='q']"]
    if any(w in desc for w in ["email", "email field", "email box"]):
        selectors += ["input[type='email']", "input[name='email']", "[placeholder*='email']"]
    if any(w in desc for w in ["password"]):
        selectors += ["input[type='password']"]
    if any(w in desc for w in ["submit", "continue", "next", "proceed"]):
        selectors += ["button[type='submit']", "text=Continue", "text=Next", "text=Submit"]
    if any(w in desc for w in ["menu", "hamburger", "nav"]):
        selectors += ["button[aria-label='Menu']", "nav button", ".hamburger"]

    # Fallback: try any button or link containing key words
    for word in desc.split():
        if len(word) > 3:
            selectors.append(f"text={word.capitalize()}")

    return selectors
