import os
import re
import json
import subprocess
import webbrowser
import urllib.parse
import logging
import asyncio
import httpx

logger = logging.getLogger("jarvis.system")
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env if present
APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

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
    "camera": "microsoft.windows.camera:",
    "webcam": "microsoft.windows.camera:",
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
        if app_target.endswith(":") or app_target.startswith("ms-"):
            subprocess.Popen(f'start "" "{app_target}"', shell=True)
            return True
        os.startfile(app_target)
        return True
    except Exception as e:
        try:
            cmd = f'start "" "{app_target}"' if (app_target.endswith(":") or app_target.startswith("ms-")) else app_target
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception as e2:
            logger.error(f"Failed to launch app {app_target}: {e2}")
            return False


def resolve_youtube_video(query: str) -> dict | None:
    """Resolve a free-form query to a single playable YouTube video.

    Returns {"video_id", "url", "title"} or None when YouTube cannot be reached.
    """
    q = (query or "").strip()
    if not q:
        return None

    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=8.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(search_url)
        if resp.status_code != 200:
            logger.warning(f"YouTube resolve HTTP {resp.status_code} for '{q}'")
            return None

        raw = resp.text
        # Prefer real search-result renderers, then any videoId, then watch links.
        ids = re.findall(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})"', raw)
        if not ids:
            ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', raw)
        if not ids:
            ids = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", raw)
        if not ids:
            logger.warning(f"No YouTube video id found for '{q}'")
            return None

        video_id = ids[0]
        title = None
        m = re.search(
            r'"videoRenderer":\{"videoId":"' + re.escape(video_id) + r'".*?"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"',
            raw,
            re.DOTALL,
        )
        if m:
            try:
                title = json.loads(f'"{m.group(1)}"')
            except Exception:
                title = m.group(1)
            title = (title or "").strip()[:140] or None

        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
        }
    except Exception as e:
        logger.warning(f"YouTube video resolve failed for '{q}': {e}")
        return None


