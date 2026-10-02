import os
import sys
import json
import time
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("jarvis.memory")

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent  # D:\New folder (4)\jarvis
WORKSPACE_ROOT = PROJECT_ROOT.parent  # D:\New folder (4)
FRONTEND_DIR = PROJECT_ROOT / "frontend"

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "jarvis_persistent.db"

# Windows Startup folder
STARTUP_DIR = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
AUTOSTART_VBS_PATH = STARTUP_DIR / "JARVIS_AutoStart.vbs"


def get_db_connection() -> sqlite3.Connection:
    """Return a thread-safe connection to SQLite with WAL mode enabled for crash resilience."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_database():
    """Initialize persistent schema if not already present."""
    with get_db_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT DEFAULT 'general',
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            due_date TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at DATETIME,
            last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
            summary TEXT DEFAULT '',
            clean_exit INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS biometric_profiles (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            face_embedding TEXT DEFAULT NULL,
            voice_embedding TEXT DEFAULT NULL,
            permissions TEXT NOT NULL DEFAULT '["chat", "search"]',
            consent_given INTEGER DEFAULT 0,
            enrolled_at DATETIME DEFAULT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS coding_sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            active_file TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS coding_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT DEFAULT '[]',
            tool_results TEXT DEFAULT '[]',
            thoughts TEXT DEFAULT '',
            diffs TEXT DEFAULT '[]',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS file_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            original_hash TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_mem_category ON agent_memories(category);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_coding_session ON coding_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_backup_file ON file_backups(file_path);
        """)
        conn.commit()

        defaults = {
            "user_name": "Sir",
            "speech_language": "en-IN",
            "voice_engine": "pocket-tts",
            "theme": "dark-obsidian",
            "panel_position": "docked-tr",
            "auto_chirp": True,
            "first_boot": False,
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO user_preferences (key, value) VALUES (?, ?)",
                (k, json.dumps(v))
            )
        conn.commit()


# =========================================================================
# 1. CONVERSATIONS & CHAT HISTORY
# =========================================================================

def save_conversation_turn(role: str, content: str, session_id: str = "default", intent: str = "", metadata: dict | None = None) -> int:
    """Permanently store a conversation turn."""
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (session_id, role, content, intent, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, intent, meta_json)
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_conversations(limit: int = 40, session_id: str = "default") -> list[dict]:
    """Retrieve chronologically ordered recent conversations."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, session_id, role, content, intent, metadata, timestamp 
               FROM conversations 
               ORDER BY id DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        
        results = []
        for r in reversed(rows):
            results.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "intent": r["intent"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "timestamp": r["timestamp"],
            })
        return results


def clear_conversation_history() -> int:
    """Clear conversation history while preserving core agent memories and preferences."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM conversations")
        conn.commit()
        return cursor.rowcount


# =========================================================================
# 2. USER PREFERENCES & CONFIGURATION
# =========================================================================

def get_preference(key: str, default=None):
    """Retrieve a persisted user preference."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,)).fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except Exception:
                return row["value"]
        return default


def set_preference(key: str, value) -> None:
    """Persist a user preference."""
    serialized = json.dumps(value, ensure_ascii=False)
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO user_preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
            (key, serialized)
        )
        conn.commit()


def get_all_preferences() -> dict:
    """Retrieve all user preferences as a dictionary."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
        result = {}
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value"])
            except Exception:
                result[r["key"]] = r["value"]
        return result


# =========================================================================
# 3. SEMANTIC AGENT MEMORIES & FACT STORE
# =========================================================================

def save_memory(category: str, title: str, content: str, importance: int = 1) -> int:
    """Store a durable memory, fact, or user observation."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO agent_memories (category, title, content, importance) VALUES (?, ?, ?, ?)",
            (category, title, content, importance)
        )
        conn.commit()
        return cursor.lastrowid

add_memory = save_memory


def get_memories(category: str | None = None, limit: int = 50) -> list[dict]:
    """Retrieve stored agent memories."""
    with get_db_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT id, category, title, content, importance, created_at, updated_at FROM agent_memories WHERE category = ? ORDER BY importance DESC, id DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, category, title, content, importance, created_at, updated_at FROM agent_memories ORDER BY importance DESC, id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
        return [dict(r) for r in rows]


def delete_memory(memory_id: int) -> bool:
    """Delete a memory item by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM agent_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0


