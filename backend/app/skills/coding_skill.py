import os
import re
import ast
import json
import difflib
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from .skill_base import BaseSkill, SkillTool

try:
    from app.persistent_memory import record_file_backup, restore_latest_backup, BACKUPS_DIR, WORKSPACE_ROOT, PROJECT_ROOT
except ImportError:
    from persistent_memory import record_file_backup, restore_latest_backup, BACKUPS_DIR, WORKSPACE_ROOT, PROJECT_ROOT


def _resolve_safe_path(rel_or_abs_path: str) -> Path:
    """Resolve a path safely within the user's workspace."""
    p = Path(rel_or_abs_path)
    if not p.is_absolute():
        p = (WORKSPACE_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _create_backup(target_path: Path, description: str = "Automated pre-edit backup") -> Optional[str]:
    """Create timestamped copy of file in BACKUPS_DIR before modifying."""
    if not target_path.exists() or not target_path.is_file():
        return None
    try:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = f"{target_path.stem}_{timestamp}{target_path.suffix}.bak"
        backup_file = BACKUPS_DIR / safe_name
        shutil.copy2(target_path, backup_file)
        record_file_backup(str(target_path), str(backup_file), description)
        return str(backup_file)
    except Exception as e:
        print(f"Warning: Failed to create file backup for {target_path}: {e}")
        return None


def _ensure_within_workspace(target: Path) -> Optional[Dict[str, Any]]:
    """Reject file mutations outside the workspace root."""
    try:
        target.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        return {"error": f"Blocked: '{target}' is outside the workspace root ({WORKSPACE_ROOT}). Writes are only allowed inside the project workspace."}
    return None


def _display_path(target: Path) -> str:
    try:
        return str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    except ValueError:
        return str(target).replace("\\", "/")


def _strip_code_fences(content: str) -> tuple[str, bool]:
    """Remove markdown code fences an LLM accidentally included in file content."""
    stripped = content.strip()
    if not stripped.startswith("```"):
        return content, False
    lines = content.splitlines(keepends=True)
    # drop opening fence line (```lang) and trailing fence line if present
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "".join(lines), True


def _validate_source(target: Path, content: str) -> Optional[str]:
    """Static validation for the file type; returns an error message or None."""
    suffix = target.suffix.lower()
    if suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            return f"Python syntax error at line {e.lineno}: {e.msg}"
    elif suffix == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            return f"JSON parse error at line {e.lineno} col {e.colno}: {e.msg}"
    return None


def _file_diff(target: Path, old_text: Optional[str], new_text: str) -> str:
    from_label = f"a/{target.name}" if old_text is not None else "/dev/null"
    diff_lines = list(
        difflib.unified_diff(
            (old_text or "").splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=from_label,
            tofile=f"b/{target.name}",
            n=3,
        )
    )
    return "".join(diff_lines)


class CodingSkill(BaseSkill):
    id = "coding_assistant"
    display_name = "Autonomous Code & Workspace Engineer"
    description = "Provides deep workspace scanning, file reading, code generation, unified diff generation, and safe existing-code editing with auto-backups."
    icon = "code-bracket"

    def _setup_tools(self):
        # 1. workspace_tree
        self.tools.append(
            SkillTool(
                name="workspace_tree",
                description="List the directory hierarchy, subdirectories, and files in the workspace with sizes and types.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path within workspace (default: '.' for root)",
                            "default": ".",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum directory nesting depth to explore (default: 3)",
                            "default": 3,
                        },
                        "include_hidden": {
                            "type": "boolean",
                            "description": "Whether to include hidden or ignored files like .git or .venv",
                            "default": False,
                        },
                    },
                },
                handler=self.tool_workspace_tree,
            )
        )

        # 2. read_file
        self.tools.append(
            SkillTool(
                name="read_file",
                description="Read contents of any text, code, or config file in the project. Supports optional line slice indexing.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative or absolute path to the target file"},
                        "start_line": {"type": "integer", "description": "Optional 1-indexed starting line"},
                        "end_line": {"type": "integer", "description": "Optional 1-indexed ending line (inclusive)"},
                    },
                    "required": ["path"],
                },
                handler=self.tool_read_file,
            )
        )

        # 3. write_file
        self.tools.append(
            SkillTool(
                name="write_file",
                description="Create a new file or completely overwrite an existing file with provided code content. Automatically creates a safe backup first.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative or absolute path to the target file"},
                        "content": {"type": "string", "description": "The exact code content to write"},
                        "overwrite": {"type": "boolean", "description": "Whether to allow overwriting if the file already exists", "default": True},
                    },
                    "required": ["path", "content"],
                },
                handler=self.tool_write_file,
            )
        )

        # 4. patch_file
        self.tools.append(
            SkillTool(
                name="patch_file",
                description="Safely replace a target snippet of code inside an existing file. Automatically validates uniqueness, generates unified diff, and creates a backup.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative or absolute path to the file to modify"},
                        "target_snippet": {"type": "string", "description": "Exact text block currently inside the file to be replaced"},
                        "replacement_snippet": {"type": "string", "description": "New replacement code block to insert in place of target_snippet"},
                    },
                    "required": ["path", "target_snippet", "replacement_snippet"],
                },
                handler=self.tool_patch_file,
            )
        )

        # 5. grep_search
        self.tools.append(
            SkillTool(
                name="grep_search",
                description="Search for exact text or regex patterns across project files. Returns matching files, line numbers, and snippets.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search term or regular expression to look for"},
                        "path": {"type": "string", "description": "Directory or file to search within (default: '.')", "default": "."},
                        "file_pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py', '*.tsx', '*.json')", "default": "*"},
                        "is_regex": {"type": "boolean", "description": "Whether query should be treated as a regex pattern", "default": False},
                    },
                    "required": ["query"],
                },
                handler=self.tool_grep_search,
            )
        )

        # 6. rollback_file
        self.tools.append(
            SkillTool(
                name="rollback_file",
                description="Instantly revert a file to its latest pre-modification backup snapshot if an edit was faulty or unwanted.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to restore"},
                    },
                    "required": ["path"],
                },
                handler=self.tool_rollback_file,
            )
        )

    def get_system_prompt_addon(self) -> str:
        return (
            "You have full access to the project workspace via the Coding Assistant tools:\n"
            "- Use `workspace_tree` to discover structure.\n"
            "- Use `read_file` to inspect code before proposing modifications.\n"
            "- Use `patch_file` for targeted modifications or `write_file` for new components.\n"
            "- All edits are automatically backed up and safe.\n"
            "- Never remove or break existing working features."
        )

    def tool_workspace_tree(self, path: str = ".", max_depth: int = 3, include_hidden: bool = False) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        if not target.exists():
            return {"error": f"Path '{path}' does not exist"}

        ignore_dirs = {".venv", "node_modules", ".git", "__pycache__", "dist", ".oxlintrc.json"}

        def scan_dir(dir_path: Path, current_depth: int):
            if current_depth > max_depth:
                return None
            entries = []
            try:
                for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                    if not include_hidden and (entry.name.startswith(".") or entry.name in ignore_dirs):
                        continue
                    if entry.is_dir():
                        children = scan_dir(entry, current_depth + 1)
                        entries.append({
                            "name": entry.name,
                            "type": "directory",
                            "path": str(entry.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                            "children": children,
                        })
                    else:
                        size = entry.stat().st_size
                        entries.append({
                            "name": entry.name,
                            "type": "file",
                            "size": size,
                            "path": str(entry.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                        })
            except PermissionError:
                pass
            return entries

        tree = scan_dir(target, 1)
        return {
            "root": str(target.relative_to(WORKSPACE_ROOT) if target != WORKSPACE_ROOT else ".").replace("\\", "/"),
            "items": tree,
        }

    def tool_read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        if not target.exists() or not target.is_file():
            return {"error": f"File '{path}' does not exist or is not a file"}

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            if start_line is not None or end_line is not None:
                s = max(1, start_line or 1) - 1
                e = min(total_lines, end_line or total_lines)
                sliced_lines = lines[s:e]
                indexed_content = "".join(f"{i + s + 1:4d}: {line}" for i, line in enumerate(sliced_lines))
                return {
                    "path": str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                    "total_lines": total_lines,
                    "showing_range": [s + 1, e],
                    "content": indexed_content,
                    "raw": "".join(sliced_lines),
                }

            # If small enough, return with line numbers
            indexed_content = "".join(f"{i + 1:4d}: {line}" for i, line in enumerate(lines))
            return {
                "path": str(target.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                "total_lines": total_lines,
                "content": indexed_content,
                "raw": content,
            }
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

    def tool_write_file(self, path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        blocked = _ensure_within_workspace(target)
        if blocked:
            return blocked
        if target.exists() and not overwrite:
            return {"error": f"File '{path}' already exists and overwrite is set to False"}

        if content is None or content == "":
            return {"error": "write_file received empty content; refusing to write. Provide the complete file content."}

        content, fences_stripped = _strip_code_fences(content)

        old_text: Optional[str] = None
        if target.exists() and target.is_file():
            old_text = target.read_text(encoding="utf-8", errors="replace")

        validation_error = _validate_source(target, content)

        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = _create_backup(target, "Pre-overwrite backup")

        try:
            target.write_text(content, encoding="utf-8")
        except Exception as e:
            return {"error": f"Failed to write file: {e}"}

        # Read-back verification: the file on disk must match what we intended.
        try:
            written = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": f"Write reported no error but file could not be read back: {e}"}
        if hashlib.sha256(written.encode("utf-8")).hexdigest() != hashlib.sha256(content.encode("utf-8")).hexdigest():
            return {"error": "Verification failed: file content on disk does not match the content that was written"}

        if validation_error:
            return {
                "success": False,
                "error": f"{validation_error} (file was written to '{_display_path(target)}' and backed up; fix the code and write it again)",
                "path": _display_path(target),
                "verified": True,
            }

        return {
            "success": True,
            "path": _display_path(target),
            "bytes_written": len(content.encode("utf-8")),
            "lines_written": content.count("\n") + 1,
            "backup_created": backup_path,
            "verified": True,
            "fences_stripped": fences_stripped,
            "diff": _file_diff(target, old_text, content),
        }

    def tool_patch_file(self, path: str, target_snippet: str, replacement_snippet: str) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        blocked = _ensure_within_workspace(target)
        if blocked:
            return blocked
        if not target.exists() or not target.is_file():
            return {"error": f"File '{path}' does not exist"}

        original_text = target.read_text(encoding="utf-8", errors="replace")

        # Normalize line endings for comparison
        clean_orig = original_text.replace("\r\n", "\n")
        clean_target = target_snippet.replace("\r\n", "\n")
        clean_replace = replacement_snippet.replace("\r\n", "\n")

        count = clean_orig.count(clean_target)
        if count == 0:
            return {
                "error": f"Target snippet not found in '{path}'. Please ensure exact matching including whitespace.",
                "snippet_preview": clean_target[:200],
            }
        if count > 1:
            return {
                "error": f"Target snippet appears {count} times in '{path}'. Please provide more surrounding lines for a unique match.",
            }

        backup_path = _create_backup(target, "Pre-patch backup")
        new_text = clean_orig.replace(clean_target, clean_replace, 1)

        validation_error = _validate_source(target, new_text)
        if validation_error:
            return {
                "success": False,
                "error": f"Patch rejected before writing: {validation_error}. The file was NOT modified; produce corrected replacement code and retry.",
            }

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                clean_orig.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{target.name}",
                tofile=f"b/{target.name}",
                n=3,
            )
        )
        diff_text = "".join(diff_lines)

        try:
            target.write_text(new_text, encoding="utf-8")
        except Exception as e:
            return {"error": f"Failed to write patched file: {e}"}

        applied_ok = clean_replace in target.read_text(encoding="utf-8", errors="replace")
        if not applied_ok:
            return {
                "success": False,
                "error": f"Patch verification failed: replacement snippet not found in '{path}' after write",
                "path": _display_path(target),
            }

        return {
            "success": True,
            "path": _display_path(target),
            "diff": diff_text,
            "backup_created": backup_path,
            "verified": True,
        }

    def tool_grep_search(self, query: str, path: str = ".", file_pattern: str = "*", is_regex: bool = False) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        if not target.exists():
            return {"error": f"Search path '{path}' does not exist"}

        results = []
        ignore_dirs = {".venv", "node_modules", ".git", "__pycache__", "dist"}

        if is_regex:
            try:
                pattern = re.compile(query)
            except re.error as e:
                return {"error": f"Invalid regular expression: {e}"}
        else:
            pattern = None

        search_files = [target] if target.is_file() else list(target.rglob(file_pattern))

        for f in search_files:
            if not f.is_file() or any(p in f.parts for p in ignore_dirs):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
                for i, line in enumerate(lines):
                    matched = (pattern.search(line) is not None) if is_regex else (query in line)
                    if matched:
                        results.append({
                            "file": str(f.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                            "line": i + 1,
                            "content": line.strip()[:200],
                        })
                        if len(results) >= 50:
                            break
            except Exception:
                continue
            if len(results) >= 50:
                break

        return {
            "query": query,
            "total_matches": len(results),
            "matches": results,
            "truncated": len(results) >= 50,
        }

    def tool_rollback_file(self, path: str) -> Dict[str, Any]:
        target = _resolve_safe_path(path)
        return restore_latest_backup(str(target))
