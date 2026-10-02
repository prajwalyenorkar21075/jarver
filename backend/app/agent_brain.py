import os
import re
import time
import json
import logging
import urllib.parse
import subprocess
from pathlib import Path
import psutil
import httpx

logger = logging.getLogger("jarvis.brain")

# Load environment
APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
WORKSPACE_ROOT = BASE_DIR.parent  # D:\New folder (4)
NOTES_DIR = WORKSPACE_ROOT / "notes"
NOTES_DIR.mkdir(exist_ok=True)

# Parse .env if not loaded
env_file = BASE_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")
OPENAI_RESPONSES_API_URL = os.getenv("OPENAI_RESPONSES_API_URL", "https://api.openai.com/v1/responses")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Global in-memory safety state for destructive/sensitive actions
PENDING_SAFETY_ACTION: dict | None = None
SAFETY_ACTION_TIMEOUT = 60.0  # Confirmation valid for 60 seconds

# Fast failover cooldown for OpenAI 429 quota exhaustion to prevent 2-3s silent delays
_openai_quota_cooldown_until: float = 0.0


# Global multi-turn conversation memory for context & follow-ups
CONVERSATION_MEMORY: list[dict] = []
MAX_MEMORY_TURNS = 20

# Persistent storage engine import
try:
    from app.persistent_memory import (
        init_database,
        save_conversation_turn,
        get_recent_conversations,
        save_memory,
        get_memories,
        create_task,
        list_tasks,
        update_task_status,
        get_all_preferences,
        get_preference,
        set_preference,
        create_backup_snapshot,
        enable_windows_autostart,
        disable_windows_autostart,
        is_windows_autostart_enabled,
    )
except ImportError:
    from persistent_memory import (
        init_database,
        save_conversation_turn,
        get_recent_conversations,
        save_memory,
        get_memories,
        create_task,
        list_tasks,
        update_task_status,
        get_all_preferences,
        get_preference,
        set_preference,
        create_backup_snapshot,
        enable_windows_autostart,
        disable_windows_autostart,
        is_windows_autostart_enabled,
    )

try:
    from app.biometric_engine import identity_manager
except ImportError:
    from biometric_engine import identity_manager


def load_persisted_conversation_memory():
    """Load latest conversation history from SQLite into memory on boot."""
    global CONVERSATION_MEMORY
    try:
        init_database()
        stored_turns = get_recent_conversations(limit=20)
        CONVERSATION_MEMORY = [{"role": t["role"], "content": t["content"]} for t in stored_turns]
        logger.info(f"Loaded {len(CONVERSATION_MEMORY)} conversation turns from persistent storage.")
    except Exception as e:
        logger.error(f"Error loading persisted conversations: {e}")
        CONVERSATION_MEMORY = []

# Initialize and restore persistent memory immediately
load_persisted_conversation_memory()

JARVIS_EXPERT_SYSTEM_PROMPT = """You are J.A.R.V.I.S., Tony Stark's personal AI companion and high-performance operating system.
Persona: Highly articulate, polite, composed, brilliant, with refined British wit and Stark Industries sophistication.

Core Multitasking & Knowledge Capabilities:
1. Natural Multilingual Proficiency: Speak and understand English, Marathi (मराठी), Hindi (हिंदी), Hinglish, Marathlish, and code-mixed vernacular naturally.
2. AI, Machine Learning & Deep Learning Mastery:
   - Deep theoretical and practical mastery of Transformers (Self-Attention, FlashAttention, Rotary Position Embeddings / RoPE, KV Caching, Multi-Head / Grouped-Query Attention, Mixture of Experts / MoE).
   - Neural network training, optimization algorithms (AdamW, Lion, SGD with Momentum, Cosine Annealing, Gradient Clipping, Loss Scaling).
   - LLMs, Fine-tuning (LoRA, QLoRA, SFT, DPO, PPO, RLHF), Quantization (GGUF, AWQ, GPTQ, FP8, INT4).
   - Computer Vision (CNNs, Vision Transformers / ViTs, Diffusion models, YOLO, Semantic Segmentation).
   - Production PyTorch, JAX, HuggingFace, ONNX, and CUDA code generation, architecture explanation, and debugging.
3. Desktop & System Control:
   - Real PC control: opening/closing applications, camera feed, music/media, file management, system diagnostics, and safe shutdown/restart with confirmation.
4. Persistent Memory Awareness:
   - You remember past conversations, tasks, and facts across workstation shutdowns and reboots.
5. Voice & Tone:
   - Keep answers crisp, articulate, and direct (1-3 sentences for spoken voice responses, with rich technical depth when asked for code or deep explanations).
   - Match the user's language (if user asks in Marathi, answer in polished Marathi; if in Hindi, polished Hindi; if in English, refined British Jarvis; if mixed, natural vernacular).
"""


