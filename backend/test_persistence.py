import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.persistent_memory import (
    init_database, set_preference, get_preference, add_memory, get_memories,
    create_task, list_tasks, update_task_status, save_conversation_turn,
    get_recent_conversations, create_backup, list_backups, verify_and_repair_database,
    enable_windows_autostart, is_windows_autostart_enabled, disable_windows_autostart,
    get_launch_scripts_paths
)
from app.main import app
from fastapi.testclient import TestClient

def main():
    print("--- 1. Testing Core Persistence (SQLite WAL) ---")
    init_database()
    set_preference('user_name', 'Tony Stark')
    set_preference('preferred_language', 'en-IN')
    assert get_preference('user_name') == 'Tony Stark'
    assert get_preference('preferred_language') == 'en-IN'
    print("[OK] User preferences stored & retrieved successfully")

    mem_id = add_memory(category='profile', title='Tech Stack', content='User prefers Python, PyTorch, and Next.js for ML development', importance=5)
    assert mem_id > 0
    mems = get_memories()
    assert any(m['title'] == 'Tech Stack' for m in mems)
    print(f"[OK] Memory record saved & retrieved: {len(mems)} memories in store")

    task = create_task('Deploy Quantum Telemetry Engine', priority='high')
    assert task['id'] > 0
    assert update_task_status(task['id'], 'in_progress')
    tasks = list_tasks()
    assert any(t['id'] == task['id'] and t['status'] == 'in_progress' for t in tasks)
    print(f"[OK] Task workflow validated: {len(tasks)} tasks in store")

    save_conversation_turn('user', 'JARVIS, calibrate thrusters.', intent='automation')
    save_conversation_turn('assistant', 'Thrusters calibrated to 100% capacity, sir.')
    convs = get_recent_conversations(limit=5)
    assert len(convs) >= 2
    assert convs[-1]['content'] == 'Thrusters calibrated to 100% capacity, sir.'
    print(f"[OK] Conversation turns persisted: last message '{convs[-1]['content']}'")

    print("\n--- 2. Testing Atomic Backups & JSON Snapshots ---")
    bk = create_backup('Test snapshot')
    assert bk['status'] == 'ok'
    backups = list_backups()
    assert len(backups) > 0
    print(f"[OK] Atomic SQLite backup created: {backups[0]['filename']} ({backups[0]['size_kb']} KB)")

    print("\n--- 3. Testing Database Integrity & Auto-Repair ---")
    ok = verify_and_repair_database()
    assert ok is True
    print("[OK] SQLite PRAGMA integrity_check verified: 100% OK")

    print("\n--- 4. Testing Safe Windows Auto-Start ---")
    res = enable_windows_autostart()
    assert res['status'] == 'ok'
    assert is_windows_autostart_enabled() is True
    bat_path, vbs_path = get_launch_scripts_paths()
    assert bat_path.exists()
    assert vbs_path.exists()
    print("[OK] Windows Auto-Start launcher active at:", vbs_path)
    print("[OK] Master system launcher batch script active at:", bat_path)

    print("\n--- 5. Testing REST API Endpoints ---")
    client = TestClient(app)
    resp = client.get('/api/memory/state')
    assert resp.status_code == 200
    data = resp.json()
    assert 'tasks' in data and 'memories' in data and 'recent_conversations' in data
    assert data['autostart_enabled'] is True
    print(f"[OK] GET /api/memory/state: returned {len(data['tasks'])} tasks, {len(data['memories'])} memories, {len(data['recent_conversations'])} turns")

    resp = client.get('/api/memory/tasks')
    assert resp.status_code == 200
    print(f"[OK] GET /api/memory/tasks: {len(resp.json())} tasks returned")

    resp = client.get('/api/memory/backups')
    assert resp.status_code == 200
    print(f"[OK] GET /api/memory/backups: {len(resp.json())} backups tracked")

    resp = client.get('/api/system/autostart')
    assert resp.status_code == 200
    assert resp.json()['autostart_enabled'] is True
    print(f"[OK] GET /api/system/autostart: verified enabled")

    print("\n--- 6. Testing Biometric Security, Face & Voice Recognition ---")
    from app.biometric_engine import (
        detect_faces, compute_face_embedding, compute_voice_embedding,
        identity_manager
    )
    import numpy as np

    # A. Face embedding math
    fake_face = np.full((128, 128, 3), 128, dtype=np.uint8)
    f_emb = compute_face_embedding(fake_face)
    assert len(f_emb) == 128
    assert 0.99 <= np.linalg.norm(f_emb) <= 1.01
    print(f"[OK] Face embedding math: 128-D normalized vector, norm {np.linalg.norm(f_emb):.4f}")

    # B. Voice acoustic signature math
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    voice_sig = 0.5 * np.sin(2 * np.pi * 320 * t)
    v_emb = compute_voice_embedding(voice_sig, sample_rate=sr)
    assert v_emb is not None and len(v_emb) == 128
    print(f"[OK] Voice acoustic signature: 128-D normalized vector")

    # C. REST Biometrics Status & Consent
    b_status = client.get('/api/biometrics/status')
    assert b_status.status_code == 200
    assert 'role' in b_status.json()

    c_post = client.post('/api/biometrics/consent', json={'user_id': 'owner', 'consent': True})
    assert c_post.status_code == 200
    assert c_post.json()['consent_given'] is True
    print(f"[OK] Explicit biometric consent granted & persisted")

    # D. Role switching and permission gate
    client.post('/api/biometrics/user/switch', json={'role': 'guest', 'display_name': 'Unknown Guest'})
    guest_chat = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'JARVIS, shutdown PC'}]})
    assert guest_chat.status_code == 200
    assert 'Access denied' in guest_chat.json()['reply'] or 'restricted' in guest_chat.json()['reply'].lower()
    print("[OK] Guest permission gate: Workstation shutdown blocked for unauthorized guest")

    # Switch back to owner
    client.post('/api/biometrics/user/switch', json={'role': 'owner', 'display_name': 'Tony Stark'})
    owner_chat = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'JARVIS, shutdown PC'}]})
    assert owner_chat.status_code == 200
    assert owner_chat.json().get('requires_confirmation') is True
    print("[OK] Owner permission gate: Safety confirmation gate triggered for Tony Stark")

    print("\n=========================================================================")
    print("SUCCESS: ALL PERSISTENCE, BACKUP, AUTOSTART, FACE & VOICE TESTS PASSED!")
    print("=========================================================================")

if __name__ == '__main__':
    main()

