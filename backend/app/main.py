import os
import sys
import re
import urllib.parse
import asyncio
import queue
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from app.system_controller import open_url, launch_app, execute_system_intent
except ImportError:
    from system_controller import open_url, launch_app, execute_system_intent

app = FastAPI(title="Jarvis Backend", version="0.2.0")

# Load environment variables from .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
POCKET_TTS_SERVE_URL = os.getenv("POCKET_TTS_SERVE_URL", "http://127.0.0.1:8001/tts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[MessageItem]


class TTSRequest(BaseModel):
    text: str


class SystemOpenRequest(BaseModel):
    target: str
    type: str = "auto"  # "url", "app", "auto"


JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's sophisticated AI companion.
Tone: Highly polite, articulate, composed, intelligent, with a refined British manner.
Keep answers concise (1-2 sentences) ideal for spoken voice.
When asked to open websites or apps (YouTube, Instagram, Facebook, browser, calculator, etc.), confirm you are launching them directly on the system."""


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "jarvis-backend",
        "llm_provider": "groq",
        "llm_model": GROQ_MODEL,
        "tts_engine": "uvx pocket-tts serve",
        "tts_serve_url": POCKET_TTS_SERVE_URL,
        "cloned_voice": "JARVIS - Marvel's Iron Man 3",
        "system_automation": "enabled",
        "chromium_engine": "ready",
        "version": "0.2.0",
    }


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Synthesize speech using official `uvx pocket-tts serve` server."""
    text_content = req.text.strip()
    if not text_content:
        text_content = "Yes, sir."

    # 1. Forward directly to running `uvx pocket-tts serve` instance
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                POCKET_TTS_SERVE_URL,
                data={"text": text_content},
            )
            resp.raise_for_status()
            return Response(content=resp.content, media_type="audio/wav")
    except Exception as e:
        print(f"`uvx pocket-tts serve` proxy error: {e}, falling back to in-process pocket-tts service")

    # 2. In-process fallback with pre-computed voice state
    try:
        try:
            from app.tts_service import synthesize_speech
        except ImportError:
            from tts_service import synthesize_speech

        wav_bytes = synthesize_speech(text_content)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e2:
        print(f"Fallback synthesis error: {e2}")
        raise HTTPException(status_code=500, detail=str(e2))


@app.post("/api/system/open")
async def system_open_endpoint(req: SystemOpenRequest):
    """Directly open URLs in default desktop browser or launch desktop apps."""
    target = req.target.strip()
    if req.type == "url":
        success = open_url(target)
        return {"success": success, "type": "url", "target": target}
    elif req.type == "app":
        success = launch_app(target)
        return {"success": success, "type": "app", "target": target}
    else:
        result = execute_system_intent(target)
        return result