# =========================================================================
# 4. TASK & TODO PERSISTENCE
# =========================================================================

def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> dict:
    """Add a new task to persistent memory."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, description, status, priority, due_date) VALUES (?, ?, 'pending', ?, ?)",
            (title, description, priority, due_date)
        )
        conn.commit()
        task_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row)


def list_tasks(status: str | None = None) -> list[dict]:
    """List tasks, optionally filtered by status."""
    with get_db_connection() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END, id DESC").fetchall()
        return [dict(r) for r in rows]


def update_task_status(task_id: int, status: str) -> bool:
    """Update task status (pending, in_progress, completed, cancelled)."""
    completed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") if status == "completed" else None
    with get_db_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, task_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_task(task_id: int) -> bool:
    """Permanently delete a task."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0


# =========================================================================
# 5. SESSION LIFECYCLE & CRASH RECOVERY
# =========================================================================

_CURRENT_SESSION_ID: int | None = None

def start_session() -> int:
    """Record startup session and check for previous unclean exits."""
    global _CURRENT_SESSION_ID
    init_database()
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (started_at, last_heartbeat) VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )
        conn.commit()
        _CURRENT_SESSION_ID = cursor.lastrowid
        return _CURRENT_SESSION_ID


def update_session_heartbeat():
    """Update session heartbeat timestamp."""
    global _CURRENT_SESSION_ID
    if not _CURRENT_SESSION_ID:
        return
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE sessions SET last_heartbeat = CURRENT_TIMESTAMP WHERE id = ?",
                (_CURRENT_SESSION_ID,)
            )
            conn.commit()
    except Exception as e:
        logger.debug(f"Heartbeat update notice: {e}")


def close_session(summary: str = "Clean shutdown"):
    """Record graceful session shutdown."""
    global _CURRENT_SESSION_ID
    if not _CURRENT_SESSION_ID:
        return
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = CURRENT_TIMESTAMP, summary = ?, clean_exit = 1 WHERE id = ?",
                (summary, _CURRENT_SESSION_ID)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Session close notice: {e}")


