import os
import sys
import re
import time
import base64
import urllib.parse
import asyncio
import queue
import threading
import logging
import json
import mimetypes
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import AsyncGenerator
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
WORKSPACE_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Setup Multi-Destination Persistent Logging
LOG_FILE = BASE_DIR / "backend.log"
WORKSPACE_LOG_FILE = WORKSPACE_ROOT / "backend.log"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

log_formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# StreamHandler for console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(console_handler)

# RotatingFileHandler for backend directory
try:
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
except Exception as e:
    print(f"Notice: Failed to initialize file logger at {LOG_FILE}: {e}")

# RotatingFileHandler for workspace root directory
if WORKSPACE_LOG_FILE != LOG_FILE:
    try:
        ws_file_handler = RotatingFileHandler(
            str(WORKSPACE_LOG_FILE), maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        ws_file_handler.setFormatter(log_formatter)
        root_logger.addHandler(ws_file_handler)
    except Exception:
        pass

logger = logging.getLogger("jarvis.backend")
logger.info("=" * 65)
logger.info("  J.A.R.V.I.S. Autonomous AI Backend Initialized")
logger.info(f"  Logging destinations: {LOG_FILE} | {WORKSPACE_LOG_FILE}")
logger.info("=" * 65)

# Fast failover cooldown for OpenAI 429 quota exhaustion to prevent 2-3s silent delays
_openai_quota_cooldown_until: float = 0.0

from typing import Any

try:
    from app.agent_brain import (
        get_system_telemetry,
        manage_workspace_files,
        parse_and_execute_multitask,
        check_and_handle_safety_confirmation,
        close_application,
    )
    from app.system_controller import open_url, launch_app, execute_system_intent, resolve_natural_intent
    from app.persistent_memory import (
        init_database,
        verify_and_repair_database,
        start_session,
        close_session,
        get_recent_conversations,
        save_conversation_turn,
        get_all_preferences,
        set_preference,
        get_preference,
        list_tasks,
        create_task,
        update_task_status,
        delete_task,
        get_memories,
        save_memory,
        delete_memory,
        create_backup_snapshot,
        list_backups,
        restore_backup,
        is_windows_autostart_enabled,
        enable_windows_autostart,
        disable_windows_autostart,
        get_last_session_info,
        get_biometric_consent,
        set_biometric_consent,
        purge_all_biometrics,
        create_or_get_coding_session,
        list_coding_sessions,
        get_coding_session,
        get_coding_messages,
        restore_latest_backup,
        WORKSPACE_ROOT,
    )
    from app.biometric_engine import (
        identity_manager,
        decode_base64_image,
    )
    from app.skills import skills_registry
    from app.coding_engine import coding_engine
except ImportError:
    from skills import skills_registry
    from coding_engine import coding_engine
    from agent_brain import (
        get_system_telemetry,
        manage_workspace_files,
        parse_and_execute_multitask,
        check_and_handle_safety_confirmation,
        close_application,
    )
    from system_controller import open_url, launch_app, execute_system_intent, resolve_natural_intent
    from persistent_memory import (
        init_database,
        verify_and_repair_database,
        start_session,
        close_session,
        get_recent_conversations,
        save_conversation_turn,
        get_all_preferences,
        set_preference,
        get_preference,
        list_tasks,
        create_task,
        update_task_status,
        delete_task,
        get_memories,
        save_memory,
        delete_memory,
        create_backup_snapshot,
        list_backups,
        restore_backup,
        is_windows_autostart_enabled,
        enable_windows_autostart,
        disable_windows_autostart,
        get_last_session_info,
        get_biometric_consent,
        set_biometric_consent,
        purge_all_biometrics,
        create_or_get_coding_session,
        list_coding_sessions,
        get_coding_session,
        get_coding_messages,
        restore_latest_backup,
        WORKSPACE_ROOT,
    )
    from biometric_engine import (
        identity_manager,
        decode_base64_image,
    )


app = FastAPI(title="Jarvis Backend", version="0.5.0")

# Register CAD Engine API router
try:
    from app.cad_api import router as cad_router
    logger.info(f"[CAD] CAD router has {len(cad_router.routes)} routes")
    app.include_router(cad_router)
    logger.info(f"[CAD] CAD Engine API router registered. App now has {len(app.routes)} routes")
except Exception as e:
    logger.warning(f"[CAD] Failed to register CAD API router: {e}")

# Register Image Processing API router
try:
    from app.image_api import router as image_router
    logger.info(f"[IMAGE] Image router has {len(image_router.routes)} routes")
    app.include_router(image_router)
    logger.info(f"[IMAGE] Image Processing API router registered")
except Exception as e:
    logger.warning(f"[IMAGE] Failed to register Image API router: {e}")

# Register Database API router
try:
    from app.database_api import router as database_router
    logger.info(f"[DATABASE] Database router has {len(database_router.routes)} routes")
    app.include_router(database_router)
    logger.info(f"[DATABASE] Database API router registered")
except Exception as e:
    logger.warning(f"[DATABASE] Failed to register Database API router: {e}")
    import traceback
    logger.warning(f"[CAD] Traceback: {traceback.format_exc()}")

# Register Ethical Hacking API router
try:
    from app.ethical_hacking_api import router as ethical_hacking_router
    logger.info(f"[ETHICAL_HACKING] Ethical Hacking router has {len(ethical_hacking_router.routes)} routes")
    app.include_router(ethical_hacking_router)
    logger.info(f"[ETHICAL_HACKING] Ethical Hacking API router registered")
except Exception as e:
    logger.warning(f"[ETHICAL_HACKING] Failed to register Ethical Hacking API router: {e}")
    import traceback
    logger.warning(f"[ETHICAL_HACKING] Traceback: {traceback.format_exc()}")

# Register Cybersecurity API router
try:
    from app.cybersecurity_api import router as cybersecurity_router
    logger.info(f"[CYBERSECURITY] Cybersecurity router has {len(cybersecurity_router.routes)} routes")
    app.include_router(cybersecurity_router)
    logger.info(f"[CYBERSECURITY] Cybersecurity API router registered")
except Exception as e:
    logger.warning(f"[CYBERSECURITY] Failed to register Cybersecurity API router: {e}")
    import traceback
    logger.warning(f"[CYBERSECURITY] Traceback: {traceback.format_exc()}")

# Register new JARVIS capabilities API router (policy, observability,
# asset graph, industrial, twin, PLC, maintenance, knowledge, capabilities)
try:
    from app.new_capabilities_api import router as capabilities_router
    logger.info(f"[CAPABILITIES] New-capabilities router has {len(capabilities_router.routes)} routes")
    app.include_router(capabilities_router)
    logger.info(f"[CAPABILITIES] New capabilities API router registered. App now has {len(app.routes)} routes")
except Exception as e:
    logger.warning(f"[CAPABILITIES] Failed to register new capabilities API router: {e}")
    import traceback
    logger.warning(f"[CAPABILITIES] Traceback: {traceback.format_exc()}")

@app.on_event("startup")
def on_startup():
    verify_and_repair_database()
    init_database()
    start_session()
    print("Jarvis Persistent Memory & Session State restored successfully.")
    # Pre-load the cloned-voice Pocket-TTS engine so the first spoken reply
    # does not stall the UI waiting for model weights. Every reply - English,
    # Hindi, Marathi - is voiced by this single cloned JARVIS speaker.
    try:
        try:
            from app.tts_service import warm_up
        except ImportError:
            from tts_service import warm_up
        warm_up()
    except Exception as exc:
        print(f"TTS warm-up skipped: {exc}")

@app.on_event("shutdown")
def on_shutdown():
    close_session("Graceful shutdown")
    try:
        create_backup_snapshot()
    except Exception:
        pass
    print("Jarvis session saved and backup snapshot created.")

# Load environment variables from .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")
OPENAI_RESPONSES_API_URL = os.getenv("OPENAI_RESPONSES_API_URL", "https://api.openai.com/v1/responses")

def get_openai_credentials() -> tuple[str | None, str, str]:
    """Dynamically get OpenAI API credentials from environment or .env file."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-6-astra")
    url = os.getenv("OPENAI_RESPONSES_API_URL", "https://api.openai.com/v1/responses")
    if not api_key and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k_clean = k.strip()
                v_clean = v.strip()
                if k_clean == "OPENAI_API_KEY":
                    api_key = v_clean
                elif k_clean == "OPENAI_MODEL":
                    model = v_clean
                elif k_clean == "OPENAI_RESPONSES_API_URL":
                    url = v_clean
    return api_key, model, url

POCKET_TTS_SERVE_URL = os.getenv("POCKET_TTS_SERVE_URL", "http://127.0.0.1:8001/tts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Minimal noise for frequent status polling
    is_frequent_poll = path in ["/api/system/telemetry", "/api/health", "/api/biometrics/status"]

    if not is_frequent_poll:
        logger.info(f"[HTTP INCOMING] {method} {path} from {client_ip}")

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 1)
        if not is_frequent_poll or duration_ms > 300:
            logger.info(f"[HTTP COMPLETED] {method} {path} - {response.status_code} ({duration_ms}ms)")
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 1)
        logger.error(f"[HTTP FAILED] {method} {path} ({duration_ms}ms): {exc}", exc_info=True)
        raise

@app.get("/api/logs")
def get_logs_endpoint(lines: int = 100) -> dict:
    """Retrieve the most recent backend log entries for debugging and verification."""
    if not LOG_FILE.exists():
        return {"status": "ok", "lines": [], "path": str(LOG_FILE), "total_lines": 0}
    try:
        content = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = content[-lines:]
        return {
            "status": "ok",
            "total_lines": len(content),
            "returned_lines": len(tail),
            "log_path": str(LOG_FILE),
            "lines": tail,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



class MessageItem(BaseModel):
    role: str
    content: str


class AttachmentRef(BaseModel):
    filename: str = ""
    path: str = ""
    mime_type: str = ""


class ChatRequest(BaseModel):
    messages: list[MessageItem]
    selected_feature_id: str | None = None
    attachments: list[AttachmentRef] | None = None


class TTSRequest(BaseModel):
    text: str
    emotion: str | None = None


class SystemOpenRequest(BaseModel):
    target: str
    type: str = "auto"  # "url", "app", "auto"


class SafetyConfirmRequest(BaseModel):
    decision: str  # "confirm" | "cancel"


class FileManageRequest(BaseModel):
    action: str  # "list" | "read" | "save_note" | "search"
    target: str = ""
    content: str = ""


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: str = ""


class TaskUpdateRequest(BaseModel):
    status: str


class MemoryCreateRequest(BaseModel):
    title: str
    content: str
    category: str = "general"
    importance: int = 1


class PreferenceUpdateRequest(BaseModel):
    key: str
    value: Any


class RestoreRequest(BaseModel):
    filename: str


class AutostartToggleRequest(BaseModel):
    enable: bool


class BiometricConsentRequest(BaseModel):
    user_id: str = "owner"
    consent: bool


class BiometricFaceVerifyRequest(BaseModel):
    image: str  # base64 data-url or base64 raw string


class BiometricFaceEnrollRequest(BaseModel):
    image: str
    user_id: str = "owner"
    display_name: str = "Tony Stark"


class BiometricVoiceEnrollRequest(BaseModel):
    audio: str  # base64 encoded audio
    user_id: str = "owner"
    display_name: str = "Tony Stark"


class BiometricVoiceVerifyRequest(BaseModel):
    audio: str


class BiometricSwitchRequest(BaseModel):
    role: str
    display_name: str = ""


class CodingChatRequest(BaseModel):
    session_id: str = "default_coding"
    message: str
    active_file: str = ""
    auto_run_tools: bool = True


class CodingSessionNewRequest(BaseModel):
    title: str = "New Coding Task"
    active_file: str = ""


class SkillToggleRequest(BaseModel):
    skill_id: str
    enabled: bool


class FileSaveRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = True


class RollbackRequest(BaseModel):
    path: str


class RunTerminalRequest(BaseModel):
    command: str
    cwd: str = "."
    timeout: int = 30


class FileUploadRequest(BaseModel):
    filename: str
    content_base64: str
    mime_type: str = "application/octet-stream"
    category: str = "file"


JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's sophisticated AI companion.
Tone: Highly polite, articulate, composed, intelligent, with a refined British manner.
Language Capabilities: You are fully multilingual and naturally converse in English, Marathi (मराठी), Hindi (हिंदी), Hinglish, Marathlish, and code-mixed vernacular phrasing.
Always understand the user's intent naturally without requiring rigid commands.
When the user speaks or writes in Marathi, respond with articulate, polite Marathi (or British-polite bilingual phrasing).
When the user speaks in Hindi, respond with polite, respectful Hindi.
When the user speaks in English or mixed languages, respond in kind.
Keep answers concise (1-2 sentences) ideal for spoken voice.
When confirming system actions (camera, YouTube, music, apps, browser), articulate that you are launching them directly on the system."""


@app.get("/api/health")
def health() -> dict:
    openai_key, openai_model, openai_url = get_openai_credentials()
    active_llm = "openai (gpt-6-astra)" if openai_key else ("gemini" if GEMINI_API_KEY else ("groq" if GROQ_API_KEY else "none"))
    return {
        "status": "ok",
        "service": "jarvis-backend",
        "llm_provider": active_llm,
        "openai_model": openai_model if openai_key else None,
        "openai_ready": bool(openai_key),
        "openai_responses_api": "active" if openai_key else "not_configured",
        "gemini_model": GEMINI_MODEL if GEMINI_API_KEY else None,
        "gemini_ready": bool(GEMINI_API_KEY),
        "groq_model": GROQ_MODEL,
        "groq_ready": bool(GROQ_API_KEY),
        "tts_engine": "pocket-tts (in-process cloned JARVIS voice)",
        "tts_serve_url": POCKET_TTS_SERVE_URL,
        "tts_voice_identity": "single cloned voice for en / hi / mr replies",
        "cloned_voice": "JARVIS - Marvel's Iron Man 3",
        "system_automation": "enabled",
        "chromium_engine": "ready",
        "persistent_storage": "sqlite-wal",
        "autostart_configured": is_windows_autostart_enabled(),
        "version": "0.5.0",
    }


async def query_openai_responses_llm(messages: list[MessageItem], prompt_instruction: str = JARVIS_SYSTEM_PROMPT, max_tokens: int = 250) -> str:
    """Query OpenAI via the Responses API or Chat completions with fast failover."""
    global _openai_quota_cooldown_until
    if time.time() < _openai_quota_cooldown_until:
        raise ValueError("OpenAI API in cooldown (skipping to eliminate latency)")

    api_key, model, responses_url = get_openai_credentials()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    input_items = []
    for m in messages[-10:]:
        role = "user" if m.role == "user" else "assistant"
        input_items.append({"role": role, "content": m.content})

    payload = {
        "model": model,
        "instructions": prompt_instruction,
        "input": input_items,
        "max_output_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=2.5) as client:
        try:
            resp = await client.post(responses_url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text_content = ""
                if "output" in data and isinstance(data["output"], list):
                    for item in data["output"]:
                        if isinstance(item, dict):
                            if item.get("type") == "message" and "content" in item:
                                for c in item["content"]:
                                    if isinstance(c, dict) and c.get("text"):
                                        text_content += c["text"]
                            elif item.get("text"):
                                text_content += item["text"]
                elif "output_text" in data:
                    text_content = data["output_text"]
                elif "choices" in data and len(data["choices"]) > 0:
                    text_content = data["choices"][0].get("message", {}).get("content", "")

                if text_content.strip():
                    return text_content.strip()
            elif resp.status_code in [400, 401, 403, 404, 429]:
                _openai_quota_cooldown_until = time.time() + 3600.0
                raise ValueError(f"OpenAI API unavailable (HTTP {resp.status_code}). Fast failover active.")
            else:
                resp.raise_for_status()
        except ValueError:
            raise
        except Exception:
            if time.time() < _openai_quota_cooldown_until:
                raise
            # Fast fallback to standard OpenAI chat completions endpoint
            chat_url = "https://api.openai.com/v1/chat/completions"
            chat_messages = [{"role": "system", "content": prompt_instruction}]
            for m in messages[-10:]:
                chat_messages.append({"role": "user" if m.role == "user" else "assistant", "content": m.content})
            chat_payload = {
                "model": model if model != "gpt-6-astra" else "gpt-4o-mini",
                "messages": chat_messages,
                "max_tokens": max_tokens,
                "temperature": 0.5,
            }
            chat_resp = await client.post(chat_url, headers=headers, json=chat_payload)
            if chat_resp.status_code in [400, 401, 403, 404, 429]:
                _openai_quota_cooldown_until = time.time() + 3600.0
                raise ValueError(f"OpenAI chat unavailable (HTTP {chat_resp.status_code}). Fast failover active.")
            chat_resp.raise_for_status()
            data = chat_resp.json()
            return data["choices"][0]["message"]["content"].strip()



def _gemini_inline_image_parts(image_paths: list[str]) -> list[dict]:
    parts = []
    for p in image_paths[:2]:
        try:
            blob = Path(p).read_bytes()
            if len(blob) > 4 * 1024 * 1024:
                continue
            parts.append({"inline_data": {
                "mime_type": "image/jpeg" if Path(p).suffix.lower() in (".jpg", ".jpeg") else "image/png",
                "data": base64.b64encode(blob).decode(),
            }})
        except Exception:
            continue
    return parts


async def query_gemini_llm(messages: list[MessageItem], prompt_instruction: str = JARVIS_SYSTEM_PROMPT,
                           max_tokens: int = 200, inline_image_paths: list[str] | None = None) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    contents = []
    for m in messages[-10:]:
        role = "user" if m.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.content}]})

    if inline_image_paths and contents and contents[-1]["role"] == "user":
        contents[-1]["parts"] = _gemini_inline_image_parts(inline_image_paths) + contents[-1]["parts"]

    payload = {
        "system_instruction": {
            "parts": [{"text": prompt_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": max_tokens,
        }
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_MR_MARKERS_RE = re.compile(
    r"[\u0933\u0934]|आहे|आहेत|करा|करो|नाही|नको|काय|मी |तुम्ही|आपण|झाले|सर|कसा|कशी",
    re.IGNORECASE,
)


def detect_text_language(text: str) -> str | None:
    """Best-effort ISO language guess (en / hi / mr) for a transcript.

    Whisper sometimes omits the detected language, and typed commands never
    carry one - this keeps automatic English / Hindi / Marathi switching working.
    """
    text = (text or "").strip()
    if not text:
        return None
    if _DEVANAGARI_RE.search(text):
        return "mr" if _MR_MARKERS_RE.search(text) else "hi"
    return "en"


@app.post("/api/voice/transcribe")
async def voice_transcribe_endpoint(file: UploadFile = File(...)):
    """Transcribe user's spoken voice using Groq Whisper Large v3 Turbo (supports English, Marathi, Hindi, and mixed languages)."""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured for voice transcription")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    filename = file.filename or "recording.webm"
    mime_type = file.content_type or "audio/webm"

    try:
        try:
            from app.audio_preprocessing import preprocess_audio
            audio_bytes, audio_stats = preprocess_audio(audio_bytes)
            print(f"Audio preprocessed: SNR={audio_stats.snr_estimate:.1f}dB, duration={audio_stats.processed_duration:.2f}s")
        except ImportError:
            pass
        except Exception as e:
            print(f"Audio preprocessing failed (continuing with raw audio): {e}")

        async with httpx.AsyncClient(timeout=25.0) as client:
            files = {"file": (filename, audio_bytes, mime_type)}
            # verbose_json makes Whisper report which language it heard, which the
            # frontend uses to keep speech recognition locked onto the user's language.
            data = {"model": "whisper-large-v3-turbo", "response_format": "verbose_json"}
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files=files,
                data=data
            )
            if resp.status_code != 200:
                print(f"Whisper transcription status {resp.status_code}: {resp.text[:300]}")
                # Some model/plan combos reject verbose_json - retry with the default shape.
                data = {"model": "whisper-large-v3-turbo"}
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files=files,
                    data=data,
                )
            if resp.status_code != 200:
                logger.error(f"Whisper transcription failed ({resp.status_code}): {resp.text[:300]}")
                raise HTTPException(status_code=resp.status_code, detail="Speech transcription service error")

            res_json = resp.json()
            transcribed_text = res_json.get("text", "").strip()
            whisper_language = (res_json.get("language") or "").strip() or None
            
            # Use enhanced language detection with confidence scoring
            try:
                from app.language_detection import detect_language, get_speech_lang_code
                detection = detect_language(transcribed_text)
                language = get_speech_lang_code(detection)
                confidence = detection.confidence
                code_switching = detection.code_switching
            except ImportError:
                # Fallback to basic detection
                language = whisper_language or detect_text_language(transcribed_text)
                confidence = 0.5
                code_switching = False

            # Classify voice command intent
            intent_data = {}
            try:
                from app.intent_classification import classify_intent
                intent_result = classify_intent(transcribed_text)
                intent_data = {
                    "intent": intent_result.intent.value,
                    "intent_confidence": intent_result.confidence,
                    "primary_intent": intent_result.primary_intent.value,
                    "secondary_intent": intent_result.secondary_intent.value if intent_result.secondary_intent else None,
                    "entities": intent_result.entities,
                    "is_multi_intent": intent_result.is_multi_intent,
                }

                # Handle CAD-specific commands
                if intent_result.intent.value == "cad_modeling":
                    try:
                        from app.cad_voice_handler import cad_command_handler
                        import httpx

                        cad_action = cad_command_handler.parse_cad_command(transcribed_text)
                        if cad_action:
                            intent_data["cad_action"] = cad_action
                            intent_data["cad_response"] = cad_command_handler.generate_response(cad_action)

                            # Execute CAD API call asynchronously
                            async def execute_cad_command(action: dict):
                                try:
                                    async with httpx.AsyncClient(timeout=10.0) as client:
                                        if action["action"] == "create_primitive":
                                            # Call CAD API to create primitive (using query params)
                                            primitive_type = action["primitive_type"]
                                            dimensions = action.get("dimensions", {})
                                            
                                            # Build query params
                                            params = {}
                                            if "width" in dimensions:
                                                params["width"] = dimensions["width"]
                                            if "height" in dimensions:
                                                params["height"] = dimensions["height"]
                                            if "depth" in dimensions:
                                                params["depth"] = dimensions["depth"]
                                            if "radius" in dimensions:
                                                params["radius"] = dimensions["radius"]
                                            
                                            # Map primitive type to endpoint
                                            endpoint_map = {
                                                "box": "/api/cad/primitive/box",
                                                "cylinder": "/api/cad/primitive/cylinder",
                                                "sphere": "/api/cad/primitive/sphere",
                                                "cone": "/api/cad/primitive/cone",
                                                "torus": "/api/cad/primitive/torus",
                                            }
                                            
                                            endpoint = endpoint_map.get(primitive_type)
                                            if endpoint:
                                                resp = await client.post(
                                                    f"http://localhost:8000{endpoint}",
                                                    params=params
                                                )
                                                if resp.status_code == 200:
                                                    return {"success": True, "result": resp.json()}
                                                return {"success": False, "error": resp.text}
                                            return {"success": False, "error": f"Unknown primitive type: {primitive_type}"}

                                        elif action["action"] == "navigate":
                                            if action["navigation"] == "open_cad":
                                                return {"success": True, "message": "CAD viewport opened"}

                                        elif action["action"] == "perform_operation":
                                            # Map operation to CAD API endpoint
                                            operation = action["operation"]
                                            params = action.get("parameters", {})
                                            
                                            operation_map = {
                                                "extrude": "/api/cad/feature/extrude",
                                                "revolve": "/api/cad/feature/revolve",
                                                "fillet": "/api/cad/feature/fillet",
                                                "chamfer": "/api/cad/feature/chamfer",
                                                "shell": "/api/cad/feature/shell",
                                            }
                                            
                                            endpoint = operation_map.get(operation)
                                            if endpoint:
                                                resp = await client.post(
                                                    f"http://localhost:8000{endpoint}",
                                                    params=params
                                                )
                                                if resp.status_code == 200:
                                                    return {"success": True, "result": resp.json()}
                                                return {"success": False, "error": resp.text}

                                    return {"success": False, "error": "Operation not implemented"}
                                except Exception as e:
                                    logger.error(f"CAD command execution failed: {e}")
                                    return {"success": False, "error": str(e)}

                            # Execute CAD command
                            cad_result = await execute_cad_command(cad_action)
                            intent_data["cad_execution"] = cad_result

                    except Exception as e:
                        logger.warning(f"CAD voice handler failed: {e}")

                # Handle Ethical Hacking commands
                if intent_result.intent.value == "ethical_hacking":
                    try:
                        from app.ethical_hacking_voice_handler import (
                            parse_ethical_hacking_command,
                            generate_response,
                        )
                        from app.ethical_hacking import (
                            get_ethical_hacking_engine,
                            get_recon_scanner,
                            get_vuln_assessor,
                            get_web_security_tester,
                            get_network_security_assessor,
                            get_config_security_auditor,
                            get_auth_security_auditor,
                            get_misconfig_detector,
                            get_report_generator,
                        )

                        eh_command = parse_ethical_hacking_command(transcribed_text)
                        if eh_command:
                            cmd = eh_command["command"]
                            target = eh_command.get("target")
                            engine = get_ethical_hacking_engine()

                            if cmd == "get_status":
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True,
                                    "data": {"stats": engine.get_stats()},
                                })
                            elif cmd == "create_scope" and target:
                                scope = engine.create_test_scope(
                                    name=f"Voice-{target}", targets=[target],
                                    authorized_by="voice_user",
                                )
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": {"scope": scope},
                                })
                            elif cmd == "port_scan" and target:
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_recon_scanner().port_scan(target, scope_id=scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": result.get("success", False),
                                    "data": result, "error": result.get("error"),
                                })
                            elif cmd == "vuln_assess" and target:
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_vuln_assessor().assess_host(target, scope_id=scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": result.get("success", False),
                                    "data": result, "error": result.get("error"),
                                })
                            elif cmd == "network_assess":
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_network_security_assessor().comprehensive_network_assessment(scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "config_audit":
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_config_security_auditor().comprehensive_config_audit(scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "auth_audit":
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_auth_security_auditor().comprehensive_auth_audit(scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "misconfig_check":
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_misconfig_detector().comprehensive_misconfig_check(scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "check_firewall":
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_network_security_assessor().check_firewall_status(scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "check_secrets" and target:
                                scopes = engine.get_active_scopes()
                                scope_id = scopes[0]["id"] if scopes else None
                                result = get_misconfig_detector().detect_exposed_secrets(target, scope_id)
                                intent_data["eh_response"] = generate_response({
                                    "command": cmd, "success": True, "data": result,
                                })
                            elif cmd == "generate_report":
                                scopes = engine.get_active_scopes()
                                if scopes:
                                    result = get_report_generator().generate_report(scopes[0]["id"])
                                    intent_data["eh_response"] = generate_response({
                                        "command": cmd, "success": result.get("success", False),
                                        "data": result,
                                    })
                                else:
                                    intent_data["eh_response"] = "No active test scope. Create a scope first."
                            else:
                                intent_data["eh_response"] = generate_response({
                                    "command": "get_status", "success": True,
                                    "data": {"stats": engine.get_stats()},
                                })

                    except Exception as e:
                        logger.warning(f"Ethical hacking voice handler failed: {e}")

                # Handle Cybersecurity commands
                if intent_result.intent.value == "cybersecurity":
                    try:
                        from app.cybersecurity_voice_handler import (
                            parse_cybersecurity_command,
                            generate_response,
                        )
                        from app.cybersecurity import (
                            get_threat_detection_engine,
                            get_windows_endpoint_security,
                            get_network_security_monitor,
                            get_vulnerability_scanner,
                            get_web_application_analyzer,
                            get_secure_code_analyzer,
                            get_dependency_scanner,
                            get_file_integrity_monitor,
                            get_malware_analyzer,
                            get_log_analyzer,
                            get_secret_scanner,
                            get_database_auditor,
                            get_alert_manager,
                            get_incident_response_engine,
                            get_backup_verifier,
                            get_privacy_protection,
                            get_security_knowledge_base,
                            get_report_generator,
                            get_security_orchestrator,
                        )

                        cs_command = parse_cybersecurity_command(transcribed_text)
                        if cs_command:
                            cmd = cs_command["command"]
                            target = cs_command.get("target")

                            if cmd == "get_status":
                                orch = get_security_orchestrator()
                                alert_mgr = get_alert_manager()
                                summary = alert_mgr.get_alert_summary()
                                intent_data["cyber_response"] = generate_response({
                                    "command": cmd, "success": True,
                                    "stats": {
                                        "active_alerts": summary.get("total_active", 0),
                                        "open_vulnerabilities": 0,
                                        "total_events": 0,
                                        **orch.get_orchestrator_stats(),
                                    },
                                })
                            elif cmd == "threat_scan":
                                result = get_threat_detection_engine().comprehensive_threat_scan()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "endpoint_check":
                                result = get_windows_endpoint_security().comprehensive_endpoint_check()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "network_check":
                                result = get_network_security_monitor().comprehensive_network_check()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "vulnerability_scan":
                                result = get_vulnerability_scanner().comprehensive_vulnerability_scan()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "web_security" and target:
                                result = get_web_application_analyzer().analyze_web_application(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "code_scan" and target:
                                result = get_secure_code_analyzer().scan_project(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "dependency_scan" and target:
                                result = get_dependency_scanner().comprehensive_dependency_scan(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "integrity_check":
                                result = get_file_integrity_monitor().comprehensive_integrity_check()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "malware_analysis" and target:
                                result = get_malware_analyzer().comprehensive_file_analysis(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "log_analysis":
                                result = get_log_analyzer().comprehensive_log_analysis()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "secret_scan" and target:
                                result = get_secret_scanner().comprehensive_secret_scan(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "database_audit" and target:
                                result = get_database_auditor().comprehensive_db_audit(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "privacy_scan" and target:
                                result = get_privacy_protection().scan_directory_for_pii(target)
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "get_alerts":
                                alerts = get_alert_manager().get_active_alerts()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, {"alerts": alerts},
                                )
                            elif cmd == "full_scan":
                                threat = get_threat_detection_engine().comprehensive_threat_scan()
                                endpoint = get_windows_endpoint_security().comprehensive_endpoint_check()
                                network = get_network_security_monitor().comprehensive_network_check()
                                vuln = get_vulnerability_scanner().comprehensive_vulnerability_scan()
                                integrity = get_file_integrity_monitor().comprehensive_integrity_check()
                                logs = get_log_analyzer().comprehensive_log_analysis()
                                total = (
                                    threat.get("total", 0)
                                    + vuln.get("total_vulnerabilities", 0)
                                    + integrity.get("total_issues", 0)
                                    + logs.get("total_suspicious_events", 0)
                                )
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True},
                                    {"total_findings": total},
                                )
                            elif cmd == "generate_report":
                                result = get_report_generator().generate_report("executive_summary")
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": result.get("success", False)},
                                )
                            elif cmd == "create_incident":
                                inc = get_incident_response_engine()
                                incident = inc.create_incident(
                                    title="Voice-Reported Incident",
                                    incident_type="suspicious_activity",
                                    description=f"Reported via voice: {transcribed_text}",
                                    severity="medium",
                                )
                                intent_data["cyber_response"] = f"Incident created: {incident.get('incident_id', 'unknown')}"
                            elif cmd == "backup_verify":
                                result = get_backup_verifier().verify_all_backups()
                                intent_data["cyber_response"] = generate_response(
                                    {"command": cmd, "success": True}, result,
                                )
                            elif cmd == "knowledge_query":
                                kb = get_security_knowledge_base()
                                if target and "owasp" in target.lower():
                                    result = kb.get_owasp_top_10()
                                elif target and "cwe" in target.lower():
                                    result = kb.get_all_cwes()
                                else:
                                    result = {"owasp_top_10": kb.get_owasp_top_10()}
                                intent_data["cyber_response"] = f"Security knowledge base query complete. Found information on OWASP Top 10 and {len(kb.get_all_cwes())} CWE entries."
                            else:
                                orch = get_security_orchestrator()
                                intent_data["cyber_response"] = generate_response({
                                    "command": "get_status", "success": True,
                                    "stats": orch.get_orchestrator_stats(),
                                })

                    except Exception as e:
                        logger.warning(f"Cybersecurity voice handler failed: {e}")

            except ImportError:
                pass
            except Exception as e:
                print(f"Intent classification failed: {e}")

            return {
                "status": "ok",
                "text": transcribed_text,
                "language": language,
                "confidence": confidence,
                "code_switching": code_switching,
                "whisper_language": whisper_language,
                **intent_data,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Voice transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Synthesize speech with the single cloned JARVIS voice for every language.

    The in-process engine (cloned from the JARVIS/Iron Man reference recording)
    is the primary source so the speaker identity never changes; the optional
    standalone proxy is only used if that engine is unavailable.
    """
    text_content = req.text.strip()
    if not text_content:
        text_content = "Yes, sir."

    # 1. Primary: in-process cloned JARVIS voice (English, Hindi, Marathi alike)
    try:
        try:
            from app.tts_service import synthesize_speech, Emotion
        except ImportError:
            from tts_service import synthesize_speech, Emotion

        emotion = None
        if req.emotion:
            try:
                emotion = Emotion(req.emotion)
            except ValueError:
                pass

        wav_bytes = await asyncio.to_thread(synthesize_speech, text_content, emotion)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        print(f"In-process cloned-voice synthesis error: {e}, trying `uvx pocket-tts serve` proxy")

    # 2. Fallback: standalone `uvx pocket-tts serve` instance
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                POCKET_TTS_SERVE_URL,
                data={"text": text_content},
            )
            resp.raise_for_status()
            return Response(content=resp.content, media_type="audio/wav")
    except Exception as e2:
        print(f"`uvx pocket-tts serve` proxy error: {e2}")
        raise HTTPException(status_code=500, detail=str(e2))


@app.get("/api/system/telemetry")
def telemetry_endpoint() -> dict:
    """Retrieve real-time hardware telemetry: CPU, RAM, Disk, Battery, Processes."""
    return get_system_telemetry()


@app.post("/api/system/confirm")
def safety_confirm_endpoint(req: SafetyConfirmRequest) -> dict:
    """Explicit confirmation gate for destructive or sensitive system actions."""
    res = check_and_handle_safety_confirmation(req.decision)
    if res:
        return res
    return {"success": False, "reply": "No pending safety action found, sir."}


@app.post("/api/system/files")
def files_endpoint(req: FileManageRequest) -> dict:
    """Safe workspace file management (list, read, save_note, search)."""
    return manage_workspace_files(req.action, req.target, req.content)


_WMO_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}

_weather_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}


@app.get("/api/weather")
async def weather_endpoint(lat: float = 21.1458, lon: float = 79.0817) -> dict:
    """Real current weather + hourly forecast from Open-Meteo (no API key).

    15-minute cache; 503 with honest error when the upstream is unreachable
    so the UI can show 'unavailable' instead of fabricated data.
    """
    import time as _time

    now = _time.time()
    if _weather_cache["data"] is not None and now - _weather_cache["fetched_at"] < 900:
        return _weather_cache["data"]

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "hourly": "temperature_2m,weather_code",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
            )
            resp.raise_for_status()
            raw = resp.json()

        current = raw.get("current", {})
        hourly = raw.get("hourly", {})
        today = datetime.now()
        forecast = []
        for i, iso in enumerate(hourly.get("time", [])):
            try:
                hour = int(iso[11:13])
            except (ValueError, IndexError):
                continue
            if hour <= today.hour or hour % 3 != 0:
                continue
            if len(forecast) >= 4:
                break
            code = (hourly.get("weather_code") or [])[i]
            forecast.append({
                "hour_label": f"{(hour % 12) or 12} {'PM' if hour >= 12 else 'AM'}",
                "temp": round(hourly["temperature_2m"][i]),
                "code": code,
                "label": _WMO_WEATHER_CODES.get(code, "Unknown"),
            })

        daily = raw.get("daily", {})
        code = current.get("weather_code")
        data = {
            "available": True,
            "location": {"lat": lat, "lon": lon, "timezone": raw.get("timezone", "")},
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "code": code,
            "condition": _WMO_WEATHER_CODES.get(code, "Unknown"),
            "high": (daily.get("temperature_2m_max") or [None])[0],
            "low": (daily.get("temperature_2m_min") or [None])[0],
            "forecast": forecast,
            "fetched_at": now,
        }
        _weather_cache["data"] = data
        _weather_cache["fetched_at"] = now
        return data
    except Exception as e:
        logger.warning(f"Weather fetch failed: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Weather service unreachable")


@app.post("/api/system/open")
async def system_open_endpoint(req: SystemOpenRequest):
    """Directly open URLs in default desktop browser or launch desktop apps with natural multitasking intent."""
    target = req.target.strip()
    if req.type == "url":
        success = open_url(target)
        return {"success": success, "type": "url", "target": target}
    elif req.type == "app":
        success = launch_app(target)
        return {"success": success, "type": "app", "target": target}
    else:
        result = await parse_and_execute_multitask(target)
        return result


# =========================================================================
# PERSISTENT MEMORY, TASKS, BACKUP & AUTO-START ENDPOINTS
# =========================================================================

@app.get("/api/memory/state")
def memory_state_endpoint() -> dict:
    """Retrieve full persistent snapshot: conversations, tasks, preferences, memories, autostart, and session info."""
    return {
        "status": "ok",
        "recent_conversations": get_recent_conversations(limit=40),
        "preferences": get_all_preferences(),
        "tasks": list_tasks(),
        "memories": get_memories(limit=50),
        "autostart_enabled": is_windows_autostart_enabled(),
        "last_session": get_last_session_info(),
        "backups_available": len(list_backups()),
    }


@app.post("/api/memory/preferences")
def update_preference_endpoint(req: PreferenceUpdateRequest) -> dict:
    set_preference(req.key, req.value)
    return {"status": "ok", "key": req.key, "value": req.value}


@app.get("/api/memory/tasks")
def get_tasks_endpoint(status: str | None = None) -> dict:
    return {"status": "ok", "tasks": list_tasks(status=status)}


@app.post("/api/memory/tasks")
def create_task_endpoint(req: TaskCreateRequest) -> dict:
    t = create_task(req.title, req.description, req.priority, req.due_date)
    return {"status": "ok", "task": t}


@app.patch("/api/memory/tasks/{task_id}")
def update_task_endpoint(task_id: int, req: TaskUpdateRequest) -> dict:
    success = update_task_status(task_id, req.status)
    return {"status": "ok" if success else "error", "task_id": task_id, "updated": success}


@app.delete("/api/memory/tasks/{task_id}")
def delete_task_endpoint(task_id: int) -> dict:
    success = delete_task(task_id)
    return {"status": "ok" if success else "error", "task_id": task_id, "deleted": success}


@app.get("/api/memory/memories")
def get_memories_endpoint(category: str | None = None) -> dict:
    return {"status": "ok", "memories": get_memories(category=category)}


@app.post("/api/memory/memories")
def create_memory_endpoint(req: MemoryCreateRequest) -> dict:
    mid = save_memory(req.category, req.title, req.content, req.importance)
    return {"status": "ok", "id": mid}


@app.delete("/api/memory/memories/{memory_id}")
def delete_memory_endpoint(memory_id: int) -> dict:
    success = delete_memory(memory_id)
    return {"status": "ok" if success else "error", "deleted": success}


@app.get("/api/memory/backups")
def list_backups_endpoint() -> dict:
    return {"status": "ok", "backups": list_backups()}


@app.post("/api/memory/backup")
def create_backup_endpoint() -> dict:
    res = create_backup_snapshot()
    return res


@app.post("/api/memory/restore")
def restore_backup_endpoint(req: RestoreRequest) -> dict:
    res = restore_backup(req.filename)
    return res


@app.get("/api/system/autostart")
def get_autostart_endpoint() -> dict:
    return {"status": "ok", "autostart_enabled": is_windows_autostart_enabled()}


@app.post("/api/system/autostart")
def set_autostart_endpoint(req: AutostartToggleRequest) -> dict:
    if req.enable:
        return enable_windows_autostart()
    else:
        return disable_windows_autostart()


# =========================================================================
# BIOMETRICS & NEURAL IDENTITY SECURITY ENDPOINTS
# =========================================================================

@app.get("/api/biometrics/status")
def get_biometrics_status_endpoint() -> dict:
    """Return real-time biometric state, user identity, verification confidence, and sensor statuses."""
    return identity_manager.get_state()


@app.post("/api/biometrics/consent")
def set_biometrics_consent_endpoint(req: BiometricConsentRequest) -> dict:
    """Explicitly grant or revoke biometric data processing consent."""
    set_biometric_consent(req.user_id, req.consent)
    return {"status": "ok", "user_id": req.user_id, "consent_given": req.consent}


@app.post("/api/biometrics/verify/face")
def verify_face_endpoint(req: BiometricFaceVerifyRequest) -> dict:
    """Analyze camera video frame, detect face bounding box, and match against enrolled profiles."""
    try:
        img_np = decode_base64_image(req.image)
        res = identity_manager.verify_face_frame(img_np)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e), "detected": False, "identified": False}


@app.post("/api/biometrics/enroll/face")
def enroll_face_endpoint(req: BiometricFaceEnrollRequest) -> dict:
    """Enroll facial biometric embedding (NO raw images saved on disk)."""
    try:
        img_np = decode_base64_image(req.image)
        res = identity_manager.enroll_face(img_np, user_id=req.user_id, display_name=req.display_name)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/biometrics/verify/voice")
def verify_voice_endpoint(req: BiometricVoiceVerifyRequest) -> dict:
    """Analyze speaker voice snippet and match against enrolled acoustic voice signature."""
    try:
        raw_b64 = req.audio
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        raw_audio = base64.b64decode(raw_b64)
        res = identity_manager.verify_voice_audio(raw_audio)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e), "identified": False}


@app.post("/api/biometrics/enroll/voice")
def enroll_voice_endpoint(req: BiometricVoiceEnrollRequest) -> dict:
    """Enroll acoustic speaker signature (NO raw audio saved on disk)."""
    try:
        raw_b64 = req.audio
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        raw_audio = base64.b64decode(raw_b64)
        res = identity_manager.enroll_voice(raw_audio, user_id=req.user_id, display_name=req.display_name)
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/biometrics/purge")
def purge_biometrics_endpoint() -> dict:
    """Permanently delete all stored face scans and voice embeddings."""
    return identity_manager.purge_data()


@app.post("/api/biometrics/camera/toggle")
def toggle_camera_endpoint(req: AutostartToggleRequest) -> dict:
    """Toggle camera active state indicator."""
    identity_manager.camera_active = req.enable
    return {"status": "ok", "camera_active": identity_manager.camera_active}


@app.post("/api/biometrics/user/switch")
def switch_user_endpoint(req: BiometricSwitchRequest) -> dict:
    """Switch active user profile between Owner and Guest."""
    identity_manager.role = req.role
    if req.role == "owner":
        identity_manager.display_name = req.display_name or "Tony Stark"
        identity_manager.current_user_id = "owner"
    else:
        identity_manager.display_name = req.display_name or "Guest User"
        identity_manager.current_user_id = "guest"
    return identity_manager.get_state()



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

            # AI Executive Briefing via Gemini or Groq
            if GEMINI_API_KEY:
                try:
                    ai_briefing = await query_gemini_llm(
                        [MessageItem(role="user", content=f"Executive summary for: {query}")],
                        prompt_instruction="You are J.A.R.V.I.S. Provide an exact 1 to 2 sentence executive briefing answering or summarizing the subject for Tony Stark. Direct, articulate, sophisticated.",
                        max_tokens=120
                    )
                except Exception as ex_gem:
                    print(f"Gemini briefing error: {ex_gem}")

            if not ai_briefing and GROQ_API_KEY:
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
async def browser_preview(url: str = "https://www.google.com", width: int = 1024, height: int = 620):
    """Capture live web preview using Playwright Chromium.
    
    Returns a JPEG screenshot of the requested URL. Falls back to an SVG
    placeholder with error details if the browser cannot capture the page.
    """
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
        error_msg = str(e)[:100] if str(e) else "Unknown error"
        fallback_svg = generate_fallback_hud_svg(clean_url, f"ERROR: {error_msg}")
        return Response(content=fallback_svg, media_type="image/svg+xml")


_CAD_CREATE_RE = re.compile(
    r"\b(create|make|draw|add|build|generate|model)\b[^.;]*\b(box|cube|cylinder|sphere|ball|cone|torus|donut|ring)\b",
    re.IGNORECASE,
)
_CAD_OPEN_RE = re.compile(
    r"\b(open|show|launch|display)\b[^.;]*\b(cad|3d viewport|3d workspace|modeling workspace|modeling)\b",
    re.IGNORECASE,
)


_CAD_PARAM_KW = {
    "tall": "height", "height": "height", "higher": "height",
    "wide": "width", "width": "width",
    "deep": "depth", "depth": "depth",
    "radius": "radius",
}
_CAD_PARAM_TAIL_RE = re.compile(
    r"\b(?:make|set|change|adjust|update|increase|reduce)\b[^.;]*?\b(\d+(?:\.\d+)?)\s*(?:mm|millimeters|millimetre|cm|centimeters|inch|inches)?\b[^.;]*?\b(tall|height|higher|wide|width|deep|depth|radius)\b",
    re.IGNORECASE,
)
_CAD_PARAM_LEAD_RE = re.compile(
    r"\b(?:make|set|change|adjust|update)\b[^.;]*?\b(height|width|depth|radius)\s*(?:to|=|:|at)?\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_CAD_ROTATE_RE = re.compile(r"\brotate\b[^.;]*?\b(-?\d+(?:\.\d+)?)\s*(?:°|degrees?|deg)", re.IGNORECASE)
_CAD_MOVE_RE = re.compile(r"\bmove\b[^.;]*?\b([xyz])\b\s*(?:to|=|:|at)?\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_CAD_SCALE_RE = re.compile(r"\bscale\b[^.;]*?\b(\d+(?:\.\d+)?)\s*(?:x|times|percent|%)?", re.IGNORECASE)
_CAD_DELETE_RE = re.compile(r"\b(delete|erase|remove)\b[^.;]*\b(selected|object|shape|body|feature|it)\b", re.IGNORECASE)
_CAD_MEASURE_RE = re.compile(r"\bdimensions?\b|\bmeasure\b[^.;]*\b(selected|object|it|shape|body)\b", re.IGNORECASE)
_CAD_FIT_RE = re.compile(r"\b(fit|zoom)\b[^.;]*\b(all|everything|extents|objects|view|screen)\b", re.IGNORECASE)
# Editing verbs only become CAD commands when they clearly target a 3D object.
_CAD_OBJ_HINT_RE = re.compile(
    r"\b(object|selected|shape|body|feature|it|this|box|cube|cylinder|sphere|cone|torus|viewport|model)\b",
    re.IGNORECASE,
)


def _cad_param_to_spoken(key: str, value: float) -> str:
    labels = {"height": "height", "width": "width", "depth": "depth", "radius": "radius"}
    return f"{labels.get(key, key)} {value:g} mm"


async def _try_cad_edit_command(text: str, selected_feature_id: str | None) -> dict | None:
    """Selection-scoped CAD editing: transform in the viewport, engine-backed
    parameter changes, deletion and measurement against the live document.

    Returns None when the text is not a CAD editing command. Transform results
    are executed by the frontend viewport (scene placement is a viewport
    concern); every engine-backed operation is verified against the active
    document before reporting success.
    """
    if _CAD_FIT_RE.search(text):
        return {
            "reply": "Framing the viewport to all objects, sir.",
            "status": "ok",
            "cad_action": {"action": "viewport", "op": "fit"},
            "via": "cad",
        }

    param_match = _CAD_PARAM_TAIL_RE.search(text) or (
        _CAD_PARAM_LEAD_RE.search(text) if _CAD_OBJ_HINT_RE.search(text) else None
    )
    rotate_m = _CAD_ROTATE_RE.search(text) and _CAD_OBJ_HINT_RE.search(text)
    move_m = _CAD_MOVE_RE.search(text) and _CAD_OBJ_HINT_RE.search(text)
    scale_m = _CAD_SCALE_RE.search(text) and _CAD_OBJ_HINT_RE.search(text)
    delete_m = _CAD_DELETE_RE.search(text)
    measure_m = _CAD_MEASURE_RE.search(text)

    if not any([param_match, rotate_m, move_m, scale_m, delete_m, measure_m]):
        return None

    from app.cad_engine.core.document import get_active_document

    doc = None
    try:
        doc = get_active_document()
    except Exception:
        doc = None

    feature = None
    if doc is not None and selected_feature_id:
        feature = doc.get_feature(selected_feature_id)
    if not selected_feature_id:
        return {
            "reply": "Please click an object in the CAD viewport to select it first, sir.",
            "status": "ok",
            "via": "cad",
        }
    if feature is None:
        return {
            "reply": "The selected object is no longer present in the active document, sir.",
            "status": "error",
            "via": "cad",
        }

    name = feature.name

    # --- Engine-backed operations (verified against the CAD document) ---
    if param_match:
        if _CAD_PARAM_TAIL_RE.search(text):
            key = _CAD_PARAM_KW.get(param_match.group(2).lower(), param_match.group(2).lower())
            value = float(param_match.group(1))
        else:
            key = _CAD_PARAM_KW.get(param_match.group(1).lower(), param_match.group(1).lower())
            value = float(param_match.group(2))
        try:
            from app.cad_api import update_parameters

            new_params = dict(feature.parameters)
            new_params[key] = value
            result = await update_parameters(selected_feature_id, new_params)
            if result.get("success") and result.get("regenerated"):
                return {
                    "reply": f"{name.capitalize()} rebuilt with {_cad_param_to_spoken(key, value)}, sir.",
                    "status": "ok",
                    "cad_action": {"action": "refresh_viewport", "feature_id": selected_feature_id},
                    "via": "cad",
                }
            return {
                "reply": f"{key.capitalize()} stored as {value:g} mm, but the geometry could not be rebuilt from parameters, sir.",
                "status": "ok",
                "cad_action": {"action": "refresh_viewport", "feature_id": selected_feature_id},
                "via": "cad",
            }
        except Exception as e:
            logger.error(f"[CAD] Chat parameter update failed: {e}")
            detail = getattr(e, "detail", str(e))
            return {
                "reply": f"I could not apply the {key} change, sir. The CAD engine reported: {detail}",
                "status": "error",
                "via": "cad",
            }

    if delete_m:
        try:
            from app.cad_api import delete_feature

            result = await delete_feature(selected_feature_id)
            if result.get("success"):
                return {
                    "reply": f"{name.capitalize()} deleted from the document, sir.",
                    "status": "ok",
                    "cad_action": {"action": "refresh_viewport", "feature_id": None},
                    "via": "cad",
                }
            return {"reply": f"The CAD engine refused to delete {name}, sir.", "status": "error", "via": "cad"}
        except Exception as e:
            logger.error(f"[CAD] Chat delete failed: {e}")
            return {"reply": f"I could not delete {name}, sir.", "status": "error", "via": "cad"}

    if measure_m:
        try:
            from app.cad_api import get_bounding_box, get_volume

            bbox = await get_bounding_box(selected_feature_id)
            b = bbox.get("bounding_box") or {}
            vol = await get_volume(selected_feature_id)
            volume = vol.get("volume")
            spoken_vol = f", volume {volume:,.0f} cubic millimetres" if isinstance(volume, (int, float)) else ""
            return {
                "reply": (
                    f"{name.capitalize()} measures {b.get('width', '?')} by {b.get('height', '?')} "
                    f"by {b.get('depth', '?')} millimetres{spoken_vol}, sir."
                ),
                "status": "ok",
                "cad_action": {"action": "measure", "feature_id": selected_feature_id},
                "via": "cad",
            }
        except Exception as e:
            logger.error(f"[CAD] Chat measurement failed: {e}")
            return {"reply": f"The CAD engine could not measure {name}, sir.", "status": "error", "via": "cad"}

    # --- Viewport transforms (executed for real by the 3D scene) ---
    if rotate_m:
        angle = float(_CAD_ROTATE_RE.search(text).group(1))
        axis = "x" if re.search(r"\b(?:about|around|on|to)?\s*(?:the\s*)?x\b", text, re.IGNORECASE) else \
               "z" if re.search(r"\b(?:about|around|on|to)?\s*(?:the\s*)?z\b", text, re.IGNORECASE) else "y"
        return {
            "reply": f"Rotating {name} {angle:g} degrees about the {axis.upper()} axis in the viewport, sir.",
            "status": "ok",
            "cad_action": {"action": "transform", "op": "rotate", "angle_deg": angle, "axis": axis, "feature_id": selected_feature_id},
            "via": "cad",
        }

    if move_m:
        mm = _CAD_MOVE_RE.search(text)
        axis = mm.group(1).lower()
        value = float(mm.group(2))
        absolute = bool(re.search(r"\bto\b|=|:", text, re.IGNORECASE))
        return {
            "reply": f"Moving {name} {'to' if absolute else 'by'} {value:g} mm on the {axis.upper()} axis, sir.",
            "status": "ok",
            "cad_action": {"action": "transform", "op": "move", "axis": axis, "value_mm": value, "absolute": absolute, "feature_id": selected_feature_id},
            "via": "cad",
        }

    if scale_m:
        factor = float(_CAD_SCALE_RE.search(text).group(1))
        if "%" in text:
            factor = factor / 100.0
        return {
            "reply": f"Scaling {name} by {factor:g}, sir.",
            "status": "ok",
            "cad_action": {"action": "transform", "op": "scale", "factor": factor, "feature_id": selected_feature_id},
            "via": "cad",
        }

    return None


async def _try_cad_command(text: str, selected_feature_id: str | None = None) -> dict | None:
    """Route CAD text & voice commands to the unified CAD Command Engine.
    Implements: VOICE/TEXT INPUT -> INTENT PARSER -> CAD COMMAND PLAN -> CURRENT CAD CONTEXT -> VALIDATION -> REAL CAD FUNCTION -> GEOMETRY ENGINE -> MODEL STATE -> VIEWPORT/UI UPDATE -> VERIFICATION -> RESULT.
    """
    if _CAD_OPEN_RE.search(text):
        return {
            "reply": "Opening the CAD engineering workspace, sir.",
            "status": "ok",
            "cad_action": {"action": "navigate", "navigation": "open_cad"},
            "via": "cad",
        }

    try:
        from app.cad_engine.commands import get_command_executor
        executor = get_command_executor()
        ctx_overrides = {"selected_feature_id": selected_feature_id} if selected_feature_id else {}
        exec_res = executor.execute(text, ctx_overrides)
        if not exec_res.get("recognized"):
            return None

        status = "ok" if exec_res.get("success") else "error"
        reply = exec_res.get("spoken_reply") or exec_res.get("message")
        return {
            "reply": reply,
            "status": status,
            "cad_action": {
                "action": (exec_res.get("action") or "cad_operation").lower(),
                "feature_id": exec_res.get("feature_id"),
                "ambiguous": exec_res.get("ambiguous", False),
                "candidates": exec_res.get("candidates", []),
                "meshes": exec_res.get("meshes", []),
                "sketches": exec_res.get("sketches", []),
                "context": exec_res.get("context", {}),
                "parameters": exec_res.get("parameters", {}),
            },
            "via": "cad",
        }
    except Exception as e:
        logger.error(f"[CAD] Unified executor error: {e}", exc_info=True)
        return None


# Spoken-safe capability replies: the orchestrator result may carry internal
# detail, but voice must only ever speak a concise summary.
def _speakable_capability_reply(result: dict) -> str:
    reply = (result or {}).get("reply", "")
    if reply:
        text = " ".join(str(reply).split())
        return text[:280]
    return "Task complete, sir."


async def _try_orchestrated_command(text: str, history: list[dict]) -> dict | None:
    """Route a command through the central orchestrator when a real executable capability exists.

    Returns a chat-shaped response dict, or None when the orchestrator has no
    runnable step (nothing was executed) so callers can fall through safely.
    """
    try:
        from app.jarvis_orchestrator import get_orchestrator
        from app.core.execution import ExecutionStatus
        _orch = get_orchestrator()
        if _orch._agent_manager is None:
            from app.agent_manager import get_agent_manager
            _orch.set_agent_manager(get_agent_manager())

        if not await _orch.can_handle(text):
            return None

        orch_result = await _orch.process_input(text, context={"conversation_history": history})
        step_results = orch_result.metadata.get("step_results") or []
        action_res = step_results[-1] if step_results else None

        if orch_result.status == ExecutionStatus.SUCCESS and isinstance(action_res, dict):
            if action_res.get("requires_confirmation"):
                return {
                    "reply": action_res["reply"],
                    "status": "ok",
                    "requires_confirmation": True,
                    "safety_action": action_res.get("safety_action"),
                    "via": "orchestrator",
                }
            # Voice-safe: speak a concise summary; full structured results ride
            # along in system_action for the UI, never as raw internals in TTS.
            reply_text = _speakable_capability_reply(action_res)
            spoken_source = str(action_res.get("reply") or "")
            if any(marker in spoken_source for marker in
                   ("Traceback", "http://", "https://", "/api/", "Exception", "  ", "{")):
                reply_text = _speakable_capability_reply({"reply": reply_text.split(".")[0] + "."})
            speak_text = reply_text if len(reply_text) <= 280 else reply_text[:277].rsplit(" ", 1)[0] + "..."
            return {
                "reply": speak_text,
                "status": "ok",
                "system_action": action_res,
                "is_compound": action_res.get("is_compound", False),
                "language": detect_text_language(speak_text),
                "via": "orchestrator",
            }

        error_text = orch_result.error or ""
        if "No executable capability" in error_text or "waiting for user permission" in error_text:
            logger.info(f"[CHAT] Orchestrator has no runnable step; using direct brain path: {error_text}")
            return None

        # The capability exists but the real execution failed — report it honestly.
        logger.warning(f"[CHAT] Orchestrator execution failed: {error_text}")
        return {
            "reply": f"I attempted that action but it did not complete, sir. {error_text}",
            "status": "error",
            "via": "orchestrator",
        }
    except Exception as orch_exc:
        logger.warning(f"[CHAT] Orchestrator path unavailable, falling back to direct execution: {orch_exc}")
        return None


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    t0 = time.time()
    if not req.messages:
        return {"reply": "Standing by, sir.", "status": "ok"}

    # --- Attachments: validate, extract real content, inject into context --
    from app import attachments as attach_engine
    last_user_msg = req.messages[-1].content.strip()
    attach_records, reused_context = await asyncio.to_thread(
        attach_engine.resolve_turn_attachments, last_user_msg,
        [a.model_dump() for a in (req.attachments or [])]
    )
    if attach_records:
        logger.info(f"[ATTACH] {len(attach_records)} attachment(s) in context, reused={reused_context}")

    logger.info(f"[COMMAND RECEIVED] User: \"{last_user_msg}\"")

    # Multi-turn history context for follow-ups and chained instructions
    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    augmented_msg = last_user_msg
    digest = attach_engine.build_attachment_digest(attach_records) if attach_records else ""
    if digest:
        note = attach_engine.capability_note(attach_records)
        prefix = digest + (("\n" + note) if note else "") + "\n\n"
        if not reused_context:
            augmented_msg = prefix + last_user_msg
        history = history + [{"role": "assistant", "content": digest}]

    # Deterministic real execution for follow-up commands on live attachments
    # (image edits, shape removal, CAD import, video frame extraction).
    if attach_records:
        handled = await asyncio.to_thread(
            attach_engine.try_handle_attachment_turn, last_user_msg, attach_records
        )
        if handled is not None:
            duration_ms = round((time.time() - t0) * 1000, 1)
            logger.info(f"[ATTACH {duration_ms}ms] status={handled.get('status')} reply=\"{handled.get('reply', '')[:120]}\"")
            handled.setdefault("language", detect_text_language(handled.get("reply", "")))
            return handled

    # -1. CAD commands go straight to the real CAD engine (bypass the LLM cascade).
    cad_reply = await _try_cad_command(last_user_msg, req.selected_feature_id)
    if cad_reply is not None:
        duration_ms = round((time.time() - t0) * 1000, 1)
        logger.info(f"[CAD {duration_ms}ms] status={cad_reply['status']} reply=\"{cad_reply['reply'][:120]}\"")
        return cad_reply

    # 0. Orchestrator-first routing: only inputs with a truly executable capability
    #    go through intent → plan → agent → tool → verification; everything else
    #    keeps using the direct agent-brain cascade below.
    orch_reply = await _try_orchestrated_command(augmented_msg, history)
    if orch_reply is not None:
        duration_ms = round((time.time() - t0) * 1000, 1)
        logger.info(f"[ORCHESTRATOR {duration_ms}ms] status={orch_reply['status']} reply=\"{orch_reply['reply'][:120]}\"")
        return orch_reply

    try:
        # 1. Evaluate with Multitasking AI Brain (Safety confirmation, close apps, file ops, compound tasks, deep AI/ML)
        brain_result = await parse_and_execute_multitask(augmented_msg, conversation_history=history)

        duration_ms = round((time.time() - t0) * 1000, 1)

        if brain_result.get("requires_confirmation"):
            logger.info(f"[COMMAND SAFETY GATE] ({duration_ms}ms) Action: {brain_result.get('safety_action')}")
            return {
                "reply": brain_result["reply"],
                "status": "ok",
                "requires_confirmation": True,
                "safety_action": brain_result.get("safety_action"),
            }

        if brain_result.get("success"):
            logger.info(f"[COMMAND EXECUTED] ({duration_ms}ms) Actions: {brain_result.get('executed_actions') or brain_result.get('action')} | Reply: \"{brain_result.get('reply')}\"")
            return {
                "reply": brain_result["reply"],
                "status": "ok",
                "system_action": brain_result,
                "is_compound": brain_result.get("is_compound", False),
                "language": detect_text_language(brain_result.get("reply", "")),
            }

        if brain_result.get("reply"):
            provider = brain_result.get("provider", "neural_core")
            logger.info(f"[COMMAND ANSWERED] ({duration_ms}ms) Provider: {provider} | Reply: \"{brain_result['reply'][:120]}...\"")
            return {
                "reply": brain_result["reply"],
                "status": "ok",
                "provider": provider,
                "language": detect_text_language(brain_result["reply"]),
            }

        # 2. General LLM Query (OpenAI Responses API -> Gemini -> Groq fallback)
        openai_key, openai_model, _ = get_openai_credentials()
        if openai_key:
            try:
                reply = await query_openai_responses_llm(req.messages)
                duration_ms = round((time.time() - t0) * 1000, 1)
                logger.info(f"[COMMAND ANSWERED] ({duration_ms}ms) Provider: openai ({openai_model})")
                return {"reply": reply, "status": "ok", "provider": f"openai ({openai_model})"}
            except Exception as ex_openai:
                logger.warning(f"OpenAI {openai_model} Responses API notice: {ex_openai}, falling back...")

        if GEMINI_API_KEY:
            try:
                inline_imgs = [str(WORKSPACE_ROOT / r["path"]) for r in attach_records
                               if r.get("category") == "image" and not r.get("error")]
                gemini_messages = (req.messages[:-1] + [MessageItem(role="user", content=augmented_msg)]) \
                    if augmented_msg != last_user_msg else req.messages
                reply = await query_gemini_llm(gemini_messages, inline_image_paths=inline_imgs)
                duration_ms = round((time.time() - t0) * 1000, 1)
                logger.info(f"[COMMAND ANSWERED] ({duration_ms}ms) Provider: gemini")
                return {"reply": reply, "status": "ok", "provider": "gemini"}
            except Exception as ex_gem:
                logger.warning(f"Gemini LLM error: {ex_gem}, falling back to Groq...")

        if GROQ_API_KEY:
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
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
                    if resp.status_code != 200:
                        fallback_payload = {**payload, "model": "qwen/qwen3.8-27b"}
                        resp = await client.post(GROQ_API_URL, json=fallback_payload, headers=headers)

                    resp.raise_for_status()
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    duration_ms = round((time.time() - t0) * 1000, 1)
                    logger.info(f"[COMMAND ANSWERED] ({duration_ms}ms) Provider: groq")
                    return {"reply": reply, "status": "ok", "provider": "groq"}
            except Exception as e_groq:
                logger.warning(f"Groq LLM error: {e_groq}")

        # 3. Final Fallback: Local Zero-Latency Natural Intent Resolver
        local_intent = await resolve_natural_intent(last_user_msg)
        duration_ms = round((time.time() - t0) * 1000, 1)
        reply = local_intent.get("reply", "Understood, sir. Systems are standing by and monitoring.")
        logger.info(f"[COMMAND ANSWERED LOCAL] ({duration_ms}ms) Reply: \"{reply}\"")
        return {
            "reply": reply,
            "status": "ok",
            "system_action": local_intent,
            "provider": "local_natural_intent",
        }

    except Exception as e:
        duration_ms = round((time.time() - t0) * 1000, 1)
        logger.error(f"[COMMAND PROCESSING ERROR] ({duration_ms}ms): {e}", exc_info=True)
        try:
            local_fallback = await resolve_natural_intent(last_user_msg)
            reply = local_fallback.get("reply", "Standing by, sir. All core diagnostics are nominal.")
            return {
                "reply": reply,
                "status": "ok",
                "system_action": local_fallback,
                "provider": "local_emergency_fallback",
            }
        except Exception:
            return {
                "reply": "Standing by, sir. All core diagnostics and protocols remain nominal.",
                "status": "ok",
                "provider": "safe_default",
            }


# =========================================================================
# STREAMING CHAT ENDPOINT (Server-Sent Events)
# =========================================================================

class StreamChatRequest(BaseModel):
    messages: list[MessageItem]
    stream: bool = True
    selected_feature_id: str | None = None
    attachments: list[AttachmentRef] | None = None


async def _stream_llm_response(messages: list[MessageItem], prompt_instruction: str = JARVIS_SYSTEM_PROMPT) -> AsyncGenerator[str, None]:
    """Stream LLM response as SSE deltas. Tries providers in order: OpenAI -> Gemini -> Groq -> Local."""
    openai_key, openai_model, openai_url = get_openai_credentials()
    
    # Try OpenAI Responses API with streaming
    if openai_key:
        try:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            input_items = []
            for m in messages[-10:]:
                role = "user" if m.role == "user" else "assistant"
                input_items.append({"role": role, "content": m.content})
            
            payload = {
                "model": openai_model,
                "instructions": prompt_instruction,
                "input": input_items,
                "max_output_tokens": 500,
                "stream": True,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", openai_url, headers=headers, json=payload) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    data = json.loads(data_str)
                                    # Parse OpenAI Responses API streaming format
                                    if "output" in data and isinstance(data["output"], list):
                                        for item in data["output"]:
                                            if item.get("type") == "message" and "content" in item:
                                                for c in item["content"]:
                                                    if isinstance(c, dict) and c.get("text"):
                                                        yield f"data: {json.dumps({'delta': c['text']})}\n\n"
                                except json.JSONDecodeError:
                                    continue
                        return
                    elif resp.status_code in [400, 401, 403, 404, 429]:
                        logger.warning(f"OpenAI streaming failed ({resp.status_code}), falling back...")
        except Exception as ex:
            logger.warning(f"OpenAI streaming error: {ex}, falling back...")
    
    # Fallback: Gemini streaming (not natively supported, simulate with chunks)
    if GEMINI_API_KEY:
        try:
            reply = await query_gemini_llm(messages, prompt_instruction, max_tokens=500)
            # Simulate streaming by chunking the response
            words = reply.split()
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
                await asyncio.sleep(0.02)
            return
        except Exception as ex:
            logger.warning(f"Gemini streaming fallback error: {ex}")
    
    # Fallback: Groq streaming
    if GROQ_API_KEY:
        try:
            payload_messages = [{"role": "system", "content": prompt_instruction}]
            for m in messages[-10:]:
                payload_messages.append({"role": m.role, "content": m.content})
            
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            
            payload = {
                "model": GROQ_MODEL,
                "messages": payload_messages,
                "temperature": 0.6,
                "max_tokens": 500,
                "stream": True,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", GROQ_API_URL, headers=headers, json=payload) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {}).get("content", "")
                                        if delta:
                                            yield f"data: {json.dumps({'delta': delta})}\n\n"
                                except json.JSONDecodeError:
                                    continue
                        return
        except Exception as ex:
            logger.warning(f"Groq streaming error: {ex}")
    
    # Final fallback: Local intent resolver
    local_intent = await resolve_natural_intent(messages[-1].content if messages else "")
    reply = local_intent.get("reply", "Standing by, sir. All core diagnostics are nominal.")
    words = reply.split()
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i+3]) + " "
        yield f"data: {json.dumps({'delta': chunk})}\n\n"
        await asyncio.sleep(0.02)


@app.post("/api/chat/stream")
async def chat_stream(req: StreamChatRequest):
    """Server-Sent Events streaming chat endpoint."""
    if not req.messages:
        async def empty_stream():
            yield f"data: {json.dumps({'delta': 'Standing by, sir.'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")
    
    last_user_msg = req.messages[-1].content.strip()
    logger.info(f"[STREAM COMMAND] User: \"{last_user_msg}\"")
    
    # Check for multitasking brain actions first (non-streaming for safety)
    history = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    # Attachments: real extraction injected into the message context
    from app import attachments as attach_engine
    attach_records, reused_context = await asyncio.to_thread(
        attach_engine.resolve_turn_attachments, last_user_msg,
        [a.model_dump() for a in (req.attachments or [])]
    )
    augmented_msg = last_user_msg
    digest = attach_engine.build_attachment_digest(attach_records) if attach_records else ""
    if digest:
        if not reused_context:
            augmented_msg = digest + "\n\n" + last_user_msg
        history = history + [{"role": "assistant", "content": digest}]

    pending_output_events: list[str] = []
    if attach_records:
        handled = await asyncio.to_thread(
            attach_engine.try_handle_attachment_turn, last_user_msg, attach_records
        )
        if handled is not None:
            async def handled_stream():
                payload = {"delta": handled.get("reply", "Done, sir.")}
                if handled.get("outputs"):
                    payload["outputs"] = handled["outputs"]
                if handled.get("cad_action"):
                    payload["cad_action"] = handled["cad_action"]
                if handled.get("status") == "error":
                    payload["error"] = True
                yield f"data: {json.dumps(payload)}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            return StreamingResponse(handled_stream(), media_type="text/event-stream")

    # CAD commands go straight to the real CAD engine (bypass the LLM cascade)
    cad_reply = await _try_cad_command(last_user_msg, req.selected_feature_id)
    if cad_reply is not None:
        async def cad_response():
            payload: dict = {"delta": cad_reply["reply"]}
            if cad_reply.get("cad_action"):
                payload["cad_action"] = cad_reply["cad_action"]
            if cad_reply.get("status") == "error":
                payload["error"] = True
            yield f"data: {json.dumps(payload)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(cad_response(), media_type="text/event-stream")

    # Orchestrator-first: executed through intent → plan → agent → tool → verification
    orch_reply = await _try_orchestrated_command(augmented_msg, history)
    if orch_reply is not None:
        async def orchestrated_response():
            payload: dict = {"delta": orch_reply["reply"]}
            if orch_reply.get("requires_confirmation"):
                payload["requires_confirmation"] = True
                payload["safety_action"] = orch_reply.get("safety_action")
            elif orch_reply.get("system_action"):
                payload["system_action"] = orch_reply["system_action"]
            if orch_reply.get("status") == "error":
                payload["error"] = True
            yield f"data: {json.dumps(payload)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(orchestrated_response(), media_type="text/event-stream")

    brain_result = await parse_and_execute_multitask(augmented_msg, conversation_history=history)
    
    if brain_result.get("requires_confirmation") or brain_result.get("success"):
        # For safety gates and system actions, return complete response
        async def complete_response():
            if brain_result.get("requires_confirmation"):
                yield f"data: {json.dumps({'delta': brain_result['reply'], 'requires_confirmation': True, 'safety_action': brain_result.get('safety_action')})}\n\n"
            elif brain_result.get("success"):
                yield f"data: {json.dumps({'delta': brain_result['reply'], 'system_action': brain_result})}\n\n"
            else:
                yield f"data: {json.dumps({'delta': brain_result.get('reply', 'Understood, sir.')})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(complete_response(), media_type="text/event-stream")
    
    # Stream LLM response
    stream_messages = (req.messages[:-1] + [MessageItem(role="user", content=augmented_msg)]) \
        if augmented_msg != last_user_msg else req.messages
    return StreamingResponse(
        _stream_llm_response(stream_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# =========================================================================
# 10. MODULAR SKILLS & PLUGINS API
# =========================================================================

@app.get("/api/skills")
def get_skills_endpoint() -> dict:
    """List all registered skills, their enable status, and callable tools."""
    return {
        "status": "ok",
        "skills": skills_registry.list_skills(),
        "active_tools_count": len(skills_registry.get_active_tools()),
    }


@app.post("/api/skills/toggle")
def toggle_skill_endpoint(req: SkillToggleRequest) -> dict:
    """Enable or disable a specific skill."""
    success = skills_registry.set_skill_enabled(req.skill_id, req.enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{req.skill_id}' not found")
    return {"status": "ok", "skill_id": req.skill_id, "enabled": req.enabled}


@app.websocket("/api/coding/ws/{session_id}")
async def coding_ws_endpoint(websocket: WebSocket, session_id: str):
    logger.info(f"[WS ATTEMPT] Connecting: {session_id}")
    await websocket.accept()
    logger.info(f"[WS ACCEPTED] Coding session: {session_id}")
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "cancel":
                coding_engine.cancel_session(session_id)
                await websocket.send_json({"type": "cancelled", "message": "Operation cancelled."})
                continue

            user_message = data.get("message", "")
            active_file = data.get("active_file", "")
            autonomous = data.get("autonomous", True)

            coding_engine.clear_cancellation(session_id)

            await websocket.send_json({"type": "status", "message": "processing"})

            pending_events: asyncio.Queue = asyncio.Queue()

            async def drain_events():
                """Background task that drains the event queue to WebSocket."""
                send_failures = 0
                while True:
                    try:
                        event_type, event_data = await asyncio.wait_for(
                            pending_events.get(), timeout=0.1
                        )
                        await websocket.send_json({"type": event_type, "data": event_data})
                        send_failures = 0
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketDisconnect:
                        break
                    except Exception as ex:
                        send_failures += 1
                        logger.warning(f"WS event send failed ({send_failures}): {ex}")
                        if send_failures >= 5:
                            break

            drain_task = asyncio.create_task(drain_events())

            def sync_event_callback(event_type: str, event_data: dict):
                """Bridge sync callback to async WebSocket send via queue."""
                try:
                    pending_events.put_nowait((event_type, event_data))
                except Exception as ex:
                    logger.warning(f"Event queue failed: {ex}")

            if autonomous:
                result = await coding_engine.execute_autonomous_task(
                    session_id=session_id,
                    user_message=user_message,
                    active_file=active_file,
                    event_callback=sync_event_callback,
                    prefer_opencode=True,
                )
            else:
                result = await coding_engine.execute_coding_turn(
                    session_id=session_id,
                    user_message=user_message,
                    active_file=active_file,
                    auto_run_tools=True,
                    event_callback=sync_event_callback,
                    autonomous=True,
                )

            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass
            while not pending_events.empty():
                try:
                    event_type, event_data = pending_events.get_nowait()
                    await websocket.send_json({"type": event_type, "data": event_data})
                except Exception:
                    break

            if coding_engine.is_cancelled(session_id):
                coding_engine.clear_cancellation(session_id)
                await websocket.send_json({"type": "cancelled", "message": "Operation cancelled by user."})
            else:
                await websocket.send_json({"type": "result", "data": result})

    except WebSocketDisconnect:
        logger.info(f"[WS DISCONNECTED] Coding session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.get("/api/coding/agent/status")
def coding_agent_status_endpoint() -> dict:
    """Report autonomous agent engine availability (OpenCode + JARVIS)."""
    opencode_available = False
    try:
        from app.opencode_bridge import is_opencode_available
        opencode_available = is_opencode_available()
    except ImportError:
        try:
            from opencode_bridge import is_opencode_available
            opencode_available = is_opencode_available()
        except ImportError:
            pass

    return {
        "status": "ok",
        "engines": {
            "jarvis": {"available": True, "description": "Built-in ReAct coding agent with skills"},
            "opencode": {
                "available": opencode_available,
                "description": "External opencode-ai agent (npm i -g opencode-ai)",
            },
        },
        "autonomous": True,
        "max_iterations": 15,
        "error_retry": True,
        "workspace_root": str(WORKSPACE_ROOT),
    }


# =========================================================================
# 11. AUTONOMOUS AI CODING ASSISTANT API
# =========================================================================

@app.post("/api/coding/chat")
async def coding_chat_endpoint(req: CodingChatRequest) -> dict:
    """Execute an autonomous AI coding turn with error-retry and OpenCode routing."""
    try:
        result = await coding_engine.execute_autonomous_task(
            session_id=req.session_id,
            user_message=req.message,
            active_file=req.active_file,
            prefer_opencode=True,
        )
        return result
    except Exception as e:
        logger.error(f"Coding engine error: {e}", exc_info=True)
        return {
            "session_id": req.session_id,
            "reply": f"An error occurred during neural coding reasoning: {e}",
            "status": "error",
            "error": str(e),
            "tool_calls": [],
            "diffs": [],
        }


@app.get("/api/coding/sessions")
def list_coding_sessions_endpoint() -> dict:
    return {"status": "ok", "sessions": list_coding_sessions()}


@app.post("/api/coding/sessions/new")
def new_coding_session_endpoint(req: CodingSessionNewRequest) -> dict:
    session_id = f"session_{int(time.time() * 1000)}"
    session = create_or_get_coding_session(session_id, title=req.title, active_file=req.active_file)
    return {"status": "ok", "session": session}


@app.get("/api/coding/sessions/{session_id}/messages")
def get_coding_session_messages_endpoint(session_id: str) -> dict:
    messages = get_coding_messages(session_id)
    return {"status": "ok", "session_id": session_id, "messages": messages}


@app.get("/api/coding/workspace/tree")
def get_workspace_tree_endpoint(path: str = ".", max_depth: int = 3) -> dict:
    res = skills_registry.execute_tool("workspace_tree", {"path": path, "max_depth": max_depth})
    return res


@app.get("/api/coding/workspace/file")
def get_workspace_file_endpoint(path: str, start_line: int | None = None, end_line: int | None = None) -> dict:
    args = {"path": path}
    if start_line is not None:
        args["start_line"] = start_line
    if end_line is not None:
        args["end_line"] = end_line
    return skills_registry.execute_tool("read_file", args)


@app.post("/api/coding/workspace/save")
def save_workspace_file_endpoint(req: FileSaveRequest) -> dict:
    return skills_registry.execute_tool("write_file", {
        "path": req.path,
        "content": req.content,
        "overwrite": req.overwrite,
    })


@app.post("/api/coding/rollback")
def rollback_file_endpoint(req: RollbackRequest) -> dict:
    return skills_registry.execute_tool("rollback_file", {"path": req.path})


@app.post("/api/coding/workspace/run")
def run_command_endpoint(req: RunTerminalRequest) -> dict:
    return skills_registry.execute_tool("run_command", {
        "command": req.command,
        "cwd": req.cwd,
        "timeout_seconds": req.timeout,
    })


@app.get("/api/coding/workspace/git")
def get_git_status_endpoint() -> dict:
    return skills_registry.execute_tool("git_status", {})


# =========================================================================
# FILE UPLOAD & ATTACHMENT ENDPOINTS
# =========================================================================

@app.post("/api/upload")
def upload_file_endpoint(req: FileUploadRequest) -> dict:
    """Upload a file to the workspace for AI inspection (validated)."""
    from app import attachments as attach_engine
    ok, error, category = attach_engine.validate_upload(req.filename, req.content_base64, req.mime_type)
    if not ok:
        return {"success": False, "error": error}
    res = skills_registry.execute_tool("upload_file", {
        "filename": req.filename,
        "content_base64": req.content_base64,
        "mime_type": req.mime_type,
        "category": req.category if req.category not in ("", "file", None) else category,
    })
    if isinstance(res, dict) and res.get("success") and isinstance(res.get("result"), dict):
        res["result"]["url"] = attach_engine.attachment_url(
            WORKSPACE_ROOT / res["result"].get("path", "")) if res["result"].get("path") else None
        res["result"]["category"] = category
    return res


@app.get("/api/files/{rel_path:path}")
def serve_workspace_file(rel_path: str):
    """Serve an uploaded/generated attachment file to the chat UI."""
    from app import attachments as attach_engine
    from app.attachments import MIME_BY_EXT
    try:
        path = attach_engine.safe_attachment_path(rel_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid attachment path")
    mime = MIME_BY_EXT.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(str(path), media_type=mime, filename=path.name)


@app.get("/api/uploads")
def list_uploads_endpoint(category: str = "") -> dict:
    """List all uploaded files."""
    return skills_registry.execute_tool("list_uploads", {"category": category})


@app.get("/api/uploads/{filename}")
def get_upload_info_endpoint(filename: str) -> dict:
    """Get information about an uploaded file."""
    return skills_registry.execute_tool("get_upload_info", {"filename": filename})


@app.post("/api/vision/analyze")
async def vision_analyze_endpoint(file: UploadFile = File(...)) -> dict:
    """Analyze uploaded image for face detection."""
    try:
        import cv2
        import numpy as np
        from io import BytesIO

        # Read uploaded file
        contents = await file.read()
        img_array = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            return {"faces": [], "error": "Invalid image"}

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply histogram equalization for better detection
        gray = cv2.equalizeHist(gray)

        # Load face cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Format results
        face_results = []
        for (x, y, w, h) in faces:
            confidence = 1.0 - (1.0 / (w * h / 1000 + 1))
            face_results.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "confidence": min(confidence, 0.99)
            })

        return {"faces": face_results, "count": len(face_results)}

    except Exception as e:
        logger.error(f"Vision analysis failed: {e}", exc_info=True)
        return {"faces": [], "error": str(e)}


@app.post("/api/image/generate")
async def image_generate_endpoint(req: dict) -> dict:
    """Generate image from text prompt using AI."""
    try:
        prompt = req.get("prompt", "")
        if not prompt.strip():
            return {"error": "Empty prompt"}

        # Use OpenAI DALL-E for image generation
        import httpx
        api_key = os.getenv("OPENAI_API_KEY", "")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024"
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                image_url = data["data"][0]["url"]
                return {"image_url": image_url, "url": image_url}
            else:
                return {"error": f"Image generation failed: {resp.status_code}", "detail": resp.text[:200]}

    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/document/analyze")
async def document_analyze_endpoint(file: UploadFile = File(...)) -> dict:
    """Analyze uploaded document (PDF, TXT, DOC, DOCX, MD)."""
    try:
        import tempfile
        import os

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Extract text based on file type
            text = ""
            ext = os.path.splitext(file.filename)[1].lower()

            if ext == ".txt" or ext == ".md":
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            elif ext == ".pdf":
                try:
                    import PyPDF2
                    with open(tmp_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        text = "\n".join([page.extract_text() or "" for page in reader.pages])
                except ImportError:
                    return {"error": "PyPDF2 not installed. Install with: pip install PyPDF2"}
            elif ext in [".doc", ".docx"]:
                try:
                    import docx
                    doc = docx.Document(tmp_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    return {"error": "python-docx not installed. Install with: pip install python-docx"}
            else:
                return {"error": f"Unsupported file type: {ext}"}

            if not text.strip():
                return {"error": "No text content found in document"}

            # Use AI to analyze the document
            from app.agent_brain import parse_and_execute_multitask

            analysis_prompt = f"""Analyze this document and provide:
1. A concise summary (2-3 sentences)
2. Key points (3-5 bullet points)
3. Important entities (people, organizations, locations)
4. Overall sentiment (positive, negative, neutral)

Document text:
{text[:3000]}"""

            response = await parse_and_execute_multitask(analysis_prompt)
            reply = response.get("reply", "") if isinstance(response, dict) else str(response)

            # Parse the response (simple extraction)
            summary = reply[:500]
            key_points = []
            entities = []
            sentiment = "neutral"

            # Try to extract structured data
            lines = reply.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                    key_points.append(line[1:].strip())
                elif line.lower().startswith("sentiment:"):
                    sentiment = line.split(":", 1)[1].strip().lower()

            # Extract potential entities (capitalized words)
            import re
            words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text[:1000])
            entities = list(set(words))[:10]

            return {
                "summary": summary,
                "key_points": key_points[:5],
                "entities": entities,
                "sentiment": sentiment
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Document analysis failed: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/diagnostics/run")
async def run_diagnostics_endpoint() -> dict:
    """Run comprehensive diagnostics across all JARVIS systems."""
    try:
        import importlib
        import app.diagnostics
        importlib.reload(app.diagnostics)
        from app.diagnostics import diagnostics_engine
        report = await diagnostics_engine.run_all_tests()

        return {
            "status": "ok",
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "skipped": report.skipped,
            "total_duration_ms": report.total_duration_ms,
            "system_health": report.system_health,
            "timestamp": report.timestamp,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "error": r.error,
                    "fix_applied": r.fix_applied,
                    "fix_description": r.fix_description,
                    "timestamp": r.timestamp,
                }
                for r in report.test_results
            ],
        }
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/diagnostics/latest")
def get_latest_diagnostics_endpoint() -> dict:
    """Get the most recent diagnostics report."""
    try:
        from app.diagnostics import diagnostics_engine
        report = diagnostics_engine.get_latest_report()

        if report is None:
            return {"status": "ok", "report": None, "message": "No diagnostics run yet"}

        return {
            "status": "ok",
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "skipped": report.skipped,
            "total_duration_ms": report.total_duration_ms,
            "system_health": report.system_health,
            "timestamp": report.timestamp,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "error": r.error,
                    "fix_applied": r.fix_applied,
                    "fix_description": r.fix_description,
                    "timestamp": r.timestamp,
                }
                for r in report.test_results
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/diagnostics/history")
def get_diagnostics_history_endpoint() -> dict:
    """Get diagnostics history."""
    try:
        from app.diagnostics import diagnostics_engine
        history = diagnostics_engine.get_history()

        return {
            "status": "ok",
            "count": len(history),
            "reports": [
                {
                    "total_tests": r.total_tests,
                    "passed": r.passed,
                    "failed": r.failed,
                    "errors": r.errors,
                    "skipped": r.skipped,
                    "total_duration_ms": r.total_duration_ms,
                    "system_health": r.system_health,
                    "timestamp": r.timestamp,
                }
                for r in history
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get diagnostics history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/voice/stream/{session_id}")
async def voice_streaming_ws(websocket: WebSocket, session_id: str):
    """Real-time streaming speech-to-text via WebSocket.

    Accepts raw PCM audio chunks (16kHz, 16-bit, mono) from the frontend,
    processes them through the streaming STT service, and sends back partial
    and final transcription results in real-time.
    """
    logger.info(f"[VOICE-WS] Connecting: {session_id}")
    await websocket.accept()
    logger.info(f"[VOICE-WS] Accepted: {session_id}")

    try:
        from app.streaming_stt import StreamingSTTService

        stt_service = StreamingSTTService(session_id)

        while True:
            data = await websocket.receive()

            if "bytes" in data:
                audio_chunk = data["bytes"]
                if not audio_chunk:
                    continue

                result = await stt_service.stream_audio_chunk(audio_chunk)

                if result:
                    await websocket.send_json({
                        "type": "transcription",
                        "text": result.get("text", ""),
                        "is_final": result.get("is_final", False),
                        "confidence": result.get("confidence", 0.0),
                        "language": result.get("language", "en"),
                    })

            elif "text" in data:
                try:
                    msg = json.loads(data["text"])
                    action = msg.get("action")

                    if action == "finalize":
                        result = await stt_service.finalize()
                        if result:
                            await websocket.send_json({
                                "type": "transcription",
                                "text": result.get("text", ""),
                                "is_final": True,
                                "confidence": result.get("confidence", 0.0),
                                "language": result.get("language", "en"),
                            })
                        await websocket.send_json({"type": "finalized"})

                    elif action == "reset":
                        stt_service.reset()
                        await websocket.send_json({"type": "reset"})

                except json.JSONDecodeError:
                    logger.warning("[VOICE-WS] Invalid JSON message")

    except WebSocketDisconnect:
        logger.info(f"[VOICE-WS] Disconnected: {session_id}")
    except Exception as exc:
        logger.error(f"[VOICE-WS] Error: {exc}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass


# ============================================================================
# OpenJARVIS Integration Endpoints
# ============================================================================

# Initialize OpenJARVIS subsystems
try:
    from app.openjarvis.security import guardrails, ssrf_checker, file_policy
    from app.openjarvis.tools import ToolRegistry
    from app.openjarvis.agents import OrchestratorAgent, DeepResearchAgent, LoopGuard
    from app.openjarvis.workflow import WorkflowEngine, WorkflowBuilder
    from app.openjarvis.skills import SkillManager
    from app.openjarvis.learning import HeuristicRouter
    from app.openclaw import WorkspaceModel, HeartbeatSystem, StateManager

    # Initialize skill manager and discover built-in skills
    _skill_manager = SkillManager(skill_dirs=[APP_DIR / "openjarvis" / "skills" / "data"])
    _skill_manager.discover()

    # Initialize workspace model
    _workspace = WorkspaceModel(workspace_dir=WORKSPACE_ROOT / ".jarvis" / "workspace")

    # Initialize heartbeat system
    _heartbeat = HeartbeatSystem(state_file=WORKSPACE_ROOT / ".jarvis" / "heartbeat-state.json")

    # Initialize state manager
    _state_manager = StateManager(db_path=WORKSPACE_ROOT / ".jarvis" / "state" / "jarvis.sqlite")

    # Initialize learning router
    _router = HeuristicRouter()

    logger.info("OpenJARVIS integration layer initialized successfully")
    logger.info(f"  - Tools registered: {len(ToolRegistry.list_names())}")
    logger.info(f"  - Skills discovered: {len(_skill_manager.list_skills())}")
except Exception as e:
    logger.warning(f"OpenJARVIS integration initialization failed: {e}")
    _skill_manager = None
    _workspace = None
    _heartbeat = None
    _state_manager = None
    _router = None


@app.get("/api/openjarvis/status")
async def openjarvis_status():
    """Get OpenJARVIS integration status."""
    return {
        "status": "active",
        "tools": {
            "registered": ToolRegistry.list_names() if _skill_manager else [],
            "count": len(ToolRegistry.list_names()) if _skill_manager else 0,
        },
        "skills": {
            "discovered": [s.name for s in _skill_manager.list_skills()] if _skill_manager else [],
            "count": len(_skill_manager.list_skills()) if _skill_manager else 0,
        },
        "workspace": {
            "enabled": _workspace is not None,
            "dir": str(_workspace.workspace_dir) if _workspace else None,
        },
        "heartbeat": {
            "enabled": _heartbeat is not None,
            "status": _heartbeat.get_status() if _heartbeat else None,
        },
        "learning_router": {
            "enabled": _router is not None,
        },
    }


@app.post("/api/openjarvis/security/scan")
async def security_scan(request: dict):
    """Scan text for PII, secrets, and security issues."""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        result = guardrails.scan_input(text)
        return {
            "clean": result.clean,
            "matches": [
                {"type": m.type, "value": m.value[:20] + "..." if len(m.value) > 20 else m.value}
                for m in result.matches
            ],
            "alerts": result.alerts,
        }
    except Exception as e:
        logger.error(f"Security scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/openjarvis/security/redact")
async def security_redact(request: dict):
    """Redact PII and secrets from text."""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        redacted = guardrails.redact(text)
        return {"redacted_text": redacted}
    except Exception as e:
        logger.error(f"Security redaction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/openjarvis/tools/execute")
async def execute_tool(request: dict):
    """Execute a registered tool."""
    try:
        tool_name = request.get("tool")
        arguments = request.get("arguments", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="No tool name provided")

        tool = ToolRegistry.get(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

        result = await tool.execute(**arguments)
        return {"tool": tool_name, "result": result}
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openjarvis/tools/list")
async def list_tools():
    """List all registered tools."""
    tools = []
    for name in ToolRegistry.list_names():
        tool = ToolRegistry.get(name)
        if tool:
            tools.append({
                "name": name,
                "description": tool.spec.description,
                "parameters": tool.spec.parameters,
            })
    return {"tools": tools}


@app.post("/api/openjarvis/agents/orchestrate")
async def orchestrate_agent(request: dict):
    """Run the orchestrator agent on a query."""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        agent = OrchestratorAgent(mode=request.get("mode", "structured"), max_turns=request.get("max_turns", 10))
        result = await agent.run(query)
        return result
    except Exception as e:
        logger.error(f"Agent orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/openjarvis/agents/research")
async def deep_research(request: dict):
    """Run deep research agent on a query."""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        agent = DeepResearchAgent(max_turns=request.get("max_turns", 8))
        result = await agent.research(query)
        return result
    except Exception as e:
        logger.error(f"Deep research failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/openjarvis/workflow/execute")
async def execute_workflow(request: dict):
    """Execute a workflow definition."""
    try:
        workflow_def = request.get("workflow", {})
        initial_input = request.get("input")

        builder = WorkflowBuilder(name=workflow_def.get("name", "workflow"))

        for node_def in workflow_def.get("nodes", []):
            node_type = node_def.get("type", "tool")
            node_id = node_def.get("id", f"node_{len(builder._graph.nodes)}")

            if node_type == "tool":
                builder.add_tool(node_id, node_def.get("tool", ""), node_def.get("arguments", {}))
            elif node_type == "agent":
                builder.add_agent(node_id, node_def.get("agent", ""), **node_def.get("config", {}))
            elif node_type == "condition":
                builder.add_condition(node_id, node_def.get("expression", "True"))

        for edge_def in workflow_def.get("edges", []):
            builder.connect(edge_def["source"], edge_def["target"], edge_def.get("condition"))

        graph = builder.build()
        engine = WorkflowEngine()
        result = await engine.execute(graph, initial_input)

        return {
            "success": result.success,
            "steps": [
                {
                    "node_id": s.node_id,
                    "success": s.success,
                    "output": s.output,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in result.steps
            ],
            "total_duration_ms": result.total_duration_ms,
            "final_output": result.final_output,
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openjarvis/skills/list")
async def list_skills():
    """List all discovered skills."""
    if not _skill_manager:
        return {"skills": []}

    skills = []
    for skill in _skill_manager.list_skills():
        skills.append({
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "author": skill.author,
            "tags": skill.tags,
            "steps": len(skill.steps),
        })
    return {"skills": skills}


@app.post("/api/openjarvis/skills/execute")
async def execute_skill(request: dict):
    """Execute a skill by name."""
    try:
        skill_name = request.get("skill")
        context = request.get("context", {})

        if not skill_name:
            raise HTTPException(status_code=400, detail="No skill name provided")

        if not _skill_manager:
            raise HTTPException(status_code=503, detail="Skill manager not initialized")

        result = await _skill_manager.execute(skill_name, context)
        return result
    except Exception as e:
        logger.error(f"Skill execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/openjarvis/learning/route")
async def route_query(request: dict):
    """Route a query to the appropriate model based on complexity."""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        if not _router:
            raise HTTPException(status_code=503, detail="Learning router not initialized")

        result = _router.route(query)
        return result
    except Exception as e:
        logger.error(f"Query routing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openclaw/workspace/status")
async def workspace_status():
    """Get workspace model status."""
    if not _workspace:
        return {"enabled": False}

    return {
        "enabled": True,
        "workspace_dir": str(_workspace.workspace_dir),
        "files": {
            key: {
                "name": wf.name,
                "exists": wf.exists(),
                "size": wf.path.stat().st_size if wf.exists() else 0,
            }
            for key, wf in _workspace.files.items()
        },
    }


@app.get("/api/openclaw/workspace/context")
async def workspace_context():
    """Get workspace system context for agent prompts."""
    if not _workspace:
        raise HTTPException(status_code=503, detail="Workspace not initialized")

    context = _workspace.build_system_context()
    return {"context": context}


@app.post("/api/openclaw/workspace/file")
async def workspace_file(request: dict):
    """Get or set workspace file content."""
    try:
        key = request.get("key", "")
        action = request.get("action", "get")

        if not key:
            raise HTTPException(status_code=400, detail="No file key provided")

        if not _workspace:
            raise HTTPException(status_code=503, detail="Workspace not initialized")

        if action == "get":
            content = _workspace.get_content(key)
            return {"key": key, "content": content}
        elif action == "set":
            content = request.get("content", "")
            _workspace.set_content(key, content)
            return {"key": key, "status": "updated"}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    except Exception as e:
        logger.error(f"Workspace file operation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openclaw/heartbeat/status")
async def heartbeat_status():
    """Get heartbeat system status."""
    if not _heartbeat:
        return {"enabled": False}

    return {"enabled": True, **_heartbeat.get_status()}


@app.post("/api/openclaw/heartbeat/run")
async def heartbeat_run():
    """Run due heartbeat tasks."""
    try:
        if not _heartbeat:
            raise HTTPException(status_code=503, detail="Heartbeat not initialized")

        results = await _heartbeat.run_due_tasks()
        return {"tasks_run": len(results), "results": results}
    except Exception as e:
        logger.error(f"Heartbeat run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openclaw/state/keys")
async def state_keys(namespace: str = "default"):
    """List all keys in state store."""
    if not _state_manager:
        raise HTTPException(status_code=503, detail="State manager not initialized")

    keys = _state_manager.list_keys(namespace)
    return {"namespace": namespace, "keys": keys}


@app.get("/api/openclaw/state/get/{key}")
async def state_get(key: str, namespace: str = "default"):
    """Get a value from state store."""
    if not _state_manager:
        raise HTTPException(status_code=503, detail="State manager not initialized")

    value = _state_manager.get(key, namespace)
    return {"key": key, "namespace": namespace, "value": value}


@app.post("/api/openclaw/state/set")
async def state_set(request: dict):
    """Set a value in state store."""
    try:
        key = request.get("key", "")
        value = request.get("value")
        namespace = request.get("namespace", "default")

        if not key:
            raise HTTPException(status_code=400, detail="No key provided")

        if not _state_manager:
            raise HTTPException(status_code=503, detail="State manager not initialized")

        _state_manager.set(key, value, namespace)
        return {"key": key, "namespace": namespace, "status": "set"}
    except Exception as e:
        logger.error(f"State set failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Robotics Knowledge Base Integration
# ============================================================================

# Initialize robotics knowledge base
try:
    from app.robotics_knowledge import KnowledgeBase
    from app.robotics_knowledge.domains import load_all_domains
    from app.robotics_knowledge.engine import KnowledgeEngine

    _robotics_kb = load_all_domains()
    _knowledge_engine = KnowledgeEngine(_robotics_kb)

    logger.info("Robotics knowledge base initialized successfully")
    logger.info(f"  - Domains loaded: {len(_robotics_kb.list_domains())}")
    logger.info(f"  - Total entries: {sum(len(d.entries) for d in _robotics_kb.domains.values())}")
except Exception as e:
    logger.warning(f"Robotics knowledge base initialization failed: {e}")
    _robotics_kb = None
    _knowledge_engine = None


@app.get("/api/robotics/knowledge/status")
async def robotics_knowledge_status():
    """Get robotics knowledge base status."""
    if not _robotics_kb:
        return {"status": "inactive", "error": "Knowledge base not initialized"}

    stats = _robotics_kb.get_stats()
    return {
        "status": "active",
        "domains": stats["domains"],
        "total_entries": stats["total_entries"],
        "domain_names": stats["domain_names"],
    }


@app.get("/api/robotics/domains")
async def robotics_list_domains():
    """List all available robotics knowledge domains."""
    if not _robotics_kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")

    domains = []
    for name in _robotics_kb.list_domains():
        domain = _robotics_kb.get_domain(name)
        if domain:
            domains.append({
                "name": domain.name,
                "description": domain.description,
                "entry_count": len(domain.entries),
                "subcategories": domain.subcategories,
            })
    return {"domains": domains}


@app.get("/api/robotics/domain/{domain_name}")
async def robotics_get_domain(domain_name: str):
    """Get overview of a specific robotics knowledge domain."""
    if not _knowledge_engine:
        raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

    overview = _knowledge_engine.get_domain_overview(domain_name)
    return {"domain": domain_name, "overview": overview}


@app.post("/api/robotics/query")
async def robotics_query(request: dict):
    """Query the robotics knowledge base."""
    try:
        query = request.get("query", "")
        domain = request.get("domain")
        limit = request.get("limit", 10)

        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        if not _knowledge_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        result = _knowledge_engine.query(query, domain=domain, limit=limit)
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Robotics query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robotics/explain")
async def robotics_explain(request: dict):
    """Get detailed explanation of a robotics topic."""
    try:
        topic = request.get("topic", "")
        depth = request.get("depth", "intermediate")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _knowledge_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        explanation = _knowledge_engine.explain(topic, depth=depth)
        return {"topic": topic, "depth": depth, "explanation": explanation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Robotics explain failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robotics/troubleshoot")
async def robotics_troubleshoot(request: dict):
    """Get troubleshooting help for a robotics problem."""
    try:
        problem = request.get("problem", "")

        if not problem:
            raise HTTPException(status_code=400, detail="No problem description provided")

        if not _knowledge_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        troubleshooting = _knowledge_engine.troubleshoot(problem)
        return {"problem": problem, "troubleshooting": troubleshooting}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Robotics troubleshoot failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robotics/learning-path")
async def robotics_learning_path(request: dict):
    """Get a structured learning path for a robotics topic."""
    try:
        topic = request.get("topic", "")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _knowledge_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        path = _knowledge_engine.get_learning_path(topic)
        return {"topic": topic, "learning_path": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Robotics learning path failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/robotics/entry/{entry_id}")
async def robotics_get_entry(entry_id: str):
    """Get a specific knowledge entry by ID."""
    if not _robotics_kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")

    entry = _robotics_kb.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found")

    return {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "domain": entry.domain,
        "category": entry.category,
        "tags": entry.tags,
        "difficulty": entry.difficulty.value,
        "prerequisites": entry.prerequisites,
        "related": entry.related,
        "examples": entry.examples,
        "references": entry.references,
    }


# ============================================================================
# Indian Knowledge Base Integration
# ============================================================================

# Initialize Indian knowledge base
try:
    from app.indian_knowledge import KnowledgeBase as IndianKnowledgeBase
    from app.indian_knowledge.domains import load_all_domains as load_indian_domains
    from app.indian_knowledge.engine import KnowledgeEngine as IndianKnowledgeEngine

    _indian_kb = load_indian_domains()
    _indian_engine = IndianKnowledgeEngine(_indian_kb)

    logger.info("Indian knowledge base initialized successfully")
    logger.info(f"  - Domains loaded: {len(_indian_kb.list_domains())}")
    logger.info(f"  - Total entries: {sum(len(d.entries) for d in _indian_kb.domains.values())}")
except Exception as e:
    logger.warning(f"Indian knowledge base initialization failed: {e}")
    _indian_kb = None
    _indian_engine = None


@app.get("/api/indian-knowledge/status")
async def indian_knowledge_status():
    """Get Indian knowledge base status."""
    if not _indian_kb:
        return {"status": "inactive", "error": "Knowledge base not initialized"}

    stats = _indian_kb.get_stats()
    return {
        "status": "active",
        "domains": stats["domains"],
        "total_entries": stats["total_entries"],
        "domain_names": stats["domain_names"],
    }


@app.get("/api/indian-knowledge/domains")
async def indian_knowledge_list_domains():
    """List all available Indian knowledge domains."""
    if not _indian_kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")

    domains = []
    for name in _indian_kb.list_domains():
        domain = _indian_kb.get_domain(name)
        if domain:
            domains.append({
                "name": domain.name,
                "description": domain.description,
                "entry_count": len(domain.entries),
                "subcategories": domain.subcategories,
            })
    return {"domains": domains}


@app.get("/api/indian-knowledge/domain/{domain_name}")
async def indian_knowledge_get_domain(domain_name: str):
    """Get overview of a specific Indian knowledge domain."""
    if not _indian_engine:
        raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

    overview = _indian_engine.get_domain_overview(domain_name)
    return {"domain": domain_name, "overview": overview}


@app.post("/api/indian-knowledge/query")
async def indian_knowledge_query(request: dict):
    """Query the Indian knowledge base."""
    try:
        query = request.get("query", "")
        domain = request.get("domain")
        limit = request.get("limit", 10)

        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        if not _indian_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        result = _indian_engine.query(query, domain=domain, limit=limit)
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indian knowledge query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/indian-knowledge/explain")
async def indian_knowledge_explain(request: dict):
    """Get detailed explanation of an Indian knowledge topic."""
    try:
        topic = request.get("topic", "")
        depth = request.get("depth", "intermediate")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _indian_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        explanation = _indian_engine.explain(topic, depth=depth)
        return {"topic": topic, "depth": depth, "explanation": explanation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indian knowledge explain failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/indian-knowledge/learning-path")
async def indian_knowledge_learning_path(request: dict):
    """Get a structured learning path for an Indian knowledge topic."""
    try:
        topic = request.get("topic", "")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _indian_engine:
            raise HTTPException(status_code=503, detail="Knowledge engine not initialized")

        path = _indian_engine.get_learning_path(topic)
        return {"topic": topic, "learning_path": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indian knowledge learning path failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/indian-knowledge/entry/{entry_id}")
async def indian_knowledge_get_entry(entry_id: str):
    """Get a specific Indian knowledge entry by ID."""
    if not _indian_kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")

    entry = _indian_kb.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found")

    return {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "domain": entry.domain,
        "category": entry.category,
        "tags": entry.tags,
        "difficulty": entry.difficulty.value,
        "prerequisites": entry.prerequisites,
        "related": entry.related,
        "examples": entry.examples,
        "references": entry.references,
    }


# ============================================================================
# Vedic Knowledge System Integration
# ============================================================================

# Initialize Vedic knowledge base
try:
    from app.vedic_knowledge import VedicKnowledgeBase, load_all_domains, Language
    from app.vedic_knowledge.agent import create_vedic_knowledge_agent

    _vedic_kb = load_all_domains()
    _vedic_agent = create_vedic_knowledge_agent(knowledge_base=_vedic_kb, enable_web_fallback=True)

    logger.info("Vedic knowledge system initialized successfully")
    logger.info(f"  - Domains loaded: {len(_vedic_kb.list_domains())}")
    logger.info(f"  - Total entries: {sum(len(d.entries) for d in _vedic_kb.domains.values())}")
except Exception as e:
    logger.warning(f"Vedic knowledge system initialization failed: {e}")
    _vedic_kb = None
    _vedic_agent = None


def _vedic_language(value: str) -> "Language":
    # Agent code compares `language != Language.ENGLISH`; a raw string would
    # flow through and crash response.language.value in the endpoints below.
    if "Language" not in globals():
        return value  # vedic package import failed; endpoints 503 before use
    try:
        return Language(value)
    except (ValueError, KeyError):
        return Language.ENGLISH


@app.get("/api/vedic-knowledge/status")
async def vedic_knowledge_status():
    """Get Vedic knowledge system status."""
    if not _vedic_kb:
        return {"status": "inactive", "error": "Knowledge base not initialized"}

    stats = _vedic_kb.get_stats()
    return {
        "status": "active",
        "domains": stats["domains"],
        "total_entries": stats["total_entries"],
        "total_chunks": stats.get("total_chunks", 0),
        "domain_names": stats["domain_names"],
        "version": stats.get("version", "1.0.0"),
    }


@app.get("/api/vedic-knowledge/domains")
async def vedic_knowledge_list_domains():
    """List all available Vedic knowledge domains."""
    if not _vedic_kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")

    domains = []
    for name in _vedic_kb.list_domains():
        domain = _vedic_kb.get_domain(name)
        if domain:
            domains.append({
                "name": domain.name.value,
                "description": domain.description,
                "entry_count": len(domain.entries),
                "subcategories": domain.subcategories,
            })
    return {"domains": domains}


@app.get("/api/vedic-knowledge/domain/{domain_name}")
async def vedic_knowledge_get_domain(domain_name: str):
    """Get overview of a specific Vedic knowledge domain."""
    if not _vedic_agent:
        raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

    overview = _vedic_agent.get_domain_overview(domain_name)
    return {"domain": domain_name, "overview": overview}


@app.post("/api/vedic-knowledge/query")
async def vedic_knowledge_query(request: dict):
    """Query the Vedic knowledge base with multilingual support."""
    try:
        query = request.get("query", "")
        domain = request.get("domain")
        depth = request.get("depth", "intermediate")
        language = _vedic_language(request.get("language", "en"))
        use_web_fallback = request.get("use_web_fallback", True)

        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        response = await _vedic_agent.answer(
            query=query,
            domain=domain,
            depth=depth,
            language=language,
            use_web_fallback=use_web_fallback,
        )

        return {
            "status": "success",
            "answer": response.answer,
            "sources": response.sources,
            "query": response.query,
            "language": response.language.value,
            "depth": response.depth,
            "used_web_fallback": response.used_web_fallback,
            "web_results": response.web_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/explain")
async def vedic_knowledge_explain(request: dict):
    """Get detailed explanation of a Vedic knowledge topic."""
    try:
        topic = request.get("topic", "")
        depth = request.get("depth", "intermediate")
        language = _vedic_language(request.get("language", "en"))

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        response = await _vedic_agent.explain(topic=topic, depth=depth, language=language)

        return {
            "status": "success",
            "answer": response.answer,
            "sources": response.sources,
            "topic": topic,
            "language": response.language.value,
            "depth": response.depth,
            "used_web_fallback": response.used_web_fallback,
            "web_results": response.web_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge explain failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/compare")
async def vedic_knowledge_compare(request: dict):
    """Compare a concept across two Vedic knowledge domains."""
    try:
        concept = request.get("concept", "")
        domain1 = request.get("domain1")
        domain2 = request.get("domain2")
        language = _vedic_language(request.get("language", "en"))

        if not concept or not domain1 or not domain2:
            raise HTTPException(status_code=400, detail="concept, domain1, and domain2 are required")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        response = await _vedic_agent.compare(concept, domain1, domain2, language)

        return {
            "status": "success",
            "answer": response.answer,
            "sources": response.sources,
            "query": concept,
            "language": response.language.value,
            "depth": response.depth,
            "used_web_fallback": response.used_web_fallback,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge compare failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/concept-graph")
async def vedic_knowledge_concept_graph(request: dict):
    """Get concept relationship graph from corpus evidence."""
    try:
        concept = request.get("concept", "")

        if not concept:
            raise HTTPException(status_code=400, detail="No concept provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        graph = await _vedic_agent.get_concept_graph(concept)

        return {
            "status": "success",
            "concept": concept,
            "graph": graph,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge concept graph failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/learning-path")
async def vedic_knowledge_learning_path(request: dict):
    """Get a structured learning path for a Vedic knowledge topic."""
    try:
        topic = request.get("topic", "")

        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        path = _vedic_agent.get_learning_path(topic)

        return {"topic": topic, "learning_path": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge learning path failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/search")
async def vedic_knowledge_search(request: dict):
    """Direct search without answer generation."""
    try:
        query = request.get("query", "")
        domain = request.get("domain")
        limit = request.get("limit", 10)
        language = _vedic_language(request.get("language", "en"))

        if not query:
            raise HTTPException(status_code=400, detail="No query provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        result = _vedic_agent.search(query, domain=domain, limit=limit, language=language)

        return {"status": "success", "result": result.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/ingest")
async def vedic_knowledge_ingest(request: dict):
    """Ingest corpus from a file or directory path."""
    try:
        path = request.get("path", "")

        if not path:
            raise HTTPException(status_code=400, detail="No path provided")

        if not _vedic_agent:
            raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

        result = _vedic_agent.ingest_corpus(path)

        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic knowledge ingest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vedic-knowledge/validate")
async def vedic_knowledge_validate():
    """Validate the Vedic knowledge corpus."""
    if not _vedic_agent:
        raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

    result = _vedic_agent.validate_corpus()
    return {"status": "success", "validation": result}


@app.get("/api/vedic-knowledge/report")
async def vedic_knowledge_report():
    """Get corpus validation report."""
    if not _vedic_agent:
        raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

    report = _vedic_agent.get_corpus_report()
    return {"status": "success", "report": report}


@app.get("/api/vedic-knowledge/stats")
async def vedic_knowledge_stats():
    """Get Vedic knowledge agent and corpus statistics."""
    if not _vedic_agent:
        raise HTTPException(status_code=503, detail="Vedic knowledge agent not initialized")

    stats = _vedic_agent.get_stats()
    return {"status": "success", "stats": stats}


# ============================================================================
# Model Configuration Registry
# ============================================================================

try:
    from app.configs.model_config import get_model_registry

    _model_registry = get_model_registry()
    logger.info(f"Model configuration registry initialized: {len(_model_registry.models)} models")
except Exception as e:
    logger.warning(f"Model configuration registry initialization failed: {e}")
    _model_registry = None


@app.get("/api/models")
async def list_models():
    """List all configured models with their capabilities."""
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")

    return {"models": _model_registry.list_models()}


@app.get("/api/models/{model_id}")
async def get_model(model_id: str):
    """Get detailed configuration for a specific model."""
    if not _model_registry:
        raise HTTPException(status_code=503, detail="Model registry not initialized")

    config = _model_registry.get(model_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    return {
        "id": config.id,
        "name": config.name,
        "provider": config.provider,
        "type": config.type,
        "version": config.version,
        "description": config.description,
        "capabilities": {
            "text_generation": config.capabilities.text_generation,
            "tool_use": config.capabilities.tool_use,
            "function_calling": config.capabilities.function_calling,
            "vision": config.capabilities.vision,
            "streaming": config.capabilities.streaming,
            "structured_output": config.capabilities.structured_output,
            "json_mode": config.capabilities.json_mode,
            "reasoning": config.capabilities.reasoning,
            "extended_thinking": config.capabilities.extended_thinking,
        },
        "limits": {
            "context_window": config.limits.context_window,
            "max_output_tokens": config.limits.max_output_tokens,
            "max_tool_calls_per_turn": config.limits.max_tool_calls_per_turn,
            "request_timeout_seconds": config.limits.request_timeout_seconds,
        },
        "parameters": {
            "default_temperature": config.parameters.default_temperature,
            "default_top_p": config.parameters.default_top_p,
        },
        "api": {
            "endpoint": config.api_endpoint,
            "supports_responses_api": config.supports_responses_api,
            "fallback_model": config.fallback_model,
        },
        "fallback_chain": _model_registry.get_fallback_chain(model_id),
    }


# ============================================================================
# JARVIS Core Infrastructure — Orchestrator, Agents, Vision, Robotics, etc.
# ============================================================================

try:
    from app.jarvis_orchestrator import get_orchestrator
    from app.agent_manager import get_agent_manager
    from app.vision_service import get_vision_service
    from app.robotics_service import get_robotics_service
    from app.remote_service import get_remote_service
    from app.adaptive_memory import get_adaptive_memory
    from app.core.permissions import get_permission_manager
    from app.core.error_recovery import get_recovery_engine
    from app.core.event_bus import get_event_bus

    _orchestrator = get_orchestrator()
    _agent_manager = get_agent_manager()
    _orchestrator.set_agent_manager(_agent_manager)
    _vision_service = get_vision_service()
    _robotics_service = get_robotics_service()
    _remote_service = get_remote_service()
    _adaptive_memory = get_adaptive_memory()
    _permission_manager = get_permission_manager()
    _recovery_engine = get_recovery_engine()
    _event_bus = get_event_bus()

    _core_initialized = True
    logger.info("[MAIN] JARVIS core infrastructure initialized")
except Exception as e:
    logger.warning(f"[MAIN] Core infrastructure initialization failed: {e}")
    _core_initialized = False


@app.get("/api/jarvis/status")
async def jarvis_status():
    """Complete JARVIS system status — all subsystems."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    return {
        "orchestrator": _orchestrator.get_stats(),
        "agents": _agent_manager.get_stats(),
        "vision": _vision_service.get_stats(),
        "robotics": _robotics_service.get_full_status(),
        "remote": _remote_service.get_stats(),
        "memory": _adaptive_memory.get_stats(),
        "permissions": _permission_manager.get_stats(),
        "recovery": _recovery_engine.get_recovery_stats(),
        "events": _event_bus.get_stats(),
    }


@app.post("/api/jarvis/process")
async def jarvis_process(request: dict):
    """Process a user input through the central orchestrator."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    user_input = request.get("input", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="No input provided")

    result = await _orchestrator.process_input(user_input, request.get("context"))
    return result.to_dict()


@app.get("/api/jarvis/tasks")
async def jarvis_tasks():
    """Get active and recent tasks."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    return {
        "active": _orchestrator.get_active_tasks(),
        "history": _orchestrator.get_task_history(),
    }


@app.get("/api/jarvis/tasks/{task_id}")
async def jarvis_task_status(task_id: str):
    """Get status of a specific task."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    status = _orchestrator.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return status


@app.get("/api/agents")
async def list_agents(category: str | None = None):
    """List all agents with their status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    return {
        "agents": _agent_manager.list_agents(category=category),
        "by_category": _agent_manager.get_agents_by_category(),
        "stats": _agent_manager.get_stats(),
    }


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get details for a specific agent."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    agent = _agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return agent.to_dict()


@app.post("/api/agents/{agent_id}/execute")
async def execute_agent(agent_id: str, request: dict):
    """Execute a specific agent with given arguments."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    result = await _agent_manager.execute_agent(
        agent_id, request.get("args", {}), context=request.get("context")
    )
    return result.to_dict()


@app.get("/api/vision/status")
async def vision_status():
    """Get computer vision service status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return _vision_service.get_stats()


@app.post("/api/vision/process")
async def vision_process():
    """Process a single vision frame."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    frame = await _vision_service.process_frame()
    return frame.to_dict()


@app.get("/api/vision/events")
async def vision_events(limit: int = 20):
    """Get recent visual events."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return {"events": _vision_service.get_recent_events(limit)}


@app.post("/api/vision/start")
async def vision_start():
    """Start the vision service."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    await _vision_service.start()
    return {"status": "started"}


@app.post("/api/vision/stop")
async def vision_stop():
    """Stop the vision service."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    await _vision_service.stop()
    return {"status": "stopped"}


@app.get("/api/robotics/status")
async def robotics_status():
    """Get complete robotics system status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return _robotics_service.get_full_status()


@app.get("/api/robotics/state")
async def robotics_state():
    """Get current robot state."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return _robotics_service.robot_state.to_dict()


@app.get("/api/robotics/map")
async def robotics_map():
    """Get semantic map locations."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return {
        "locations": _robotics_service.semantic_map.get_all_locations(),
        "stats": _robotics_service.semantic_map.get_stats(),
    }


@app.post("/api/robotics/navigate")
async def robotics_navigate(request: dict):
    """Navigate robot to a named location."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    location = request.get("location", "")
    if not location:
        raise HTTPException(status_code=400, detail="No location provided")

    result = await _robotics_service.navigate_to(location)
    return result


@app.post("/api/robotics/emergency-stop")
async def robotics_emergency_stop():
    """Activate emergency stop."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    await _robotics_service.emergency_stop()
    return {"status": "emergency_stop_activated"}


@app.post("/api/robotics/reset")
async def robotics_reset():
    """Reset robot state."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    await _robotics_service.reset()
    return {"status": "reset"}


@app.post("/api/remote/connect")
async def remote_connect(request: dict):
    """Connect a remote client."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    client_id = request.get("client_id", "")
    client_secret = request.get("client_secret", "")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="client_id and client_secret required")

    result = await _remote_service.connect(client_id, client_secret, request.get("ip_address", ""))
    return result


@app.post("/api/remote/command")
async def remote_command(request: dict):
    """Send a command through remote access."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    session_id = request.get("session_id", "")
    command = request.get("command", "")
    if not session_id or not command:
        raise HTTPException(status_code=400, detail="session_id and command required")

    result = await _remote_service.send_command(
        session_id, command, request.get("args", {}), request.get("token", "")
    )
    return result


@app.post("/api/remote/emergency-stop")
async def remote_emergency_stop():
    """Activate emergency stop via remote."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    await _remote_service.emergency_stop()
    return {"status": "emergency_stop_activated"}


@app.get("/api/remote/sessions")
async def remote_sessions():
    """Get active remote sessions."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return {
        "sessions": _remote_service.get_active_sessions(),
        "commands": _remote_service.get_command_history(),
        "audit": _remote_service.get_audit_log(),
        "stats": _remote_service.get_stats(),
    }


@app.get("/api/memory/status")
async def memory_status():
    """Get adaptive memory status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return _adaptive_memory.get_stats()


@app.post("/api/memory/search")
async def memory_search(request: dict):
    """Search adaptive memory."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    results = _adaptive_memory.retrieve(query, limit=request.get("limit", 10))
    return {"results": [r.to_dict() for r in results]}


@app.get("/api/permissions/status")
async def permissions_status():
    """Get permission system status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return {
        "stats": _permission_manager.get_stats(),
        "pending": _permission_manager.get_pending_confirmations(),
        "recent_audit": _permission_manager.get_audit_log(),
    }


@app.post("/api/permissions/confirm")
async def permissions_confirm(request: dict):
    """Confirm a pending permission check."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")

    check_id = request.get("check_id", "")
    if not check_id:
        raise HTTPException(status_code=400, detail="No check_id provided")

    success = _orchestrator.confirm_permission(check_id, request.get("confirmed_by", "user"))
    return {"confirmed": success}


@app.get("/api/recovery/status")
async def recovery_status():
    """Get error recovery system status."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return _recovery_engine.get_recovery_stats()


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent system events."""
    if not _core_initialized:
        raise HTTPException(status_code=503, detail="Core infrastructure not initialized")
    return {"events": _event_bus.get_recent_events(limit), "stats": _event_bus.get_stats()}