@app.get("/api/youtube/search")
async def youtube_search(q: str = "Iron Man 3"):
    """Search YouTube and return playable video IDs and details."""
    query = q.strip()
    if not query:
        query = "Iron Man 3"

    import urllib.parse
    import re
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    videos = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                raw = resp.text
                found_ids = list(dict.fromkeys(re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', raw)))[:10]
                for vid in found_ids:
                    videos.append({
                        "id": vid,
                        "title": f"{query.title()} Video Stream",
                        "channel": "YouTube HD",
                        "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
    except Exception as e:
        print(f"YouTube search error: {e}")

    # Fallback to verified embeddable videos if list is empty
    if not videos:
        presets = [
            {"id": "Ke1Y3P9D0Bc", "title": "Iron Man 3 — Official Trailer", "channel": "Marvel UK"},
            {"id": "8hYlB38asDY", "title": "Iron Man — Official Trailer", "channel": "Marvel Entertainment"},
            {"id": "TcMBFSGVi1c", "title": "Avengers: Endgame — Official Trailer", "channel": "Marvel Studios"},
            {"id": "eOrNdBpGMv8", "title": "Marvel's The Avengers — Trailer", "channel": "Marvel Studios"},
            {"id": "d96cjJhvlMA", "title": "Guardians of the Galaxy — Trailer", "channel": "Marvel Studios"},
            {"id": "LdOM0x0XDMo", "title": "TENET — Official Trailer", "channel": "Warner Bros"},
        ]
        videos = [
            {
                "id": p["id"],
                "title": p["title"],
                "channel": p["channel"],
                "thumbnail": f"https://img.youtube.com/vi/{p['id']}/hqdefault.jpg",
                "url": f"https://www.youtube.com/watch?v={p['id']}"
            }
            for p in presets
        ]

    return {"query": query, "results": videos}


@app.get("/api/google/search")
async def google_search(q: str = "Iron Man"):
    """Search Google/web index and return structured results, AI briefing, and knowledge card."""
    query = q.strip()
    if not query:
        query = "Iron Man"

    wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote_plus(query)}&utf8=&format=json"
    results = []
    knowledge_card = None
    ai_briefing = ""

    headers = {
        "User-Agent": "JarvisAI/1.0 (https://github.com/tonystark/jarvis; contact@jarvis.ai)"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            resp = await client.get(wiki_url)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("query", {}).get("search", [])
                for it in items[:8]:
                    raw_snippet = it.get("snippet", "")
                    clean_snippet = re.sub(r'<[^>]+>', '', raw_snippet).replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&')
                    item_title = it.get("title", "")
                    results.append({
                        "title": item_title,
                        "snippet": clean_snippet,
                        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item_title.replace(' ', '_'))}",
                        "display_url": f"https://www.google.com/search?q={urllib.parse.quote_plus(item_title)}",
                    })

            # Fetch summary knowledge card
            if results:
                summary_title = results[0]["title"].replace(" ", "_")
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(summary_title)}"
                try:
                    s_resp = await client.get(summary_url)
                    if s_resp.status_code == 200:
                        s_data = s_resp.json()
                        knowledge_card = {
                            "title": s_data.get("title", results[0]["title"]),
                            "description": s_data.get("description", "Subject Intelligence Dossier"),
                            "extract": s_data.get("extract", ""),
                            "thumbnail": s_data.get("thumbnail", {}).get("source"),
                        }
                except Exception as ex_card:
                    print(f"Knowledge card error: {ex_card}")

            # AI Executive Briefing via Groq
            if GROQ_API_KEY:
                try:
                    ai_resp = await client.post(
                        GROQ_API_URL,
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": GROQ_MODEL,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are J.A.R.V.I.S. Provide an exact 1 to 2 sentence executive briefing answering or summarizing the subject for Tony Stark. Direct, articulate, sophisticated."
                                },
                                {"role": "user", "content": f"Executive summary for: {query}"}
                            ],
                            "max_tokens": 120,
                            "temperature": 0.4
                        },
                        timeout=5.0
                    )
                    if ai_resp.status_code == 200:
                        ai_data = ai_resp.json()
                        ai_briefing = ai_data["choices"][0]["message"]["content"].strip()
                except Exception as ex_ai:
                    print(f"AI briefing error: {ex_ai}")

    except Exception as e:
        print(f"Google search error: {e}")

    # Fallback AI briefing if empty
    if not ai_briefing:
        if knowledge_card and knowledge_card.get("extract"):
            ai_briefing = knowledge_card["extract"][:220] + "..."
        else:
            ai_briefing = f"Neural query retrieved for '{query}'. Multiple high-confidence records indexed across global telemetry."

    return {
        "query": query,
        "ai_briefing": ai_briefing,
        "results": results,
        "knowledge_card": knowledge_card,
        "google_url": f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    }