def fast_multilingual_intent(text: str) -> dict | None:
    """Zero-latency heuristic matcher for English, Marathi, Hindi, and Hinglish."""
    raw = text.strip()
    lower = raw.lower()

    # 1. Camera Intent (English, Marathi: उघड / चालू कर, Hindi: खोल / चलाओ, Hinglish: open kar)
    camera_nouns = ["camera", "कॅमेरा", "कैमरा", "webcam", "वेबकॅम"]
    open_verbs = [
        "open", "launch", "start", "turn on", "activate",
        "उघड", "उघडा", "उघडणे", "चालू कर", "चालू करा", "सुरू कर", "सुरू करा", "दाखव", "दाखवा",
        "खोल", "खोलो", "खोलना", "चलाओ", "चालू करो", "दिखाओ", "स्टार्ट",
        "open kar", "open karo", "chalu kar", "chalu karo", "khol kar", "khol de", "khol do"
    ]
    if any(noun in lower for noun in camera_nouns):
        if any(verb in lower for verb in open_verbs) or lower.startswith("camera") or lower == "camera" or "कॅमेरा" in lower:
            launch_app("microsoft.windows.camera:")
            return {
                "success": True,
                "action": "open_camera",
                "type": "app",
                "target": "microsoft.windows.camera:",
                "reply": "Activating optical sensors and launching the camera interface, sir.",
            }

    # 2. Play Song / Music Intent (English, Marathi: गाणं लाव/वाजव, Hindi: गाना बजाओ/लगाओ/सुनाओ)
    music_nouns = ["song", "songs", "music", "track", "गाणं", "गाणी", "गाणे", "गीत", "संगीत", "गाना", "गाने"]
    play_verbs = [
        "play", "start", "listen",
        "लाव", "लावा", "वाजव", "वाजवा", "चालू कर", "चालू करा", "सुरू कर", "सुरू करा", "ऐकव",
        "बजाओ", "लगाओ", "चलाओ", "सुनाओ", "शुरू करो",
        "play kar", "play karo", "bajao", "lagao", "chalao", "sunao", "lav"
    ]
    strip_words = {
        "a", "an", "the", "ek", "एक", "काही", "koi", "on", "youtube", "यूट्यूब", "वर", "पर", "मला",
        "mere", "liye", "माझ्यासाठी", "माझ्या", "साठी",
        "लाव", "लावा", "वाजव", "वाजवा", "चालू", "कर", "करा", "सुरू",
        "ऐकव", "बजाओ", "लगाओ", "चलाओ", "सुनाओ", "शुरू", "करो", "play", "start", "listen", "chalu", "suru",
        "karo", "bajao", "lagao", "sunao", "lav", "kara", "kar", "de", "do", "na", "ye", "wo", "ko",
        "se", "me", "ke", "ka", "ki", "ho", "bhai", "yaar", "jara", "thoda", "is", "are",
        "दे", "दो", "ना", "ये", "वो", "तो", "ही", "लो",
    }
    tokens = [t.strip(" :,-_!?.") for t in lower.split()]
    filtered = [t for t in tokens if t and t not in strip_words]
    content_words = [t for t in filtered if t not in music_nouns]
    has_music_noun = any(noun in lower for noun in music_nouns)
    has_play_verb = any(verb in lower for verb in play_verbs) or "play" in lower
    # "play <anything>" with or without an explicit music noun counts as a music request,
    # while bare verbs ("start chrome") must stay with the app launcher below.
    music_play_starts = (
        "play", "bajao", "lagao", "sunao", "vajav", "ऐकव", "बजाओ", "लगाओ", "सुनाओ", "वाजव",
    )
    is_play_phrase = any(lower == v or lower.startswith(v + " ") for v in music_play_starts)
    # User only said the music noun itself: "song", "गाणं", "गाना"
    is_bare_noun = has_music_noun and not content_words
    # "play spotify" / "play youtube" should reach the app & site launcher, not a music search
    known_launch_targets = set(COMMON_APPS.keys()) | set(COMMON_WEBSITES.keys()) | {"spotify", "code", "vscode"}
    skip_for_app = is_play_phrase and len(filtered) == 1 and filtered[0] in known_launch_targets
    if ((has_music_noun and has_play_verb) or is_play_phrase or is_bare_noun) and not skip_for_app:
        # Keep nouns as search modifiers ("hindi songs") but fall back to trending when
        # the user only named the music noun itself.
        clean_query = " ".join(filtered).strip() if content_words else "trending hit songs"
        if not clean_query:
            clean_query = "trending hit songs"

        # Resolve the actual video so playback starts immediately instead of
        # dumping the user on a YouTube search results page.
        resolved = resolve_youtube_video(clean_query)
        if resolved:
            return {
                "success": True,
                "action": "play_music",
                "type": "video",
                "target": resolved["url"],
                "url": resolved["url"],
                "video_id": resolved["video_id"],
                "title": resolved.get("title"),
                "query": clean_query,
                "reply": f"Now playing '{resolved.get('title') or clean_query}' for you, sir.",
            }

        target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_query)}"
        open_url(target_url)
        return {
            "success": True,
            "action": "play_music",
            "type": "url",
            "target": target_url,
            "query": clean_query,
            "reply": f"Initiating music playback for '{clean_query}' on your PC, sir.",
        }

    # 3. YouTube Search Intent ("माझ्यासाठी YouTube वर हे search कर", "YouTube वर ... शोध", "YouTube search for ...")
    if "youtube" in lower or "यूट्यूब" in lower:
        search_triggers = [
            "search", "find", "look up",
            "शोध", "शोधा", "सर्च", "दाखव", "दाखवा", "बघायचं", "पहायचं",
            "खोजो", "सर्च करो", "दिखाओ", "ढूंढो",
            "search kar", "search karo", "dakhva", "dikhao", "dhoondo"
        ]
        if any(st in lower for st in search_triggers):
            strip_tokens = {
                "माझ्यासाठी", "माझ्या", "साठी", "मेरे", "लिए", "हे", "एक", "youtube", "यूट्यूब",
                "वर", "पर", "search", "शोध", "शोधा", "सर्च", "दाखव", "दाखवा", "दिखाओ", "खोजो",
                "कर", "करा", "karo", "kar", "pe", "var", "for", "please", "about", "videos", "video"
            }
            tokens = [t.strip(" :,-_!?.") for t in lower.split()]
            filtered = [t for t in tokens if t and t not in strip_tokens]
            q = " ".join(filtered).strip()
            if not q:
                q = "Iron Man 3"
            target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            open_url(target_url)
            return {
                "success": True,
                "action": "search_youtube",
                "type": "url",
                "target": target_url,
                "query": q,
                "reply": f"Searching YouTube for '{q}' on your PC, sir.",
            }

    # 4. Google / Web Search Intent
    if ("google" in lower or "गुगल" in lower or "गूगल" in lower or "search" in lower or "शोध" in lower) and not any(k in lower for k in ["youtube", "यूट्यूब", "camera", "song"]):
        search_verbs = ["search", "google", "शोध", "खोजो", "सर्च", "information", "माहिती", "dhoondo"]
        if any(v in lower for v in search_verbs):
            q = lower
            for tok in ["search for", "search", "google for", "google", "शोध", "खोजो", "सर्च", "वर", "पर", "बदल", "बद्दल", "माहिती", "सांग", "batao", "about"]:
                q = re.sub(rf"\b{re.escape(tok)}\b", "", q, flags=re.IGNORECASE)
            q = q.strip(" :,-_!?.")
            if q:
                target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
                open_url(target_url)
                return {
                    "success": True,
                    "action": "search_google",
                    "type": "url",
                    "target": target_url,
                    "query": q,
                    "reply": f"Searching Google for '{q}' on your PC, sir.",
                }

    # 5. Native Apps (Chrome, Calculator, Notepad, Explorer, Terminal, etc.)
    app_aliases = {
        "chrome": ["chrome", "क्रोम", "google chrome"],
        "calculator": ["calculator", "कॅल्क्युलेटर", "कैलकुलेटर", "calc", "हिशोब"],
        "notepad": ["notepad", "नोटपॅड", "नोटपैड", "text editor"],
        "file explorer": ["file explorer", "explorer", "files", "फाइल्स", "फोल्डर", "माय कॉम्प्युटर"],
        "cmd": ["cmd", "command prompt", "terminal", "कमांड प्रॉम्प्ट"],
        "paint": ["paint", "mspaint", "पेंट"],
        "settings": ["settings", "सेटिंग्ज", "सेटिंग्स"],
        "task manager": ["task manager", "taskmgr", "टास्क मॅनेजर"],
    }
    for app_key, aliases in app_aliases.items():
        if any(alias in lower for alias in aliases):
            is_play_alias = lower.startswith("play ") and any(alias in lower for alias in aliases)
            if any(verb in lower for verb in open_verbs) or lower.startswith(app_key) or lower == app_key or is_play_alias:
                exec_target = COMMON_APPS.get(app_key, f"{app_key}.exe")
                launch_app(exec_target)
                name = app_key.title()
                return {
                    "success": True,
                    "action": "open_app",
                    "type": "app",
                    "target": exec_target,
                    "reply": f"Launching {name} on your system, sir.",
                }

    # 6. Common Websites (WhatsApp, Instagram, Spotify, etc.)
    site_aliases = {
        "youtube": ["youtube", "यूट्यूब"],
        "whatsapp": ["whatsapp", "व्हाट्सएप", "व्हाट्सअ‍ॅप"],
        "instagram": ["instagram", "insta", "इंस्टाग्राम"],
        "spotify": ["spotify", "स्पॉटिफाय"],
        "facebook": ["facebook", "फेसबुक"],
        "netflix": ["netflix", "नेटफ्लिक्स"],
        "github": ["github", "गिटहब"],
        "chatgpt": ["chatgpt", "चॅटजीपीटी"],
    }
    for site_key, aliases in site_aliases.items():
        if any(alias in lower for alias in aliases):
            is_play_alias = lower.startswith("play ") and any(alias in lower for alias in aliases)
            if any(verb in lower for verb in open_verbs) or lower.startswith(site_key) or lower == site_key or is_play_alias:
                site_url = COMMON_WEBSITES.get(site_key, f"https://www.{site_key}.com")
                open_url(site_url)
                name = site_key.capitalize() if site_key != "youtube" else "YouTube"
                return {
                    "success": True,
                    "action": "open_website",
                    "type": "url",
                    "target": site_url,
                    "reply": f"Opening {name} on your PC, sir.",
                }

    # 7. Browser launcher
    if "browser" in lower or "ब्राउझर" in lower or "ब्राउज़र" in lower or "open web" in lower:
        open_url("https://www.google.com")
        return {
            "success": True,
            "action": "open_website",
            "type": "url",
            "target": "https://www.google.com",
            "reply": "Opening the default web browser on your PC, sir.",
        }

    # 8. Direct domain/URL like "github.com", "openai.com"
    tokens = lower.split()
    for t in tokens:
        if "." in t and not t.endswith(".exe"):
            clean = t.strip(".,;:?!'\"")
            if clean.startswith("http://") or clean.startswith("https://") or any(clean.endswith(ext) for ext in [".com", ".org", ".net", ".io", ".ai", ".in", ".edu", ".gov"]):
                open_url(clean)
                return {
                    "success": True,
                    "action": "open_url",
                    "type": "url",
                    "target": clean,
                    "reply": f"Navigating to {clean} on your PC, sir.",
                }

    return None