def get_last_session_info() -> dict:
    """Retrieve metadata about the previous session."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT 1 OFFSET 1"
        ).fetchone()
        if row:
            return dict(row)
        # Fallback to current session
        current = conn.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        return dict(current) if current else {}


# =========================================================================
# 6. ATOMIC BACKUP & RELIABLE RECOVERY
# =========================================================================

def create_backup_snapshot(description: str = "") -> dict:
    """Create an atomic SQLite online backup and a JSON human-readable snapshot."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_db_name = f"jarvis_backup_{timestamp_str}.db"
    backup_json_name = f"jarvis_backup_{timestamp_str}.json"
    
    backup_db_path = BACKUPS_DIR / backup_db_name
    backup_json_path = BACKUPS_DIR / backup_json_name

    # 1. Atomic SQLite Online Backup
    with get_db_connection() as src_conn:
        dest_conn = sqlite3.connect(str(backup_db_path))
        src_conn.backup(dest_conn)
        dest_conn.close()

    # 2. JSON Full Export
    data_dump = {
        "timestamp": timestamp_str,
        "description": description,
        "preferences": get_all_preferences(),
        "memories": get_memories(limit=500),
        "tasks": list_tasks(),
        "recent_conversations": get_recent_conversations(limit=200),
    }
    backup_json_path.write_text(json.dumps(data_dump, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Clean up older backups (keep latest 10)
    rotate_backups(keep=10)

    size_kb = round(backup_db_path.stat().st_size / 1024, 1)
    logger.info(f"Created persistent backup: {backup_db_name} ({size_kb} KB)")

    return {
        "status": "ok",
        "backup_db": backup_db_name,
        "backup_json": backup_json_name,
        "size_kb": size_kb,
        "timestamp": timestamp_str,
    }

create_backup = create_backup_snapshot


def rotate_backups(keep: int = 10):
    """Keep only the newest N backups, prune older ones."""
    db_files = sorted(BACKUPS_DIR.glob("jarvis_backup_*.db"), key=os.path.getmtime)
    if len(db_files) > keep:
        for old in db_files[:-keep]:
            try:
                old.unlink(missing_ok=True)
                json_counterpart = old.with_suffix(".json")
                json_counterpart.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Error rotating old backup {old}: {e}")


def list_backups() -> list[dict]:
    """List available backups ordered from newest to oldest."""
    backups = []
    for f in sorted(BACKUPS_DIR.glob("jarvis_backup_*.db"), key=os.path.getmtime, reverse=True):
        stat = f.stat()
        json_file = f.with_suffix(".json")
        backups.append({
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "has_json": json_file.exists(),
        })
    return backups


def restore_backup(filename: str) -> dict:
    """Safely restore database from a specified backup file with pre-restore safety copy."""
    target_backup = BACKUPS_DIR / filename
    if not target_backup.exists() or not filename.endswith(".db"):
        return {"status": "error", "message": f"Backup file {filename} not found"}

    try:
        # 1. Create a pre-restore safety copy of current DB
        safety_path = DATA_DIR / f"pre_restore_safety_{int(time.time())}.db"
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, safety_path)

        # 2. Restore from backup
        dest_conn = sqlite3.connect(str(DB_PATH))
        src_conn = sqlite3.connect(str(target_backup))
        src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()

        # 3. Verify integrity
        with get_db_connection() as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            if integrity != "ok":
                # Rollback
                shutil.copy2(safety_path, DB_PATH)
                return {"status": "error", "message": f"Integrity check failed: {integrity}. Rolled back."}

        logger.info(f"Successfully restored persistent memory from {filename}")
        return {"status": "ok", "restored_file": filename, "safety_copy": safety_path.name}

    except Exception as e:
        logger.error(f"Restore error: {e}")
        return {"status": "error", "message": str(e)}


def verify_and_repair_database() -> bool:
    """Verify SQLite database integrity on startup; auto-recover from latest backup if corrupted."""
    if not DB_PATH.exists():
        init_database()
        return True

    try:
        with get_db_connection() as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            if integrity == "ok":
                return True
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")

    # Corruption detected — attempt auto-recovery
    backups = list_backups()
    if backups:
        newest = backups[0]["filename"]
        logger.warning(f"Corrupted database detected. Auto-recovering from {newest}...")
        res = restore_backup(newest)
        return res.get("status") == "ok"
    else:
        logger.error("No backups available for auto-recovery. Initializing clean database.")
        init_database()
        return False


# =========================================================================
# 7. SAFE WINDOWS AUTO-START MANAGEMENT
# =========================================================================

def get_launch_scripts_paths() -> tuple[Path, Path]:
    """Paths for start_jarvis.bat in project root and silent VBS in Windows Startup."""
    bat_path = PROJECT_ROOT / "start_jarvis.bat"
    return bat_path, AUTOSTART_VBS_PATH


def is_windows_autostart_enabled() -> bool:
    """Check if JARVIS auto-start launcher is present in the Windows Startup folder."""
    return AUTOSTART_VBS_PATH.exists()


def enable_windows_autostart() -> dict:
    """Safely configure Windows Auto-Start without modifying sensitive registry keys."""
    try:
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)
        bat_path, vbs_path = get_launch_scripts_paths()

        # 1. Create start_jarvis.bat in project root and workspace root
        ps_script = PROJECT_ROOT / "start_jarvis.ps1"
        bat_content = """@echo off
title JARVIS System Launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_jarvis.ps1"
"""
        bat_path.write_text(bat_content, encoding="utf-8")
        # Also mirror to WORKSPACE_ROOT for user convenience
        (WORKSPACE_ROOT / "start_jarvis.bat").write_text(bat_content, encoding="utf-8")

        # 2. Create invisible VBS launcher in Startup folder
        # Runs start_jarvis.ps1 with -Background in 0 (hidden window) mode
        escaped_ps = str(ps_script).replace('"', '""')
        vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""{escaped_ps}"" -Background", 0, False