class ChromiumCaptureDaemon:
    def __init__(self):
        self.req_queue = queue.Queue()
        self.lock = threading.Lock()
        self._is_alive = False
        self._ready_event = threading.Event()
        self._start_thread()

    def _start_thread(self):
        self._is_alive = True
        self._ready_event.clear()
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="JarvisChromiumDaemon")
        self.thread.start()

    def _worker_loop(self):
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                self._ready_event.set()
                print("Jarvis Chromium Engine initialized successfully.")
                while True:
                    item = self.req_queue.get()
                    if item is None:
                        break
                    url, timeout_ms, res_q = item
                    try:
                        ctx = browser.new_context(
                            viewport={"width": 1024, "height": 620},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        page = ctx.new_page()
                        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                        page.wait_for_timeout(300)
                        shot = page.screenshot(type="jpeg", quality=80)
                        ctx.close()
                        res_q.put((True, shot))
                    except Exception as exc:
                        res_q.put((False, exc))
                browser.close()
        except Exception as e:
            print(f"Jarvis Chromium Engine daemon error: {e}")
        finally:
            self._is_alive = False
            self._ready_event.set()

    def capture(self, url: str, timeout_seconds: float = 12.0) -> bytes:
        with self.lock:
            if not self._is_alive or not self.thread.is_alive():
                self._start_thread()
        if not self._ready_event.wait(timeout=10.0):
            raise TimeoutError("Chromium startup timed out")
        res_q = queue.Queue()
        self.req_queue.put((url, int(timeout_seconds * 1000), res_q))
        success, res = res_q.get(timeout=timeout_seconds + 3.0)
        if not success:
            raise res
        return res


_chromium_daemon = None


def get_chromium_daemon():
    global _chromium_daemon
    if _chromium_daemon is None:
        _chromium_daemon = ChromiumCaptureDaemon()
    return _chromium_daemon


def generate_fallback_hud_svg(target_url: str, message: str = "LIVE HUD PREVIEW READY") -> bytes:
    escaped_url = target_url.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg width="1024" height="620" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#040916"/>
      <stop offset="50%" stop-color="#061226"/>
      <stop offset="100%" stop-color="#02040a"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="620" fill="url(#bg)"/>
  <rect x="20" y="20" width="984" height="580" fill="none" stroke="#00e5ff" stroke-width="1.5" stroke-opacity="0.3" rx="8"/>
  <rect x="25" y="25" width="974" height="570" fill="none" stroke="#00e5ff" stroke-width="0.5" stroke-dasharray="8 4" stroke-opacity="0.2"/>
  <text x="512" y="160" text-anchor="middle" fill="#00e5ff" font-family="monospace" font-size="26" font-weight="bold" letter-spacing="4">
    // STARK HUD SATELLITE RELAY
  </text>
  <circle cx="512" cy="270" r="45" fill="none" stroke="#00e5ff" stroke-width="2" stroke-opacity="0.6"/>
  <circle cx="512" cy="270" r="35" fill="none" stroke="#00e5ff" stroke-width="1" stroke-dasharray="6 3"/>
  <polygon points="512,250 528,280 496,280" fill="#00e5ff" opacity="0.8"/>
  <text x="512" y="370" text-anchor="middle" fill="#ffffff" font-family="monospace" font-size="16" font-weight="bold">
    {message}
  </text>
  <text x="512" y="405" text-anchor="middle" fill="#38bdf8" font-family="monospace" font-size="13">
    TARGET: {escaped_url}
  </text>
  <text x="512" y="445" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-family="monospace" font-size="11">
    [ Click &quot;Launch on PC ↗&quot; in header to interact directly in Chrome/Edge ]
  </text>
</svg>"""
    return svg.encode("utf-8")


@app.get("/api/browser/preview")
async def browser_preview(url: str = "https://www.google.com"):
    """Capture live web preview using Playwright Chromium."""
    clean_url = url.strip()
    if not clean_url:
        clean_url = "https://www.google.com"
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    try:
        daemon = get_chromium_daemon()
        screenshot_bytes = await asyncio.to_thread(daemon.capture, clean_url, 12.0)
        return Response(content=screenshot_bytes, media_type="image/jpeg")
    except Exception as e:
        print(f"Browser preview notice for {clean_url}: {e}")
        fallback_svg = generate_fallback_hud_svg(clean_url, "STREAM READY — CLICK LAUNCH ON PC TO INTERACT")
        return Response(content=fallback_svg, media_type="image/svg+xml")


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    if not req.messages:
        return {"reply": "Standing by, sir.", "status": "ok"}

    last_user_msg = req.messages[-1].content.strip()

    # 1. Check if user is asking to open a website, browser, or app
    intent = execute_system_intent(last_user_msg)
    if intent["success"]:
        return {
            "reply": intent["reply"],
            "status": "ok",
            "system_action": intent,
        }

    # 2. General LLM Query via Groq
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key not configured")

    payload_messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
    for m in req.messages[-10:]:
        payload_messages.append({"role": m.role, "content": m.content})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "JarvisBackend/1.0",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": payload_messages,
        "temperature": 0.6,
        "max_tokens": 200,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                fallback_payload = {**payload, "model": "qwen/qwen3.8-27b"}
                resp = await client.post(GROQ_API_URL, json=fallback_payload, headers=headers)

            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return {"reply": reply, "status": "ok"}
    except Exception as e:
        print(f"LLM proxy error: {e}")
        return {
            "reply": "I am standing by, sir. All core diagnostics are nominal.",
            "error": str(e),
            "status": "error",
        }