async def gemini_multilingual_intent(text: str) -> dict | None:
    """Semantic intent classification using Gemini for natural, conversational, or ambiguous queries."""
    if not GEMINI_API_KEY:
        return None

    system_instruction = """You are the semantic intent parser for J.A.R.V.I.S., Tony Stark's personal assistant.
The user speaks naturally in English, Marathi (मराठी), Hindi (हिंदी), Hinglish, Marathlish, or code-mixed language.
Analyze the user's input and determine if they want to execute an action on their PC.

Action categories:
- "open_camera": User wants to open/launch their camera or webcam (e.g., "माझा camera उघड", "camera open kar", "mera camera khol", "take a picture with camera").
- "play_music": User wants to play a song/music (e.g., "एक गाना लाव", "गाणी वाजव", "play a song", "कोई गाना बजाओ").
- "open_app": User wants to open a desktop PC app (e.g., Chrome, Calculator, Notepad, File Explorer, Terminal, Paint, Settings).
- "open_website": User wants to open a website (e.g., YouTube, WhatsApp, Instagram, Spotify, Netflix, GitHub).
- "search_youtube": User wants to search YouTube for something (e.g., "माझ्यासाठी YouTube वर हे search कर", "YouTube pe trailer dikhao").
- "search_google": User wants to search Google/web for something.
- "none": Pure conversational question, greeting, or knowledge query (e.g., "तू कोण आहेस?", "who are you?", "tell me about Stark Tower").

Always output strictly valid JSON:
{
  "action": "open_camera" | "play_music" | "open_app" | "open_website" | "search_youtube" | "search_google" | "none",
  "target": "<app name or website name or URI, or empty string>",
  "query": "<search query or song title if applicable, or empty string>",
  "reply": "<Articulate, polite 1-sentence Jarvis confirmation in the user's language or refined British-polite tone>"
}"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 180,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                GEMINI_API_URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_json = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(raw_json)
                action = parsed.get("action", "none")

                if action == "open_camera":
                    launch_app("microsoft.windows.camera:")
                    return {
                        "success": True,
                        "action": "open_camera",
                        "type": "app",
                        "target": "microsoft.windows.camera:",
                        "reply": parsed.get("reply") or "Activating optical sensors and opening the camera, sir.",
                    }

                elif action == "play_music":
                    query = parsed.get("query", "").strip() or "trending songs"
                    target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                    open_url(target_url)
                    return {
                        "success": True,
                        "action": "play_music",
                        "type": "url",
                        "target": target_url,
                        "query": query,
                        "reply": parsed.get("reply") or f"Playing music for you on your PC, sir.",
                    }

                elif action == "search_youtube":
                    query = parsed.get("query", "").strip() or "Iron Man"
                    target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                    open_url(target_url)
                    return {
                        "success": True,
                        "action": "search_youtube",
                        "type": "url",
                        "target": target_url,
                        "query": query,
                        "reply": parsed.get("reply") or f"Searching YouTube for '{query}' on your PC, sir.",
                    }

                elif action == "search_google":
                    query = parsed.get("query", "").strip() or "Stark Industries"
                    target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                    open_url(target_url)
                    return {
                        "success": True,
                        "action": "search_google",
                        "type": "url",
                        "target": target_url,
                        "query": query,
                        "reply": parsed.get("reply") or f"Searching Google for '{query}' on your PC, sir.",
                    }

                elif action == "open_app":
                    target_name = (parsed.get("target") or "notepad").lower().strip()
                    app_exec = COMMON_APPS.get(target_name, f"{target_name}.exe")
                    launch_app(app_exec)
                    return {
                        "success": True,
                        "action": "open_app",
                        "type": "app",
                        "target": app_exec,
                        "reply": parsed.get("reply") or f"Launching {target_name.title()} on your system, sir.",
                    }

                elif action == "open_website":
                    site_name = (parsed.get("target") or "google").lower().strip()
                    site_url = COMMON_WEBSITES.get(site_name, f"https://www.{site_name}.com")
                    open_url(site_url)
                    return {
                        "success": True,
                        "action": "open_website",
                        "type": "url",
                        "target": site_url,
                        "reply": parsed.get("reply") or f"Opening {site_name.title()} on your PC, sir.",
                    }

    except Exception as e:
        logger.error(f"Gemini semantic intent parsing error: {e}")

    return None


async def resolve_natural_intent(text: str) -> dict:
    """Asynchronous intent resolver: checks fast multilingual rules first, then Gemini semantic parser."""
    clean_text = text.strip()
    if not clean_text:
        return {"success": False, "type": "none", "target": "", "reply": ""}

    # 1. Zero-latency fast-path match
    fast_match = fast_multilingual_intent(clean_text)
    if fast_match and fast_match.get("success"):
        return fast_match

    # 2. Gemini semantic understanding fallback
    gemini_match = await gemini_multilingual_intent(clean_text)
    if gemini_match and gemini_match.get("success"):
        return gemini_match

    return {"success": False, "type": "none", "target": "", "reply": ""}


def execute_system_intent(text: str) -> dict:
    """Synchronous entry point backwards-compatible with existing callers."""
    clean_text = text.strip()
    fast_match = fast_multilingual_intent(clean_text)
    if fast_match and fast_match.get("success"):
        return fast_match

    # If in async loop or fallback
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a task or use fast heuristics
            return fast_match or {"success": False, "type": "none", "target": "", "reply": ""}
        else:
            return loop.run_until_complete(resolve_natural_intent(text))
    except Exception:
        return fast_match or {"success": False, "type": "none", "target": "", "reply": ""}