Set WshShell = Nothing
"""
        vbs_path.write_text(vbs_content, encoding="utf-8")

        set_preference("windows_autostart", True)
        logger.info(f"Windows Auto-Start enabled: {vbs_path}")
        return {
            "status": "ok",
            "autostart_enabled": True,
            "startup_file": str(vbs_path),
            "batch_launcher": str(bat_path),
        }
    except Exception as e:
        logger.error(f"Failed to enable auto-start: {e}")
        return {"status": "error", "message": str(e)}


def disable_windows_autostart() -> dict:
    """Safely remove JARVIS auto-start launcher from Windows Startup folder."""
    try:
        if AUTOSTART_VBS_PATH.exists():
            AUTOSTART_VBS_PATH.unlink()
        set_preference("windows_autostart", False)
        logger.info("Windows Auto-Start disabled.")
        return {"status": "ok", "autostart_enabled": False}
    except Exception as e:
        logger.error(f"Failed to disable auto-start: {e}")
        return {"status": "error", "message": str(e)}


# =========================================================================
# 8. PRIVACY-PRESERVING BIOMETRIC EMBEDDINGS STORE
# =========================================================================

def set_biometric_consent(user_id: str = "owner", consent: bool = True) -> None:
    """Record explicit user consent for biometric processing."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO biometric_profiles (user_id, display_name, role, consent_given, updated_at)
            VALUES (?, 'Tony Stark', 'owner', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET consent_given = excluded.consent_given, updated_at = CURRENT_TIMESTAMP
        """, (user_id, 1 if consent else 0))
        conn.commit()


def get_biometric_consent(user_id: str = "owner") -> bool:
    """Check if the user has given explicit consent for biometric processing."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT consent_given FROM biometric_profiles WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row["consent_given"]) if row else False


def save_face_embedding(
    user_id: str,
    display_name: str,
    embedding: list[float],
    role: str = "owner",
    permissions: list[str] | None = None
) -> bool:
    """Securely store normalized face embedding vector (NO raw images saved on disk)."""
    if not permissions:
        permissions = ["system_actions", "shutdown", "file_ops", "multitask", "settings"] if role == "owner" else ["chat", "search"]
    
    emb_json = json.dumps(embedding)
    perm_json = json.dumps(permissions)
    
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO biometric_profiles (user_id, display_name, role, face_embedding, permissions, consent_given, enrolled_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                face_embedding = excluded.face_embedding,
                permissions = excluded.permissions,
                consent_given = 1,
                enrolled_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, display_name, role, emb_json, perm_json))
        conn.commit()
    logger.info(f"Face embedding enrolled for '{display_name}' ({user_id})")
    return True


def save_voice_embedding(
    user_id: str,
    display_name: str,
    embedding: list[float],
    role: str = "owner",
    permissions: list[str] | None = None
) -> bool:
    """Securely store acoustic speaker signature vector (NO raw audio saved on disk)."""
    if not permissions:
        permissions = ["system_actions", "shutdown", "file_ops", "multitask", "settings"] if role == "owner" else ["chat", "search"]

    emb_json = json.dumps(embedding)
    perm_json = json.dumps(permissions)

    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO biometric_profiles (user_id, display_name, role, voice_embedding, permissions, consent_given, enrolled_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                voice_embedding = excluded.voice_embedding,
                permissions = excluded.permissions,
                consent_given = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, display_name, role, emb_json, perm_json))
        conn.commit()
    logger.info(f"Voice embedding enrolled for '{display_name}' ({user_id})")
    return True


def get_biometric_profile(user_id: str) -> dict | None:
    """Retrieve biometric profile with deserialized embeddings."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM biometric_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["face_embedding"] = json.loads(d["face_embedding"]) if d.get("face_embedding") else None
        d["voice_embedding"] = json.loads(d["voice_embedding"]) if d.get("voice_embedding") else None
        d["permissions"] = json.loads(d["permissions"]) if d.get("permissions") else ["chat"]
        d["consent_given"] = bool(d["consent_given"])
        return d


def get_all_biometric_profiles() -> list[dict]:
    """Retrieve all enrolled biometric profiles."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM biometric_profiles").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["face_embedding"] = json.loads(d["face_embedding"]) if d.get("face_embedding") else None
            d["voice_embedding"] = json.loads(d["voice_embedding"]) if d.get("voice_embedding") else None
            d["permissions"] = json.loads(d["permissions"]) if d.get("permissions") else ["chat"]
            d["consent_given"] = bool(d["consent_given"])
            result.append(d)
        return result