def build_augmented_system_prompt() -> str:
    """Build system prompt dynamically augmented with persistent memories, user preferences, and pending tasks."""
    try:
        prefs = get_all_preferences()
        user_title = prefs.get("user_name", "Sir")
        
        # Pending tasks
        pending = list_tasks(status="pending")[:6]
        if pending:
            tasks_lines = [f"- [Task #{t['id']}] {t['title']} ({t['priority']} priority)" for t in pending]
            tasks_block = "\n".join(tasks_lines)
        else:
            tasks_block = "No pending tasks."

        # Memories
        memories = get_memories(limit=8)
        if memories:
            mem_lines = [f"- {m['title']}: {m['content']}" for m in memories]
            mem_block = "\n".join(mem_lines)
        else:
            mem_block = "No personal memory entries recorded yet."

        autostart_status = "Enabled" if is_windows_autostart_enabled() else "Disabled"

        # Biometric Identity & Speaker Verification State
        bio_state = identity_manager.get_state()
        recognized_user = bio_state.get("display_name", "Tony Stark")
        user_role = bio_state.get("role", "owner").upper()
        face_status = f"VERIFIED ({int(bio_state['face_confidence']*100)}% match)" if bio_state.get("face_matched") else "Standby / Off-camera"
        voice_status = f"VERIFIED ({int(bio_state['voice_confidence']*100)}% match)" if bio_state.get("voice_matched") else "Standby"
        
        if bio_state.get("role") == "owner":
            guidance = f"The active user is identified as {recognized_user} (Primary Owner). Address with utmost Stark loyalty (Sir/Tony Stark). All workstation permissions, multitasking, and destructive system actions (subject to confirmation) are authorized."
        else:
            guidance = f"The active user is detected as GUEST / UNRECOGNIZED USER. Address politely as Guest (or 'पाहुणे'/'अतिथी'). Restrict destructive workstation actions (e.g. shutdown, process termination, file deletions). Inform them that administrative control requires Tony Stark's biometric authorization."

        return f"""{JARVIS_EXPERT_SYSTEM_PROMPT}

Biometric Recognition & Active Security State:
- Identified User: {recognized_user} [ROLE: {user_role}]
- Facial Verification: {face_status}
- Voice Identification: {voice_status}
- Camera Active: {"ON" if bio_state.get("camera_active") else "OFF"} | Mic Active: {"ON" if bio_state.get("mic_active") else "OFF"}
- Interaction Guidance: {guidance}

User Profile & Persistent State (Restored from local storage):
- Addressing Salutation: {user_title}
- Windows Auto-Start: {autostart_status}
- Persistent Memories & Observations:
{mem_block}

Current Active Task Board:
{tasks_block}
"""
    except Exception as e:
        logger.error(f"Prompt augmentation error: {e}")
        return JARVIS_EXPERT_SYSTEM_PROMPT


def get_system_telemetry() -> dict:
    """Retrieve real-time hardware telemetry: CPU, RAM, Disk, Battery, Process count."""
    try:
        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(WORKSPACE_ROOT))
        battery = psutil.sensors_battery()
        
        battery_data = None
        if battery:
            battery_data = {
                "percent": round(battery.percent, 1),
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft if battery.secsleft > 0 else None,
            }

        return {
            "status": "ok",
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "battery": battery_data,
            "active_processes": len(psutil.pids()),
            "timestamp": time.strftime("%H:%M:%S"),
        }
    except Exception as e:
        logger.error(f"Telemetry error: {e}")
        return {"status": "error", "error": str(e)}


