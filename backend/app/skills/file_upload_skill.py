import os
import hashlib
import uuid
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .skill_base import BaseSkill, SkillTool

try:
    from app.persistent_memory import WORKSPACE_ROOT, record_file_backup
except ImportError:
    from persistent_memory import WORKSPACE_ROOT, record_file_backup


class FileUploadSkill(BaseSkill):
    id = "file_upload_manager"
    display_name = "Workspace File & Image Upload Manager"
    description = "Upload files and images to the workspace with drag-and-drop support, store attachments, and allow AI to inspect uploaded content."
    icon = "upload"

    # Upload directory for user files
    UPLOAD_DIR = WORKSPACE_ROOT / "uploads"

    def __init__(self, enabled: bool = True):
        super().__init__(enabled=enabled)
        # Ensure upload directory exists
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _setup_tools(self):
        # 1. Upload file
        self.tools.append(
            SkillTool(
                name="upload_file",
                description="Upload a file to the workspace. Returns the file path and metadata.",
                parameters={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Original filename"},
                        "content_base64": {"type": "string", "description": "Base64 encoded file content"},
                        "mime_type": {"type": "string", "description": "MIME type of the file", "default": "application/octet-stream"},
                        "category": {"type": "string", "description": "Optional category for organization (e.g., 'image', 'code', 'document')", "default": "file"},
                    },
                    "required": ["filename", "content_base64"],
                },
                handler=self.tool_upload_file,
            )
        )

        # 2. List uploaded files
        self.tools.append(
            SkillTool(
                name="list_uploads",
                description="List all uploaded files in the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Optional filter by category", "default": ""},
                    },
                },
                handler=self.tool_list_uploads,
            )
        )

        # 3. Get uploaded file info
        self.tools.append(
            SkillTool(
                name="get_upload_info",
                description="Get information about an uploaded file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Filename to look up"},
                    },
                    "required": ["filename"],
                },
                handler=self.tool_get_upload_info,
            )
        )

        # 4. Delete uploaded file
        self.tools.append(
            SkillTool(
                name="delete_upload",
                description="Delete an uploaded file from the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Filename to delete"},
                    },
                    "required": ["filename"],
                },
                handler=self.tool_delete_upload,
            )
        )

        # 5. List attachments in messages (for chat integration)
        self.tools.append(
            SkillTool(
                name="list_attachments",
                description="List all attachments from chat messages.",
                parameters={"type": "object", "properties": {}},
                handler=self.tool_list_attachments,
            )
        )

    def tool_upload_file(
        self,
        filename: str,
        content_base64: str,
        mime_type: str = "application/octet-stream",
        category: str = "file",
    ) -> Dict[str, Any]:
        """Upload a file to the workspace."""
        import base64

        try:
            # Sanitize filename
            safe_filename = os.path.basename(filename)
            if not safe_filename:
                safe_filename = f"upload_{uuid.uuid4().hex[:8]}"

            # Generate unique filename to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            name, ext = os.path.splitext(safe_filename)
            final_filename = f"{name}_{timestamp}_{unique_id}{ext}"

            # Decode base64 content
            try:
                content_bytes = base64.b64decode(content_base64)
            except Exception as e:
                return {"success": False, "error": f"Failed to decode base64 content: {e}"}

            # Create category subdirectory if needed
            category_dir = self.UPLOAD_DIR / category.replace(" ", "_").lower()
            category_dir.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path = category_dir / final_filename
            file_path.write_bytes(content_bytes)

            # Calculate hash for verification
            file_hash = hashlib.sha256(content_bytes).hexdigest()

            # Record backup for versioning
            record_file_backup(str(file_path), str(file_path), f"Upload: {safe_filename}")

            return {
                "success": True,
                "path": str(file_path.relative_to(WORKSPACE_ROOT)),
                "filename": final_filename,
                "original_filename": safe_filename,
                "size": len(content_bytes),
                "mime_type": mime_type,
                "category": category,
                "sha256": file_hash,
                "uploaded_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tool_list_uploads(self, category: str = "") -> Dict[str, Any]:
        """List uploaded files."""
        try:
            search_dir = self.UPLOAD_DIR
            if category:
                search_dir = self.UPLOAD_DIR / category.replace(" ", "_").lower()

            if not search_dir.exists():
                return {"success": True, "files": [], "message": "No uploads directory"}

            files = []
            for f in search_dir.rglob("*"):
                if f.is_file():
                    stat = f.stat()
                    files.append({
                        "filename": f.name,
                        "path": str(f.relative_to(WORKSPACE_ROOT)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "category": category if category else f.parent.name,
                    })

            return {"success": True, "files": files, "count": len(files)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tool_get_upload_info(self, filename: str) -> Dict[str, Any]:
        """Get information about an uploaded file."""
        try:
            # Search in all subdirectories
            for f in self.UPLOAD_DIR.rglob("*"):
                if f.is_file() and f.name == filename:
                    stat = f.stat()
                    return {
                        "success": True,
                        "filename": f.name,
                        "path": str(f.relative_to(WORKSPACE_ROOT)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "category": f.parent.name,
                    }

            return {"success": False, "error": f"File '{filename}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tool_delete_upload(self, filename: str) -> Dict[str, Any]:
        """Delete an uploaded file."""
        try:
            for f in self.UPLOAD_DIR.rglob("*"):
                if f.is_file() and f.name == filename:
                    f.unlink()
                    return {"success": True, "deleted": str(f.relative_to(WORKSPACE_ROOT))}

            return {"success": False, "error": f"File '{filename}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tool_list_attachments(self) -> Dict[str, Any]:
        """List attachments currently retained in chat context."""
        try:
            try:
                from app import attachments as attach_engine
            except ImportError:
                import attachments as attach_engine
            return {
                "success": True,
                "attachments": attach_engine.SESSION_ATTACHMENTS,
                "count": len(attach_engine.SESSION_ATTACHMENTS),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_prompt_addon(self) -> str:
        return (
            "You have access to file upload tools:\n"
            "- Use `upload_file` to store files in the workspace.\n"
            "- Use `list_uploads` to see uploaded files.\n"
            "- Use `get_upload_info` for file details.\n"
            "- Use `delete_upload` to remove files.\n"
            "- All uploads are stored in the 'uploads' directory with backtracking.\n"
        )