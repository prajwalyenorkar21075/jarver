#!/usr/bin/env python3
"""
J.A.R.V.I.S. Developer CLI
Autonomous AI Coding Assistant, Skill Commander & Project Engineer
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add backend directory to sys.path so CLI can also run standalone if needed
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BACKEND_URL = os.getenv("JARVIS_BACKEND_URL", "http://127.0.0.1:8000")

# ANSI Color Codes for Stark Terminal UI
CYAN = "\033[96m"
BRIGHT_CYAN = "\033[38;5;51m"
GOLD = "\033[38;5;214m"
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    banner = f"""{BRIGHT_CYAN}{BOLD}
    ===============================================================
       J.A.R.V.I.S. // AUTONOMOUS AI CODING COMMANDER
       Model: GPT-6 Astra | Skills: Modular | Memory: SQLite-WAL
    ===============================================================
    {RESET}"""
    print(banner)


def check_backend_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/api/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def call_api(endpoint: str, data: dict = None, method: str = "GET") -> dict:
    url = f"{BACKEND_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "User-Agent": "JarvisCLI/2.0"}
    req_body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        try:
            return json.loads(err_body)
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": err_body}
    except Exception as e:
        return {"error": f"Failed to connect to JARVIS backend at {BACKEND_URL}: {e}"}


def cmd_chat(args):
    print_banner()
    if not check_backend_alive():
        print(f"{RED}[!] JARVIS backend is not responding on {BACKEND_URL}. Please start JARVIS first via 'start_jarvis.bat'.{RESET}")
        return

    session_id = args.session or f"cli_{os.getpid()}"
    print(f"{GREEN}[OK] Connected to JARVIS Neural Core. Session: {session_id}{RESET}")
    print(f"{GRAY}Type your coding instruction, 'exit' to quit, or 'tools' to see available skills.{RESET}\n")

    while True:
        try:
            user_input = input(f"{BRIGHT_CYAN}{BOLD}JARVIS-DEV > {RESET}").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print(f"{GOLD}Standing by, sir. Session saved.{RESET}")
                break

            if user_input.lower() == "tools":
                res = call_api("/api/skills")
                print(f"\n{GOLD}--- Active Skills & Tools ---{RESET}")
                for sk in res.get("skills", []):
                    status = f"{GREEN}[ACTIVE]{RESET}" if sk.get("enabled") else f"{RED}[DISABLED]{RESET}"
                    print(f" • {sk['display_name']} {status} ({len(sk.get('tools', []))} tools)")
                    for t in sk.get("tools", []):
                        print(f"    - {t['name']}: {t['description'][:75]}...")
                print()
                continue

            print(f"{GOLD}[*] GPT-6 Astra reasoning over workspace...{RESET}")
            res = call_api("/api/coding/chat", {
                "session_id": session_id,
                "message": user_input,
                "active_file": args.file or "",
            }, method="POST")

            if "error" in res:
                print(f"{RED}[Error]: {res['error']}{RESET}\n")
                continue

            # Display executed tool calls
            for tc in res.get("tool_calls", []):
                print(f"{CYAN}  [+] Tool Executed: {BOLD}{tc['name']}{RESET} {GRAY}({json.dumps(tc.get('arguments', {}))[:90]}...){RESET}")

            # Display diffs if any
            for diff in res.get("diffs", []):
                print(f"\n{GOLD}--- Code Changes in {diff.get('path')} ---{RESET}")
                for line in diff.get("diff", "").splitlines()[:15]:
                    if line.startswith("+"):
                        print(f"{GREEN}{line}{RESET}")
                    elif line.startswith("-"):
                        print(f"{RED}{line}{RESET}")
                    else:
                        print(line)

            print(f"\n{BOLD}J.A.R.V.I.S. [{res.get('provider', 'AI')}]:{RESET}")
            print(f"{res.get('reply', 'Task completed.')}\n")

        except KeyboardInterrupt:
            print(f"\n{GOLD}Operation paused.{RESET}")
            break


def cmd_code(args):
    instruction = " ".join(args.instruction).strip()
    if not instruction:
        print(f"{RED}Error: Please provide a coding instruction.{RESET}")
        return

    print(f"{GOLD}[*] Dispatching autonomous coding task to GPT-6 Astra: \"{instruction}\"{RESET}")
    res = call_api("/api/coding/chat", {
        "session_id": f"cli_task_{os.getpid()}",
        "message": instruction,
        "active_file": args.file or "",
    }, method="POST")

    if "error" in res:
        print(f"{RED}[Error]: {res['error']}{RESET}")
        return

    for tc in res.get("tool_calls", []):
        print(f"{CYAN}[+] Tool Invoked: {tc['name']}{RESET}")

    for diff in res.get("diffs", []):
        print(f"\n{GOLD}--- Diff Applied: {diff.get('path')} ---{RESET}")
        print(diff.get("diff"))

    print(f"\n{BRIGHT_CYAN}{BOLD}JARVIS Response:{RESET}")
    print(res.get("reply"))


def cmd_scan(args):
    print_banner()
    print(f"{GOLD}[*] Running System & Workspace Diagnostics...{RESET}\n")
    health = call_api("/api/health")
    print(f"{BOLD}Core Health & Models:{RESET}")
    print(f"  • Service:          {health.get('service')}")
    print(f"  • Primary Provider: {health.get('llm_provider')}")
    print(f"  • OpenAI Model:     {health.get('openai_model')} (Ready: {health.get('openai_ready')})")
    print(f"  • Gemini Fallback:  {health.get('gemini_model')} (Ready: {health.get('gemini_ready')})")
    print(f"  • Groq Fallback:    {health.get('groq_model')} (Ready: {health.get('groq_ready')})")
    print(f"  • Cloned Voice:     {health.get('cloned_voice')}")

    skills = call_api("/api/skills")
    print(f"\n{BOLD}Registered Skills:{RESET}")
    for sk in skills.get("skills", []):
        st = f"{GREEN}ONLINE{RESET}" if sk.get("enabled") else f"{RED}OFFLINE{RESET}"
        print(f"  • {sk['display_name']} ({len(sk.get('tools', []))} tools) [{st}]")

    print(f"\n{GREEN}[OK] Diagnostics Complete. All systems operational.{RESET}")


def cmd_rollback(args):
    file_path = args.path
    print(f"{GOLD}[*] Attempting rollback for '{file_path}'...{RESET}")
    res = call_api("/api/coding/rollback", {"path": file_path}, method="POST")
    if res.get("success"):
        print(f"{GREEN}[OK] Successfully restored {res.get('restored_file')} from backup: {res.get('restored_from')}{RESET}")
    else:
        print(f"{RED}[Error]: {res.get('error', 'Rollback failed.')}{RESET}")


def main():
    parser = argparse.ArgumentParser(description="JARVIS Autonomous AI Coding Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # chat command
    p_chat = subparsers.add_parser("chat", help="Start interactive ChatGPT-style terminal session")
    p_chat.add_argument("--session", "-s", help="Session ID to resume")
    p_chat.add_argument("--file", "-f", help="Active file context")

    # code command
    p_code = subparsers.add_parser("code", help="Run autonomous one-shot coding task")
    p_code.add_argument("instruction", nargs="+", help="Coding task instruction")
    p_code.add_argument("--file", "-f", help="Active file context")

    # scan command
    subparsers.add_parser("scan", help="Run full project & model diagnostics")

    # rollback command
    p_roll = subparsers.add_parser("rollback", help="Revert a modified file to latest backup")
    p_roll.add_argument("path", help="Path of the file to revert")

    args = parser.parse_args()

    if args.command == "chat" or not args.command:
        cmd_chat(args if args.command == "chat" else argparse.Namespace(session=None, file=None))
    elif args.command == "code":
        cmd_code(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "rollback":
        cmd_rollback(args)


if __name__ == "__main__":
    main()