def close_application(target: str) -> dict:
    """Safely terminate target application processes on Windows."""
    clean_target = target.lower().strip()
    
    app_to_processes = {
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "browser": ["chrome.exe", "msedge.exe"],
        "edge": ["msedge.exe", "edge.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["CalculatorApp.exe", "calc.exe", "Calculator.exe"],
        "camera": ["WindowsCamera.exe"],
        "webcam": ["WindowsCamera.exe"],
        "paint": ["mspaint.exe"],
        "spotify": ["spotify.exe"],
        "explorer": ["explorer.exe"],
        "terminal": ["WindowsTerminal.exe", "wt.exe", "cmd.exe", "powershell.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "vscode": ["Code.exe"],
        "code": ["Code.exe"],
        "task manager": ["taskmgr.exe"],
        "taskmgr": ["taskmgr.exe"],
    }
    
    targets = app_to_processes.get(clean_target, [f"{clean_target}.exe"])
    closed_count = 0
    
    for p in psutil.process_iter(['pid', 'name']):
        try:
            p_name = p.info['name']
            if p_name and any(t.lower() == p_name.lower() for t in targets):
                p.terminate()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    if closed_count > 0:
        return {
            "success": True,
            "closed_count": closed_count,
            "target": clean_target,
            "reply": f"Terminated {clean_target.title()} ({closed_count} instances closed), sir.",
        }
    return {
        "success": False,
        "closed_count": 0,
        "target": clean_target,
        "reply": f"No active instances of {clean_target.title()} were found running, sir.",
    }


def manage_workspace_files(action: str, target: str = "", content: str = "") -> dict:
    """Safe file manager strictly restricted to user's workspace (D:\\New folder (4))."""
    try:
        if action == "list":
            sub = (target or "").strip().lstrip("/\\")
            target_dir = (WORKSPACE_ROOT / sub).resolve()
            if not str(target_dir).startswith(str(WORKSPACE_ROOT.resolve())):
                return {"success": False, "reply": "Access denied: Path outside permitted workspace."}
            if not target_dir.exists():
                return {"success": False, "reply": f"Directory not found: {sub or 'root'}"}
                
            items = []
            for item in sorted(target_dir.iterdir()):
                if item.name.startswith("."):
                    continue
                is_dir = item.is_dir()
                size = item.stat().st_size if not is_dir else 0
                items.append({
                    "name": item.name,
                    "is_dir": is_dir,
                    "size_kb": round(size / 1024, 1) if not is_dir else None,
                })
            count = len(items)
            return {
                "success": True,
                "action": "list",
                "count": count,
                "items": items[:25],
                "reply": f"Indexed {count} files in your workspace directory, sir.",
            }

        elif action == "save_note":
            title = (target or f"note_{int(time.time())}").strip().replace(" ", "_")
            if not title.endswith(".txt") and not title.endswith(".md"):
                title += ".txt"
            file_path = NOTES_DIR / title
            file_path.write_text(content or "Note recorded by JARVIS.", encoding="utf-8")
            return {
                "success": True,
                "action": "save_note",
                "filename": title,
                "path": str(file_path),
                "reply": f"Saved note '{title}' to your notes archive, sir.",
            }

        elif action == "read":
            clean_name = target.strip()
            # Look in notes or workspace
            candidate = NOTES_DIR / clean_name
            if not candidate.exists():
                candidate = WORKSPACE_ROOT / clean_name
            if not candidate.exists() and not clean_name.endswith(".txt"):
                candidate = NOTES_DIR / (clean_name + ".txt")
            if not candidate.exists():
                return {"success": False, "reply": f"Could not locate file '{clean_name}', sir."}
                
            text = candidate.read_text(encoding="utf-8", errors="replace")[:1500]
            return {
                "success": True,
                "action": "read",
                "filename": candidate.name,
                "content": text,
                "reply": f"Reading '{candidate.name}': {text[:160]}...",
            }

        elif action == "search":
            q = target.lower().strip()
            matches = []
            for root, dirs, files in os.walk(str(WORKSPACE_ROOT)):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != ".venv"]
                for f in files:
                    if q in f.lower():
                        rel = os.path.relpath(os.path.join(root, f), str(WORKSPACE_ROOT))
                        matches.append(rel)
                        if len(matches) >= 15:
                            break
            return {
                "success": True,
                "action": "search",
                "query": q,
                "count": len(matches),
                "matches": matches,
                "reply": f"Found {len(matches)} matching files for '{q}' in your workspace, sir.",
            }
            
        return {"success": False, "reply": "Unsupported file operation."}
    except Exception as e:
        logger.error(f"File operation error: {e}")
        return {"success": False, "reply": f"File manager encountered an error: {e}"}


def check_and_handle_safety_confirmation(user_text: str) -> dict | None:
    """Evaluate if the user's input is a confirmation or cancellation of a pending safety action."""
    global PENDING_SAFETY_ACTION
    if not PENDING_SAFETY_ACTION:
        return None

    # Check timeout
    elapsed = time.time() - PENDING_SAFETY_ACTION["timestamp"]
    if elapsed > SAFETY_ACTION_TIMEOUT:
        PENDING_SAFETY_ACTION = None
        return None

    lower = user_text.lower().strip()
    action = PENDING_SAFETY_ACTION["action"]

    # Positive confirmation words across English, Marathi, Hindi
    confirm_words = [
        "yes", "confirm", "proceed", "execute", "do it", "sure", "ok", "okay",
        "हो", "करा", "चालू करा", "बंद करा", "होय", "नक्की", "करून टाका",
        "हाँ", "करो", "हां", "कन्फर्म", "बिलकुल", "कर दो", "शटडाउन करो"
    ]
    
    # Cancellation words
    cancel_words = [
        "no", "cancel", "abort", "stop", "wait", "don't", "nevermind",
        "नाही", "नको", "थांब", "थांबा", "रद्द करा", "रद्द",
        "नहीं", "मत करो", "रुको", "कैंसिल", "रद्द करो"
    ]

    if any(w in lower for w in cancel_words) or lower in ["no", "cancel", "abort", "थांब", "नको"]:
        PENDING_SAFETY_ACTION = None
        if action in ["shutdown_pc", "restart_pc"]:
            try:
                subprocess.Popen("shutdown /a", shell=True)
            except Exception:
                pass
        return {
            "success": True,
            "action": "cancel_safety_action",
            "reply": "Destructive operation cancelled, sir. All workstation systems remain safe and nominal.",
        }

    if any(w in lower for w in confirm_words) or lower in ["yes", "confirm", "हो", "हाँ", "y"]:
        PENDING_SAFETY_ACTION = None
        if action == "shutdown_pc":
            logger.info("Executing confirmed system shutdown (grace period: 25s)...")
            try:
                create_backup_snapshot()
            except Exception:
                pass
            subprocess.Popen("shutdown /s /t 25", shell=True)
            return {
                "success": True,
                "action": "shutdown_pc",
                "reply": "Confirmation acknowledged, sir. Workstation shutdown protocol initiated (25s grace period). Issue 'cancel shutdown' at any time to abort.",
            }
        elif action == "restart_pc":
            logger.info("Executing confirmed system restart (grace period: 25s)...")
            try:
                create_backup_snapshot()
            except Exception:
                pass
            subprocess.Popen("shutdown /r /t 25", shell=True)
            return {
                "success": True,
                "action": "restart_pc",
                "reply": "Confirmation acknowledged, sir. Workstation reboot sequence initiated (25s grace period). Issue 'cancel shutdown' at any time to abort.",
            }

    return None


def request_safety_confirmation(action: str, prompt: str) -> dict:
    """Register a pending sensitive action requiring explicit user confirmation."""
    global PENDING_SAFETY_ACTION
    PENDING_SAFETY_ACTION = {
        "action": action,
        "timestamp": time.time(),
        "prompt": prompt,
    }
    return {
        "success": False,
        "requires_confirmation": True,
        "safety_action": action,
        "reply": prompt,
    }


def execute_system_actions(actions_list: list[dict], reply: str) -> dict:
    """Safely execute extracted system actions (single or compound multitasking)."""
    from app.system_controller import launch_app, open_url, COMMON_APPS, COMMON_WEBSITES

    executed_actions = []
    for act in actions_list:
        atype = (act.get("action_type") or "").lower()
        atarget = (act.get("target") or "").strip()
        aquery = (act.get("query") or "").strip()

        # 1. Camera launch
        if atype in ["open_camera", "camera_on", "camera_control"] or (atype == "open_app" and atarget.lower() in ["camera", "webcam"]):
            launch_app("microsoft.windows.camera:")
            executed_actions.append({"action": "open_camera", "target": "microsoft.windows.camera:"})

        # 2. Play music / song
        elif atype in ["play_music", "play_song"]:
            q = aquery or atarget or "trending hit songs"
            resolved = None
            try:
                from app.system_controller import resolve_youtube_video
                resolved = resolve_youtube_video(q)
            except Exception as e:
                logger.warning(f"YouTube video resolution failed for '{q}': {e}")

            if resolved:
                # The frontend opens the in-app player with this id and autoplays it.
                executed_actions.append({
                    "action": "play_music",
                    "target": resolved["url"],
                    "url": resolved["url"],
                    "video_id": resolved["video_id"],
                    "title": resolved.get("title"),
                    "query": q,
                    "play": True,
                })
            else:
                u = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
                open_url(u)
                executed_actions.append({"action": "play_music", "target": u, "query": q})

        # 3. YouTube Search
        elif atype in ["search_youtube", "youtube_search"]:
            q = aquery or atarget or "Iron Man"
            u = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            open_url(u)
            executed_actions.append({"action": "search_youtube", "target": u, "query": q})

        # 4. Google Search / Web Search
        elif atype in ["search_google", "web_search", "google_search"]:
            q = aquery or atarget or "Jarvis AI"
            u = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            open_url(u)
            executed_actions.append({"action": "search_google", "target": u, "query": q})

        # 5. Open native app
        elif atype == "open_app":
            app_lower = atarget.lower()
            exec_target = COMMON_APPS.get(app_lower, f"{atarget}.exe")
            launch_app(exec_target)
            executed_actions.append({"action": "open_app", "target": exec_target})

        # 6. Open website
        elif atype == "open_website":
            site_lower = atarget.lower()
            site_url = COMMON_WEBSITES.get(site_lower, f"https://www.{atarget}.com" if not atarget.startswith("http") else atarget)
            open_url(site_url)
            executed_actions.append({"action": "open_website", "target": site_url})

        # 7. Close app
        elif atype == "close_app":
            close_res = close_application(atarget)
            executed_actions.append({"action": "close_app", "target": atarget, "closed": close_res["success"]})

        # 8. File management
        elif atype in ["manage_files", "file_op"]:
            sub_action = act.get("sub_action", "list")
            f_res = manage_workspace_files(sub_action, target=atarget, content=aquery)
            executed_actions.append({"action": "manage_files", "details": f_res})

        # 9. System telemetry
        elif atype in ["system_telemetry", "system_status"]:
            telem = get_system_telemetry()
            executed_actions.append({"action": "system_telemetry", "telemetry": telem})

        # 10. Shutdown or restart (SAFETY CONFIRMATION GATE)
        elif atype in ["shutdown_pc", "turn_off_pc"]:
            return request_safety_confirmation(
                "shutdown_pc",
                "Sir, you have requested a full workstation shutdown. Are you certain you wish to proceed? Please confirm with 'Confirm' / 'Yes' / 'हो', or 'Cancel' to abort."
            )
        elif atype in ["restart_pc", "reboot_pc"]:
            return request_safety_confirmation(
                "restart_pc",
                "Sir, you have requested a workstation reboot. Do you confirm system restart? Please respond with 'Confirm' / 'Yes' / 'हो', or 'Cancel' to abort."
            )

    return {
        "success": True,
        "is_compound": len(executed_actions) > 1,
        "executed_actions": executed_actions,
        "reply": reply,
    }


async def parse_and_execute_multitask(text: str, conversation_history: list[dict] | None = None) -> dict:
    """Core Multitasking Agent Brain:
    1. Checks active safety confirmation.
    2. Identifies single or compound instructions (multitasking).
    3. Handles permanent task management, memory storage, backups, and autostart.
    4. Manages files, system apps, close app commands, telemetry, and shutdown gates.
    5. Seamlessly responds to deep AI/ML/DL queries and natural conversation across English, Marathi, Hindi, and code-mixed vernacular.
    6. Automatically stores all turns permanently in SQLite.
    """
    global CONVERSATION_MEMORY
    clean_text = text.strip()
    if not clean_text:
        return {"success": False, "reply": "Standing by, sir."}

    # 1. Check if user is confirming or cancelling a pending safety action
    safety_res = check_and_handle_safety_confirmation(clean_text)
    if safety_res:
        save_conversation_turn("user", clean_text, intent="safety_confirmation")
        save_conversation_turn("assistant", safety_res["reply"], intent="safety_confirmation")
        return safety_res

    lower = clean_text.lower()

    # 2. Cancel Shutdown direct trigger ("cancel shutdown", "abort shutdown", "थांब")
    if "cancel shutdown" in lower or "abort shutdown" in lower or "shutdown cancel" in lower or lower == "थांब":
        try:
            subprocess.Popen("shutdown /a", shell=True)
        except Exception:
            pass
        reply = "System shutdown protocol has been aborted, sir. The workstation remains active."
        save_conversation_turn("user", clean_text, intent="cancel_shutdown")
        save_conversation_turn("assistant", reply, intent="cancel_shutdown")
        return {
            "success": True,
            "action": "cancel_shutdown",
            "reply": reply,
        }

    # 3. Shutdown / Restart Intent (MANDATORY SAFETY CONFIRMATION GATE & BIOMETRIC PERMISSION CHECK)
    is_shutdown_phrase = (
        any(k in lower for k in ["shut down", "shutdown", "turn off", "power off", "बंद कर", "बंद करा", "बंद करो", "शटडाउन"]) and
        any(t in lower for t in ["pc", "computer", "system", "workstation", "कॉम्प्युटर", "कंप्यूटर", "पीसी", "सिस्टम", "लॅपटॉप", "machine"])
    ) or lower in ["shut down", "shutdown", "turn off pc", "power off", "कॉम्प्युटर बंद कर", "पीसी बंद करा", "कंप्यूटर बंद करो"]

    if is_shutdown_phrase:
        allowed, reason = identity_manager.verify_permission("shutdown_pc")
        if not allowed:
            reply = f"Access denied. Workstation shutdown is restricted to Tony Stark (Primary Owner). {reason}"
            save_conversation_turn("user", clean_text, intent="unauthorized_shutdown")
            save_conversation_turn("assistant", reply, intent="unauthorized_shutdown")
            return {"success": False, "reply": reply, "blocked_by_biometrics": True}

        save_conversation_turn("user", clean_text, intent="shutdown_request")
        res = request_safety_confirmation(
            "shutdown_pc",
            "Sir, you have requested a full workstation shutdown. This will terminate all active programs. Are you certain you wish to proceed? Please confirm with 'Confirm' / 'Yes' / 'हो', or 'Cancel' to abort."
        )
        save_conversation_turn("assistant", res["reply"], intent="shutdown_confirm_gate")
        return res

    is_restart_phrase = (
        any(k in lower for k in ["restart", "reboot", "रीस्टार्ट", "रीबूट"]) and
        any(t in lower for t in ["pc", "computer", "system", "workstation", "कॉम्प्युटर", "कंप्यूटर", "पीसी", "सिस्टम", "लॅपटॉप", "machine"])
    ) or lower in ["restart pc", "reboot pc", "restart", "reboot", "कॉम्प्युटर रीस्टार्ट करा"]

    if is_restart_phrase:
        allowed, reason = identity_manager.verify_permission("restart_pc")
        if not allowed:
            reply = f"Access denied. Workstation reboot is restricted to Tony Stark (Primary Owner). {reason}"
            save_conversation_turn("user", clean_text, intent="unauthorized_restart")
            save_conversation_turn("assistant", reply, intent="unauthorized_restart")
            return {"success": False, "reply": reply, "blocked_by_biometrics": True}

        save_conversation_turn("user", clean_text, intent="restart_request")
        res = request_safety_confirmation(
            "restart_pc",
            "Sir, you have requested a workstation reboot. Do you confirm system restart? Please respond with 'Confirm' / 'Yes' / 'हो', or 'Cancel' to abort."
        )
        save_conversation_turn("assistant", res["reply"], intent="restart_confirm_gate")
        return res

    # 4. Task Management Direct Intents
    if lower.startswith("add task") or lower.startswith("new task") or lower.startswith("task:") or lower.startswith("टास्क जोडा") or lower.startswith("काम जोडा") or lower.startswith("टास्क लिखो") or lower.startswith("टास्क बनाओ") or lower.startswith("एक टास्क लिखो"):
        task_title = re.sub(r"^(add task:?|new task:?|task:?|टास्क जोडा:?|काम जोडा:?|टास्क लिखो:?|टास्क बनाओ:?|एक टास्क लिखो:?)", "", clean_text, flags=re.IGNORECASE).strip()
        if task_title:
            new_task = create_task(task_title, priority="medium")
            reply = f"Task #{new_task['id']} ('{task_title}') has been permanently saved to your task board, sir."
            save_conversation_turn("user", clean_text, intent="create_task")
            save_conversation_turn("assistant", reply, intent="create_task")
            return {"success": True, "action": "create_task", "task": new_task, "reply": reply}

    if any(k in lower for k in ["show tasks", "list tasks", "my tasks", "view tasks", "pending tasks", "माझे काम दाखव", "टास्क दाखवा", "टास्क दाखव", "टास्क दिखाओ", "मेरे टास्क"]):
        tasks = list_tasks(status="pending")
        if tasks:
            task_list_str = "; ".join([f"#{t['id']} {t['title']}" for t in tasks[:5]])
            reply = f"You have {len(tasks)} active tasks on your persistent board: {task_list_str}, sir."
        else:
            reply = "You currently have no pending tasks on your persistent board, sir."
        save_conversation_turn("user", clean_text, intent="list_tasks")
        save_conversation_turn("assistant", reply, intent="list_tasks")
        return {"success": True, "action": "list_tasks", "tasks": tasks, "reply": reply}

    if lower.startswith("complete task") or lower.startswith("finish task") or lower.startswith("done task") or "टास्क पूर्ण झाले" in lower or "टास्क खत्म" in lower:
        match = re.search(r"\d+", clean_text)
        if match:
            tid = int(match.group(0))
            updated = update_task_status(tid, "completed")
            reply = f"Task #{tid} marked as completed in persistent storage, sir." if updated else f"Task #{tid} could not be located, sir."
            save_conversation_turn("user", clean_text, intent="complete_task")
            save_conversation_turn("assistant", reply, intent="complete_task")
            return {"success": updated, "action": "complete_task", "task_id": tid, "reply": reply}

    # 5. Persistent Memories / Facts Direct Intents
    if lower.startswith("remember that") or lower.startswith("remember:") or lower.startswith("लक्षात ठेव की") or lower.startswith("लक्षात ठेवा की") or lower.startswith("याद रखो कि") or lower.startswith("याद रखना कि"):
        mem_content = re.sub(r"^(remember that:?|remember:?|लक्षात ठेव की:?|लक्षात ठेवा की:?|याद रखो कि:?|याद रखना कि:?)", "", clean_text, flags=re.IGNORECASE).strip()
        if mem_content:
            title = mem_content[:35] + ("..." if len(mem_content) > 35 else "")
            save_memory("user_observation", title, mem_content, importance=2)
            reply = f"I have permanently committed that to my core neural memory, sir: '{mem_content}'."
            save_conversation_turn("user", clean_text, intent="save_memory")
            save_conversation_turn("assistant", reply, intent="save_memory")
            return {"success": True, "action": "save_memory", "reply": reply}

    if any(k in lower for k in ["what do you remember", "recall memories", "stored memories", "माझ्याबद्दल काय आठवतं", "मेरे बारे में क्या याद है"]):
        mems = get_memories(limit=6)
        if mems:
            mem_str = "; ".join([f"{m['title']}" for m in mems])
            reply = f"Persisted memories recalled: {mem_str}, sir."
        else:
            reply = "No personal memory entries recorded yet, sir."
        save_conversation_turn("user", clean_text, intent="recall_memories")
        save_conversation_turn("assistant", reply, intent="recall_memories")
        return {"success": True, "action": "recall_memories", "reply": reply}

    # 6. Backup & Windows Auto-Start Direct Intents
    if any(k in lower for k in ["create backup", "backup data", "backup system", "डेटा बॅकअप घे", "बॅकअप कर", "सिस्टम बैकअप लो", "बैकअप बनाओ"]):
        b_res = create_backup_snapshot()
        reply = f"Full system backup snapshot created: '{b_res['backup_db']}' ({b_res['size_kb']} KB), sir."
        save_conversation_turn("user", clean_text, intent="create_backup")
        save_conversation_turn("assistant", reply, intent="create_backup")
        return {"success": True, "action": "create_backup", "backup": b_res, "reply": reply}

    if any(k in lower for k in ["enable autostart", "start with windows", "विंडोज सुरू झाल्यावर चालू कर", "ऑटोस्टार्ट चालू कर", "विंडोज के साथ चालू करो"]):
        a_res = enable_windows_autostart()
        reply = "Windows Auto-Start enabled, sir. JARVIS will now launch automatically when your PC boots." if a_res.get("status") == "ok" else f"Failed to configure auto-start: {a_res.get('message')}"
        save_conversation_turn("user", clean_text, intent="enable_autostart")
        save_conversation_turn("assistant", reply, intent="enable_autostart")
        return {"success": a_res.get("status") == "ok", "action": "enable_autostart", "reply": reply}

    if any(k in lower for k in ["disable autostart", "stop starting with windows", "ऑटोस्टार्ट बंद कर", "विंडोज ऑटोस्टार्ट बंद"]):
        a_res = disable_windows_autostart()
        reply = "Windows Auto-Start has been disabled, sir."
        save_conversation_turn("user", clean_text, intent="disable_autostart")
        save_conversation_turn("assistant", reply, intent="disable_autostart")
        return {"success": True, "action": "disable_autostart", "reply": reply}

    # 7. Biometric Identity & Voice Recognition Direct Intents
    if any(k in lower for k in [
        "who am i", "recognize me", "my identity", "who is speaking", "who is in front of camera", "do you know me",
        "माझी ओळख काय आहे", "मी कोण आहे", "माझा चेहरा ओळखलास का", "माझा आवाज ओळखलास का",
        "मैं कौन हूँ", "मेरी पहचान क्या है", "क्या मुझे पहचानते हो", "कौन बोल रहा है"
    ]):
        bio = identity_manager.get_state()
        if bio["role"] == "owner":
            reply = f"I recognize you as {bio['display_name']} (Primary Owner), sir. Biometric status: Face {'Verified' if bio['face_matched'] else 'Standby'} ({int(bio['face_confidence']*100)}%), Voice {'Verified' if bio['voice_matched'] else 'Standby'} ({int(bio['voice_confidence']*100)}%). All workstation control permissions are active."
        else:
            reply = f"You are currently recognized as a {bio['display_name']} with restricted permissions. Workstation administrative actions are reserved for Tony Stark."
        save_conversation_turn("user", clean_text, intent="biometric_identity_query")
        save_conversation_turn("assistant", reply, intent="biometric_identity_query")
        return {"success": True, "action": "biometric_identity_query", "identity": bio, "reply": reply}

    if any(k in lower for k in ["switch to guest", "guest mode", "गेस्ट मोड", "गेस्ट मोड चालू करा", "अतिथि मोड", "guest user"]):
        identity_manager.role = "guest"
        identity_manager.display_name = "Guest User"
        reply = "Switched to Guest Mode, sir. Administrative commands and sensitive system controls are now restricted."
        save_conversation_turn("user", clean_text, intent="switch_guest_mode")
        save_conversation_turn("assistant", reply, intent="switch_guest_mode")
        return {"success": True, "action": "switch_guest_mode", "reply": reply}

    if any(k in lower for k in ["switch to owner", "owner mode", "मी टोनी आहे", "ओनर मोड", "i am tony", "i am owner"]):
        identity_manager.role = "owner"
        identity_manager.display_name = "Tony Stark"
        reply = "Welcome back, Mr. Stark. Full workstation control and administrative authorization restored."
        save_conversation_turn("user", clean_text, intent="switch_owner_mode")
        save_conversation_turn("assistant", reply, intent="switch_owner_mode")
        return {"success": True, "action": "switch_owner_mode", "reply": reply}

    if any(k in lower for k in ["purge biometrics", "wipe biometric data", "delete biometrics", "बायोमेट्रिक डेटा हटवा", "बायोमेट्रिक डेटा डिलीट करा", "बायोमेट्रिक हटाओ"]):
        p_res = identity_manager.purge_data()
        reply = "All stored biometric face scans and voice signatures have been permanently erased from local storage, sir."
        save_conversation_turn("user", clean_text, intent="purge_biometrics")
        save_conversation_turn("assistant", reply, intent="purge_biometrics")
        return {"success": True, "action": "purge_biometrics", "details": p_res, "reply": reply}

    # 7.5 Direct System & Voice Acknowledgment ("acknowledge me", "standing pollution", "standing position", "standing by")
    ack_triggers = [
        "acknowledge me by standing pollution",
        "acknowledge me",
        "standing pollution",
        "standing position",
        "standing protocol",
        "standing by",
        "are you there",
        "are you listening",
        "java is not properly answering",
        "system check",
        "status check",
        "active check",
        "मला ऐकतोस का",
        "ऐकतोयस का",
        "काय करतोस",
        "सुन रहे हो",
        "क्या हाल है",
    ]
    if any(t in lower for t in ack_triggers):
        reply = "Acknowledged, sir. Standing by. All core systems, telemetry, and protocols are operating and fully active."
        save_conversation_turn("user", clean_text, intent="acknowledge")
        save_conversation_turn("assistant", reply, intent="acknowledge")
        return {
            "success": True,
            "action": "acknowledge",
            "reply": reply,
        }

    # 8. System Telemetry / Health Query Direct Match
    telemetry_triggers = [
        "system status", "system telemetry", "pc status", "cpu status", "ram status", "battery status", "hardware diagnostics",
        "हार्डवेअर कसे आहे", "सिस्टम कशी आहे", "बॅटरी किती आहे", "रॅम किती आहे",
        "सिस्टम स्टेटस", "हार्डवेयर स्टेटस", "बैटरी कितनी है", "सीपीयू यूसेज"
    ]
    if any(t in lower for t in telemetry_triggers):
        telem = get_system_telemetry()
        cpu = telem.get("cpu_percent", 0)
        ram = telem.get("ram_percent", 0)
        disk = telem.get("disk_percent", 0)
        batt = telem.get("battery")
        batt_str = f", battery at {batt['percent']}%" if batt else ""
        reply = f"Workstation diagnostics nominal: CPU at {cpu}%, RAM utilization at {ram}%, primary drive at {disk}% capacity{batt_str}, sir."
        save_conversation_turn("user", clean_text, intent="system_telemetry")
        save_conversation_turn("assistant", reply, intent="system_telemetry")
        return {
            "success": True,
            "action": "system_telemetry",
            "telemetry": telem,
            "reply": reply,
        }

    # 8. Direct Close Application Intent ("close Chrome", "कॅमेरा बंद कर", "नोटपॅड बंद करा", "chrome band karo")
    close_verbs = [
        "close", "quit", "exit", "kill", "terminate", "shut",
        "बंद कर", "बंद करा", "थांबव", "थांबवा",
        "बंद करो", "हटाओ", "काटो", "band kar", "band karo"
    ]
    if any(v in lower for v in close_verbs):
        app_candidates = ["chrome", "notepad", "calculator", "camera", "webcam", "paint", "spotify", "explorer", "terminal", "vscode", "browser", "code"]
        for cand in app_candidates:
            if cand in lower or (cand == "camera" and any(k in lower for k in ["कॅमेरा", "कैमरा"])) or (cand == "chrome" and "क्रोम" in lower) or (cand == "calculator" and any(k in lower for k in ["कॅल्क्युलेटर", "कैलकुलेटर"])) or (cand == "notepad" and any(k in lower for k in ["नोटपॅड", "नोटपैड"])):
                res = close_application(cand)
                save_conversation_turn("user", clean_text, intent="close_app")
                save_conversation_turn("assistant", res["reply"], intent="close_app")
                return {
                    "success": res["success"],
                    "action": "close_app",
                    "target": cand,
                    "reply": res["reply"],
                }

    # 9. Direct File Management Intent
    if any(k in lower for k in ["list files", "show files", "workspace files", "फाइल्स दाखव", "फाइल दाखवा", "फाइलें दिखाओ"]):
        res = manage_workspace_files("list")
        save_conversation_turn("user", clean_text, intent="list_files")
        save_conversation_turn("assistant", res["reply"], intent="list_files")
        return {
            "success": res["success"],
            "action": "manage_files",
            "file_data": res,
            "reply": res["reply"],
        }

    if lower.startswith("save note") or lower.startswith("take note") or lower.startswith("note:") or lower.startswith("एक नोट लिही") or lower.startswith("नोट लिखो"):
        content = re.sub(r"^(save note:?|take note:?|note:?|एक नोट लिही:?|नोट लिखो:?)", "", clean_text, flags=re.IGNORECASE).strip()
        res = manage_workspace_files("save_note", target=f"note_{int(time.time())}", content=content)
        save_conversation_turn("user", clean_text, intent="save_note")
        save_conversation_turn("assistant", res["reply"], intent="save_note")
        return {
            "success": res["success"],
            "action": "save_note",
            "file_data": res,
            "reply": res["reply"],
        }

    if lower.startswith("read file") or lower.startswith("read note") or lower.startswith("फाइल वाच") or lower.startswith("नोट पढ़ो"):
        target_name = re.sub(r"^(read file:?|read note:?|फाइल वाच:?|नोट पढ़ो:?)", "", clean_text, flags=re.IGNORECASE).strip()
        res = manage_workspace_files("read", target=target_name)
        save_conversation_turn("user", clean_text, intent="read_file")
        save_conversation_turn("assistant", res["reply"], intent="read_file")
        return {
            "success": res["success"],
            "action": "read_file",
            "file_data": res,
            "reply": res["reply"],
        }

    # Prepare conversation history for multi-turn contextual awareness
    hist_messages = []
    if conversation_history:
        hist_messages = conversation_history[-8:]
    elif CONVERSATION_MEMORY:
        hist_messages = CONVERSATION_MEMORY[-8:]

    # Dynamically inject persistent memories, user preferences, and active tasks into system prompt
    augmented_system_prompt = build_augmented_system_prompt()

    system_instruction = f"""{augmented_system_prompt}

You are the Task Orchestrator & Multitasking Brain of JARVIS.
Analyze the user's input (which may be in English, Marathi, Hindi, Hinglish, or mixed).
Determine if the user's request contains one or more actions (e.g. open camera, play song, search web, open app, close app, manage files), or if it is an intellectual/coding question (AI/ML/DL, algorithms, physics, coding, general chat).

Output strictly valid JSON:
{{
  "is_action": boolean,
  "actions": [
    {{
      "action_type": "open_camera" | "play_music" | "search_youtube" | "search_google" | "open_app" | "open_website" | "close_app" | "none",
      "target": "<app name, url, or target>",
      "query": "<search query or song title if applicable>"
    }}
  ],
  "reply": "<Direct, highly articulate, polite Jarvis response in the user's language matching Tony Stark's AI companion>"
}}"""

    # 9.5 TIER 0: OpenAI Responses API (`gpt-6-astra`) Orchestrator & Frontier Reasoning Brain
    global _openai_quota_cooldown_until
    if OPENAI_API_KEY and time.time() >= _openai_quota_cooldown_until:
        openai_msgs = [{"role": "system", "content": system_instruction}]
        for item in hist_messages:
            q_role = "assistant" if item.get("role") in ["model", "assistant"] else "user"
            openai_msgs.append({"role": q_role, "content": item.get("content", "")})
        openai_msgs.append({"role": "user", "content": clean_text})

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "JarvisBackend-GPT6Astra/1.0",
        }

        openai_payload = {
            "model": OPENAI_MODEL,
            "input": openai_msgs,
            "instructions": system_instruction,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(OPENAI_RESPONSES_API_URL, headers=headers, json=openai_payload)
                raw_text = None
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("output_text"):
                        raw_text = data["output_text"].strip()
                    elif "output" in data:
                        for item in data.get("output", []):
                            if item.get("type") == "message":
                                for c in item.get("content", []):
                                    if c.get("type") == "text":
                                        raw_text = c.get("text", "").strip()
                                        break
                            elif isinstance(item, dict) and "text" in item:
                                raw_text = item["text"].strip()
                                break
                    elif "choices" in data:
                        raw_text = data["choices"][0]["message"]["content"].strip()
                elif resp.status_code in [400, 401, 403, 404, 429]:
                    _openai_quota_cooldown_until = time.time() + 3600.0
                    logger.warning(f"OpenAI Responses API unavailable (HTTP {resp.status_code}). Activating cooldown; cascading directly to fast neural cores.")

                if raw_text:
                    parsed = json.loads(raw_text)
                    is_action = parsed.get("is_action", False)
                    actions_list = parsed.get("actions", [])
                    reply = parsed.get("reply", "Standing by, sir.")

                    CONVERSATION_MEMORY.append({"role": "user", "content": clean_text})
                    CONVERSATION_MEMORY.append({"role": "assistant", "content": reply})
                    if len(CONVERSATION_MEMORY) > MAX_MEMORY_TURNS:
                        CONVERSATION_MEMORY = CONVERSATION_MEMORY[-MAX_MEMORY_TURNS:]

                    save_conversation_turn("user", clean_text)
                    save_conversation_turn("assistant", reply, metadata={"is_action": is_action, "actions": actions_list})

                    if is_action and actions_list:
                        return execute_system_actions(actions_list, reply)

                    return {
                        "success": False,
                        "reply": reply,
                        "provider": f"openai-responses ({OPENAI_MODEL})",
                    }
        except Exception as e:
            logger.warning(f"OpenAI Responses API notice: {e}, falling back to Gemini...")

    # 10. TIER 1: Gemini Semantic Multi-Task & AI/ML Reasoning Parser
    if GEMINI_API_KEY:
        history_payload = []
        for item in hist_messages:
            g_role = "user" if item.get("role") == "user" else "model"
            history_payload.append({"role": g_role, "parts": [{"text": item.get("content", "")}]})
        history_payload.append({"role": "user", "parts": [{"text": clean_text}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": history_payload,
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 350,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(
                    f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(raw_text)
                    
                    is_action = parsed.get("is_action", False)
                    actions_list = parsed.get("actions", [])
                    reply = parsed.get("reply", "Standing by, sir.")

                    # Update internal conversation memory & persistent DB
                    CONVERSATION_MEMORY.append({"role": "user", "content": clean_text})
                    CONVERSATION_MEMORY.append({"role": "assistant", "content": reply})
                    if len(CONVERSATION_MEMORY) > MAX_MEMORY_TURNS:
                        CONVERSATION_MEMORY = CONVERSATION_MEMORY[-MAX_MEMORY_TURNS:]

                    save_conversation_turn("user", clean_text)
                    save_conversation_turn("assistant", reply, metadata={"is_action": is_action, "actions": actions_list})

                    if is_action and actions_list:
                        return execute_system_actions(actions_list, reply)

                    # Pure conversational / AI / ML / DL response
                    return {
                        "success": False,
                        "reply": reply,
                        "provider": "gemini",
                    }
                else:
                    logger.warning(f"Gemini multi-task status {resp.status_code}, falling back to Groq...")
        except Exception as e:
            logger.warning(f"Gemini multi-task brain error: {e}, falling back to Groq...")

    # 11. TIER 2: Groq (Qwen 3.8 27B / GPT-OSS 120B) Structured Agent Brain
    if GROQ_API_KEY:
        groq_msgs = [{"role": "system", "content": system_instruction}]
        for item in hist_messages:
            q_role = "assistant" if item.get("role") in ["model", "assistant"] else "user"
            groq_msgs.append({"role": q_role, "content": item.get("content", "")})
        groq_msgs.append({"role": "user", "content": clean_text})

        groq_payload = {
            "model": GROQ_MODEL,
            "messages": groq_msgs,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 350,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json=groq_payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["choices"][0]["message"]["content"].strip()
                    parsed = json.loads(raw_text)

                    is_action = parsed.get("is_action", False)
                    actions_list = parsed.get("actions", [])
                    reply = parsed.get("reply", "Standing by, sir.")

                    # Update memory & persistent DB
                    CONVERSATION_MEMORY.append({"role": "user", "content": clean_text})
                    CONVERSATION_MEMORY.append({"role": "assistant", "content": reply})
                    if len(CONVERSATION_MEMORY) > MAX_MEMORY_TURNS:
                        CONVERSATION_MEMORY = CONVERSATION_MEMORY[-MAX_MEMORY_TURNS:]

                    save_conversation_turn("user", clean_text)
                    save_conversation_turn("assistant", reply, metadata={"is_action": is_action, "actions": actions_list})

                    if is_action and actions_list:
                        return execute_system_actions(actions_list, reply)

                    return {
                        "success": False,
                        "reply": reply,
                        "provider": "groq",
                    }
                else:
                    logger.warning(f"Groq agent status {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            logger.warning(f"Groq agent brain error: {e}")

    # 12. TIER 3: Local Zero-Latency Multilingual Rule Matcher Fallback
    from app.system_controller import resolve_natural_intent
    local_res = await resolve_natural_intent(clean_text)
    save_conversation_turn("user", clean_text)
    save_conversation_turn("assistant", local_res.get("reply", "Standing by, sir."))
    return local_res
