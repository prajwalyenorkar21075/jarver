import os
import subprocess
import webbrowser
import urllib.parse
import logging

logger = logging.getLogger("jarvis.system")
logging.basicConfig(level=logging.INFO)

COMMON_WEBSITES = {
    "youtube": "https://www.youtube.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "whatsapp": "https://web.whatsapp.com",
    "google": "https://www.google.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chatgpt.com",
    "gmail": "https://mail.google.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitch": "https://www.twitch.tv",
    "discord": "https://discord.com/app",
}

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

COMMON_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "paint": "mspaint.exe",
    "chrome": CHROME_PATH if os.path.exists(CHROME_PATH) else "chrome.exe",
    "chromium": CHROME_PATH if os.path.exists(CHROME_PATH) else "chrome.exe",
    "edge": EDGE_PATH if os.path.exists(EDGE_PATH) else "msedge.exe",
    "browser": CHROME_PATH if os.path.exists(CHROME_PATH) else "https://www.google.com",
}


def open_url(url: str) -> bool:
    """Open URL in user's default desktop browser on Windows."""
    try:
        clean_url = url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url
        logger.info(f"Opening URL in default browser: {clean_url}")
        webbrowser.open(clean_url)
        return True
    except Exception as e:
        logger.error(f"Failed to open URL {url}: {e}")
        return False


def launch_app(app_target: str) -> bool:
    """Launch a desktop application or Windows URI scheme."""
    try:
        logger.info(f"Launching app: {app_target}")
        os.startfile(app_target)
        return True
    except Exception as e:
        try:
            subprocess.Popen(app_target, shell=True)
            return True
        except Exception as e2:
            logger.error(f"Failed to launch app {app_target}: {e2}")
            return False


def execute_system_intent(text: str) -> dict:
    """Analyze text for website, app, or search intents and execute on PC."""
    lower = text.strip().lower()

    # 1. Search on YouTube or Google
    if lower.startswith("search youtube for ") or lower.startswith("search on youtube for ") or lower.startswith("play ") and "on youtube" in lower:
        query = lower.replace("search youtube for ", "").replace("search on youtube for ", "").replace("on youtube", "").replace("play ", "").strip()
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        open_url(url)
        return {
            "success": True,
            "type": "url",
            "target": url,
            "reply": f"Searching YouTube for '{query}' on your PC, sir.",
        }

    if lower.startswith("search for ") or lower.startswith("search ") or lower.startswith("google "):
        query = lower.replace("search for ", "").replace("search ", "").replace("google ", "").strip()
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        open_url(url)
        return {
            "success": True,
            "type": "url",
            "target": url,
            "reply": f"Searching Google for '{query}' on your PC, sir.",
        }

    # 2. Known Websites (YouTube, Instagram, Facebook, etc.)
    for site_key, site_url in COMMON_WEBSITES.items():
        if site_key in lower:
            open_url(site_url)
            name = site_key.capitalize() if site_key != "youtube" else "YouTube"
            return {
                "success": True,
                "type": "url",
                "target": site_url,
                "reply": f"Opening {name} on your PC, sir.",
            }

    # 3. Known PC Apps
    for app_key, app_exec in COMMON_APPS.items():
        if app_key in lower:
            launch_app(app_exec)
            name = app_key.title()
            return {
                "success": True,
                "type": "app",
                "target": app_exec,
                "reply": f"Launching {name} on your system, sir.",
            }

    # 4. Browser launcher
    if "browser" in lower or "open web" in lower or "open internet" in lower:
        open_url("https://www.google.com")
        return {
            "success": True,
            "type": "url",
            "target": "https://www.google.com",
            "reply": "Opening the default web browser on your PC, sir.",
        }

    # 5. Direct domain/URL like "open github.com" or "open reddit.com"
    tokens = lower.split()
    for t in tokens:
        if "." in t and not t.endswith(".exe"):
            clean = t.strip(".,;:?!'\"")
            if clean.startswith("http://") or clean.startswith("https://") or clean.endswith(".com") or clean.endswith(".org") or clean.endswith(".net") or clean.endswith(".io") or clean.endswith(".ai") or clean.endswith(".in"):
                open_url(clean)
                return {
                    "success": True,
                    "type": "url",
                    "target": clean,
                    "reply": f"Navigating to {clean} on your PC, sir.",
                }

    return {"success": False, "type": "none", "target": "", "reply": ""}