def delete_biometric_profile(user_id: str) -> bool:
    """Delete a specific biometric user profile."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM biometric_profiles WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def purge_all_biometrics() -> dict:
    """Instantly purge all stored face/voice embeddings and reset biometric database."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM biometric_profiles")
        conn.commit()
    logger.warning("All biometric data purged by user command.")
    return {"status": "ok", "deleted_profiles": cursor.rowcount, "message": "All biometric data purged."}


# =========================================================================
# 9. CODING ASSISTANT PERSISTENCE & SAFE BACKUPS
# =========================================================================

def create_or_get_coding_session(session_id: str, title: str = "New Coding Task", active_file: str = "") -> dict:
    """Create a new coding session or return existing one."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM coding_sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            if active_file and row["active_file"] != active_file:
                conn.execute(
                    "UPDATE coding_sessions SET active_file = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (active_file, session_id),
                )
                conn.commit()
            return dict(row)

        conn.execute(
            "INSERT INTO coding_sessions (id, title, active_file) VALUES (?, ?, ?)",
            (session_id, title, active_file),
        )
        conn.commit()
        return {
            "id": session_id,
            "title": title,
            "active_file": active_file,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }


def list_coding_sessions(limit: int = 30) -> list[dict]:
    """List recent coding sessions ordered by last update."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM coding_sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_coding_session(session_id: str) -> dict | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM coding_sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def save_coding_message(
    session_id: str,
    role: str,
    content: str,
    tool_calls: list | None = None,
    tool_results: list | None = None,
    thoughts: str = "",
    diffs: list | None = None,
) -> int:
    """Save an exchange in a coding thread."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO coding_messages
               (session_id, role, content, tool_calls, tool_results, thoughts, diffs)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                role,
                content,
                json.dumps(tool_calls or [], ensure_ascii=False),
                json.dumps(tool_results or [], ensure_ascii=False),
                thoughts,
                json.dumps(diffs or [], ensure_ascii=False),
            ),
        )
        conn.execute("UPDATE coding_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.lastrowid


def get_coding_messages(session_id: str, limit: int = 50) -> list[dict]:
    """Retrieve ordered chat messages for a coding session."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM coding_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        messages = []
        for r in rows:
            d = dict(r)
            d["tool_calls"] = json.loads(d["tool_calls"]) if d.get("tool_calls") else []
            d["tool_results"] = json.loads(d["tool_results"]) if d.get("tool_results") else []
            d["diffs"] = json.loads(d["diffs"]) if d.get("diffs") else []
            messages.append(d)
        return messages


def record_file_backup(file_path: str, backup_path: str, description: str = "") -> int:
    """Log a created file backup before code modification."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO file_backups (file_path, backup_path, description) VALUES (?, ?, ?)",
            (str(file_path), str(backup_path), description),
        )
        conn.commit()
        return cursor.lastrowid


def get_file_backups(file_path: str | None = None, limit: int = 20) -> list[dict]:
    """Query recent backups, optionally filtered by original file path."""
    with get_db_connection() as conn:
        if file_path:
            rows = conn.execute(
                "SELECT * FROM file_backups WHERE file_path = ? ORDER BY id DESC LIMIT ?",
                (str(file_path), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM file_backups ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def restore_latest_backup(file_path: str) -> dict:
    """Safely restore a file to its most recent pre-modification backup."""
    target_path = Path(file_path).resolve()
    backups = get_file_backups(str(target_path), limit=1)
    if not backups:
        # Also try matching relative or basename
        backups = get_file_backups(limit=50)
        backups = [b for b in backups if Path(b["file_path"]).name == target_path.name]
        if not backups:
            return {"success": False, "error": f"No backup found for {file_path}"}

    latest = backups[0]
    backup_file = Path(latest["backup_path"])
    if not backup_file.exists():
        return {"success": False, "error": f"Backup file {backup_file} no longer exists"}

    try:
        shutil.copy2(backup_file, target_path)
        logger.info(f"Restored {target_path} from backup {backup_file}")
        return {
            "success": True,
            "restored_file": str(target_path),
            "restored_from": str(backup_file),
            "backup_time": latest["created_at"],
        }
    except Exception as e:
        return {"success": False, "error": f"Restore failed: {e}"}


