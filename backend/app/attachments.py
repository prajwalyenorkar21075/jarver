"""
ChatGPT-style attachment engine for JARVIS chat.

Pipeline: upload (validated) -> stored under workspace /uploads -> content
extraction (image metrics + AI vision, PDF/DOCX/text/code, video frames) ->
injected into chat context -> real tool execution (image edits, inpaint
removal, CAD import, video analysis) -> outputs served back by URL.

Every function returns honest results: failures carry an ``error`` field and
nothing is ever reported as success without on-disk verification.
"""
import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import statistics
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

try:
    from app.persistent_memory import WORKSPACE_ROOT
except ImportError:
    from persistent_memory import WORKSPACE_ROOT

try:
    from app.image_service import image_service
except ImportError:
    from image_service import image_service

logger = logging.getLogger("jarvis.attachments")

UPLOAD_DIR = WORKSPACE_ROOT / "uploads"
OUTPUT_DIR = UPLOAD_DIR / "outputs"

MAX_UPLOAD_BYTES = 60 * 1024 * 1024

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
XLSX_EXTS = {".xlsx", ".xls"}
PPTX_EXTS = {".pptx"}
TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".jsonl",
    ".xml", ".yaml", ".yml", ".toml", ".ini", ".env", ".log",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".scss",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".go", ".rs", ".rb", ".php",
    ".sh", ".bat", ".ps1", ".sql", ".r", ".m", ".swift", ".kt", ".lua",
}
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz"}
ALLOWED_EXTS = (
    IMAGE_EXTS | VIDEO_EXTS | PDF_EXTS | DOCX_EXTS | XLSX_EXTS | PPTX_EXTS
    | TEXT_EXTS | ARCHIVE_EXTS
)

MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
    ".tiff": "image/tiff", ".tif": "image/tiff",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska", ".webm": "video/webm",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain", ".md": "text/markdown", ".json": "application/json",
}

# Process-local conversation context so follow-ups like "rotate it 90 degrees"
# resolve "it" without the frontend having to re-send the file.
SESSION_ATTACHMENTS: List[Dict[str, Any]] = []
MAX_SESSION_ATTACHMENTS = 10

TEXT_CHUNK_LIMIT = 6000


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def safe_attachment_path(rel_path: str) -> Path:
    """Resolve a workspace-relative attachment path, refusing traversal."""
    candidate = Path(rel_path)
    if not candidate.is_absolute():
        candidate = WORKSPACE_ROOT / candidate
    resolved = candidate.resolve()
    root = WORKSPACE_ROOT.resolve()
    if os.path.commonpath([str(resolved), str(root)]) != str(root):
        raise ValueError("Attachment path escapes the workspace")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"File not found: {rel_path}")
    return resolved


def workspace_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(WORKSPACE_ROOT.resolve()))
    except ValueError:
        return str(path)


def attachment_url(path: Path) -> str:
    return "/api/files/" + workspace_rel(path).replace("\\", "/")


def classify_category(filename: str, mime_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS or mime_type.startswith("image/"):
        return "image"
    if ext in VIDEO_EXTS or mime_type.startswith("video/"):
        return "video"
    if ext in PDF_EXTS:
        return "pdf"
    if ext in DOCX_EXTS or ext in XLSX_EXTS or ext in PPTX_EXTS:
        return "document"
    if ext in TEXT_EXTS or mime_type.startswith("text/"):
        return "code" if ext not in {".txt", ".md", ".csv", ".json"} else "document"
    return "file"


def validate_upload(filename: str, content_base64: str, mime_type: str = "") -> Tuple[bool, str, str]:
    """Return (ok, error, category) for a base64 upload payload."""
    try:
        raw_len = len(content_base64)
    except Exception:
        return False, "Invalid content payload", ""
    if raw_len == 0:
        return False, "Empty file content", ""
    if raw_len * 3 // 4 > MAX_UPLOAD_BYTES:
        return False, f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit", ""
    ext = Path(os.path.basename(filename)).suffix.lower()
    if ext and ext not in ALLOWED_EXTS:
        return False, f"Unsupported file type '{ext}'. Supported: images, video, PDF, documents, code/text files.", ""
    if not ext:
        return False, "Uploaded file has no extension; cannot classify it.", ""
    return True, "", classify_category(filename, mime_type)


def _append_upload_index(record: Dict[str, Any]):
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        index_path = UPLOAD_DIR / "uploads_index.jsonl"
        with index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning(f"[ATTACH] upload index write failed: {exc}")


def remember_attachments(items: List[Dict[str, Any]]):
    for it in items:
        SESSION_ATTACHMENTS.append(it)
    del SESSION_ATTACHMENTS[:-MAX_SESSION_ATTACHMENTS]
    try:
        _append_upload_index({
            "event": "chat_attachments",
            "at": datetime.now().isoformat(),
            "attachments": [
                {"filename": a.get("filename"), "path": a.get("path"), "mime_type": a.get("mime_type")}
                for a in items
            ],
        })
    except Exception:
        pass
    try:
        try:
            from app.persistent_memory import save_conversation_turn
        except ImportError:
            from persistent_memory import save_conversation_turn
        save_conversation_turn(
            "user",
            f"[attached {', '.join(a.get('filename', 'file') for a in items)}]",
            metadata={"attachments": session_attachment_payload()},
        )
    except Exception as exc:
        logger.debug(f"[ATTACH] turn persistence skipped: {exc}")


def session_attachment_payload() -> List[Dict[str, Any]]:
    return [
        {"filename": a.get("filename"), "path": a.get("path"), "mime_type": a.get("mime_type")}
        for a in SESSION_ATTACHMENTS[-MAX_SESSION_ATTACHMENTS:]
    ]


def restore_session_attachments_from_db():
    """Rebuild context after a restart from persisted conversation metadata."""
    global SESSION_ATTACHMENTS
    try:
        try:
            from app.persistent_memory import get_recent_conversations
        except ImportError:
            from persistent_memory import get_recent_conversations
        restored: List[Dict[str, Any]] = []
        for turn in get_recent_conversations(limit=40):
            for a in (turn.get("metadata") or {}).get("attachments", []):
                if a.get("path"):
                    restored.append(a)
        if restored:
            SESSION_ATTACHMENTS = restored[-MAX_SESSION_ATTACHMENTS:]
            logger.info(f"[ATTACH] Restored {len(SESSION_ATTACHMENTS)} attachment refs from memory.")
    except Exception as exc:
        logger.warning(f"[ATTACH] session restore skipped: {exc}")


restore_session_attachments_from_db()


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def _file_record(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    return {
        "filename": path.name,
        "path": workspace_rel(path),
        "url": attachment_url(path),
        "size": stat.st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
        "category": classify_category(path.name),
        "mime_type": MIME_BY_EXT.get(path.suffix.lower())
        or mimetypes.guess_type(path.name)[0]
        or "application/octet-stream",
    }


def _call_gemini_with_images(prompt: str, image_paths: List[Path], max_tokens: int = 500) -> Optional[str]:
    """Real multimodal call: Gemini generateContent with inline_data parts."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    if not api_key:
        return None

    import httpx

    parts: List[Dict[str, Any]] = [{"text": prompt}]
    for p in image_paths[:3]:
        try:
            blob = p.read_bytes()
            if len(blob) > 4 * 1024 * 1024:
                img = Image.open(p)
                img.thumbnail((1024, 1024))
                import io
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=80)
                blob = buf.getvalue()
            parts.append({
                "inline_data": {
                    "mime_type": MIME_BY_EXT.get(p.suffix.lower(), "image/jpeg"),
                    "data": base64.b64encode(blob).decode(),
                }
            })
        except Exception as exc:
            logger.warning(f"[ATTACH] inline image skipped ({p.name}): {exc}")
    if len(parts) == 1:
        return None
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens},
    }
    try:
        resp = httpx.post(f"{url}?key={api_key}", json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        texts = [t.get("text", "") for t in data["candidates"][0]["content"]["parts"] if t.get("text")]
        joined = "\n".join(texts).strip()
        return joined or None
    except Exception as exc:
        logger.warning(f"[ATTACH] Gemini vision call failed: {exc}")
        return None


def _image_metrics(path: Path) -> Dict[str, Any]:
    img = Image.open(path)
    img.load()
    rgb = img.convert("RGB")
    arr = np.asarray(rgb)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    hue_hist = cv2.calcHist([hsv], [0], None, [12], [0, 180])[0]
    hue_names = ["red", "orange", "yellow", "green", "cyan", "blue",
                 "purple", "magenta", "pink", "rose", "red2", "red3"]
    dominant = hue_names[int(np.argmax(hue_hist))]
    brightness = float(np.mean(arr))
    shapes = _detect_shapes(arr)
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format or img.mode,
        "mode": img.mode,
        "has_alpha": img.mode in ("RGBA", "LA", "P"),
        "mean_brightness": round(brightness, 1),
        "exposure": "dark" if brightness < 60 else ("bright" if brightness > 195 else "normal"),
        "dominant_hue": dominant,
        "detected_shapes": shapes,
    }


def _detect_shapes(arr: np.ndarray, max_shapes: int = 8) -> List[Dict[str, Any]]:
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    min_area = (h * w) * 0.002
    found: List[Dict[str, Any]] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.03 * peri, True)
        x, y, bw, bh = cv2.boundingRect(c)
        circularity = 4 * np.pi * area / (peri * peri) if peri else 0.0
        if len(approx) == 3:
            kind = "triangle"
        elif len(approx) == 4:
            kind = "rectangle"
        elif circularity > 0.75:
            kind = "circle"
        else:
            kind = "blob"
        found.append({
            "shape": kind,
            "bbox": {"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)},
            "area_px": int(area),
            "position": _position_label(x, y, bw, bh, w, h),
            "contour_index": len(found),
            "_contour": c,
        })
        if len(found) >= max_shapes:
            break
    found.sort(key=lambda s: -s["area_px"])
    for i, s in enumerate(found):
        s["rank"] = i + 1
    return found


def _position_label(x, y, w, h, fw, fh) -> str:
    cx, cy = x + w / 2, y + h / 2
    vert = "top" if cy < fh / 3 else ("bottom" if cy > 2 * fh / 3 else "middle")
    horiz = "left" if cx < fw / 3 else ("right" if cx > 2 * fw / 3 else "center")
    return f"{vert}-{horiz}"


def _ocr_text(path: Path) -> Optional[str]:
    try:
        import pytesseract
        from PIL import Image as PILImage
        return pytesseract.image_to_string(PILImage.open(path)).strip()
    except Exception:
        return None


def _describe_image(path: Path, question: Optional[str] = None) -> Dict[str, Any]:
    record: Dict[str, Any] = {"type": "image"}
    try:
        record.update(_image_metrics(path))
    except Exception as exc:
        return {"type": "image", "error": f"Could not read image pixels: {exc}"}

    ocr = _ocr_text(path)
    if ocr:
        record["ocr_text"] = ocr[:1500]

    prompt = (
        "You are analyzing a user-attached image for an AI assistant. "
        + (question or "Describe the main subjects, layout, colors and any visible text concisely.")
        + " Be factual; do not invent details."
    )
    vision = _call_gemini_with_images(prompt, [path])
    if vision:
        record["ai_description"] = vision
        record["ai_model"] = os.getenv("GEMINI_MODEL", "gemini")
    else:
        record["note"] = "AI vision description unavailable (no Gemini key or provider error); pixel analysis results above are real."
    return record


def _extract_pdf(path: Path) -> Dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"type": "pdf", "error": "PDF parsing needs the 'pypdf' package (pip install pypdf)."}
    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:25])
        meta = {}
        try:
            info = reader.metadata or {}
            meta = {k.lstrip("/"): str(v) for k, v in info.items() if v}
        except Exception:
            pass
        return {
            "type": "pdf",
            "pages": pages,
            "metadata": meta,
            "text": text[:TEXT_CHUNK_LIMIT],
            "truncated": len(text) > TEXT_CHUNK_LIMIT,
        }
    except Exception as exc:
        return {"type": "pdf", "error": f"Failed to parse PDF: {exc}"}


def _extract_docx(path: Path) -> Dict[str, Any]:
    try:
        import docx
    except ImportError:
        return {"type": "document", "error": "DOCX parsing needs the 'python-docx' package."}
    try:
        d = docx.Document(str(path))
        paras = [p.text for p in d.paragraphs if p.text.strip()]
        tables = len(d.tables)
        return {"type": "document", "paragraph_count": len(paras), "tables": tables,
                "text": "\n".join(paras)[:TEXT_CHUNK_LIMIT]}
    except Exception as exc:
        return {"type": "document", "error": f"Failed to parse DOCX: {exc}"}


def _extract_text_or_code(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return {"type": "text", "error": f"Could not read file: {exc}"}
    if b"\x00" in raw[:4096]:
        return {"type": "binary", "size": len(raw),
                "note": "Binary file: no text content extracted."}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    lines = text.splitlines()
    return {
        "type": "text",
        "lines": len(lines),
        "chars": len(text),
        "content": text[:TEXT_CHUNK_LIMIT],
        "truncated": len(text) > TEXT_CHUNK_LIMIT,
    }


def extract_video(path: Path, ai_analysis: bool = True) -> Dict[str, Any]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"type": "video", "error": "OpenCV could not decode this video file."}
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frame_count / fps if fps else 0.0
        record: Dict[str, Any] = {
            "type": "video", "width": width, "height": height,
            "fps": round(fps, 2), "frames": frame_count,
            "duration_seconds": round(duration, 2),
        }
        frames: List[Tuple[float, np.ndarray]] = []
        if frame_count > 0:
            picks = np.linspace(0, max(frame_count - 1, 0), min(4, frame_count or 1))
            for idx in picks:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ok, frame = cap.read()
                if ok:
                    frames.append((int(idx) / fps if fps else 0.0, frame))
        saved_paths: List[Path] = []
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for t, frame in frames:
            out = OUTPUT_DIR / f"frame_{path.stem}_{int(t)}s_{uuid.uuid4().hex[:6]}.jpg"
            if cv2.imwrite(str(out), frame):
                saved_paths.append(out)
        record["sampled_frames"] = [
            {"time_seconds": round(t, 2), "url": attachment_url(p), "path": workspace_rel(p)}
            for (t, _), p in zip(frames, saved_paths)
        ]
        if ai_analysis and saved_paths:
            desc = _call_gemini_with_images(
                "These are chronological frames sampled from a user-attached video. "
                "Describe what happens across the frames and any visible text.", saved_paths)
            if desc:
                record["ai_description"] = desc
        return record
    finally:
        cap.release()


def process_attachment(att: Dict[str, Any]) -> Dict[str, Any]:
    """Extract real content for one attachment reference."""
    try:
        path = safe_attachment_path(att.get("path", ""))
    except Exception as exc:
        return {"filename": att.get("filename"), "error": str(exc)}
    record = _file_record(path)
    category = record["category"]
    try:
        if category == "image":
            record.update(_describe_image(path, att.get("question")))
        elif category == "pdf":
            record.update(_extract_pdf(path))
        elif category == "document" and path.suffix.lower() in DOCX_EXTS:
            record.update(_extract_docx(path))
        elif category == "video":
            record.update(extract_video(path, ai_analysis=bool(att.get("deep_video_analysis"))))
        elif category in ("code", "document", "file") and path.suffix.lower() in TEXT_EXTS:
            record.update(_extract_text_or_code(path))
        elif category == "file" and path.suffix.lower() in ARCHIVE_EXTS:
            import zipfile
            names = []
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()[:50]
            record.update({"type": "archive", "entries": names, "entry_count": len(names)})
        else:
            record["note"] = f"No extractor registered for '{path.suffix}' files."
    except Exception as exc:
        record["error"] = f"Extraction failed: {exc}"
        logger.error(f"[ATTACH] extract error for {path.name}: {exc}", exc_info=True)
    return record


# ---------------------------------------------------------------------------
# Chat-context digest
# ---------------------------------------------------------------------------

def build_attachment_digest(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    blocks: List[str] = ["[ATTACHED FILES — real extracted content, not speculation]"]
    for r in records:
        name = r.get("filename") or r.get("path") or "attachment"
        url = r.get("url", "")
        cat = r.get("category")
        if r.get("error"):
            blocks.append(f"- {name}: ERROR — {r['error']}")
            continue
        head = f"- {name} ({cat}, {r.get('size', 0)} bytes" + (f", url: {url}" if url else "") + ")"
        if cat == "image":
            parts = [f"size {r.get('width')}x{r.get('height')} px",
                     f"format {r.get('format')}",
                     f"exposure {r.get('exposure')}",
                     f"dominant hue {r.get('dominant_hue')}"]
            shapes = r.get("detected_shapes") or []
            if shapes:
                parts.append("shapes: " + ", ".join(
                    f"{s['shape']}#{s['rank']} at {s['position']} bbox={s['bbox']}" for s in shapes[:6]))
            if r.get("ocr_text"):
                parts.append(f"OCR text: {r['ocr_text'][:600]}")
            if r.get("ai_description"):
                parts.append(f"AI vision description: {r['ai_description'][:900]}")
            blocks.append(head + " — " + "; ".join(parts))
        elif cat == "pdf":
            txt = (r.get("text") or "").strip()
            blocks.append(head + f" pages={r.get('pages')}" + (f"\n{text[:2500]}" if txt else " (no extractable text)"))
        elif r.get("type") == "document":
            txt = (r.get("text") or "").strip()
            blocks.append(head + f" paragraphs={r.get('paragraph_count')}" + (f"\n{text[:2500]}" if txt else ""))
        elif r.get("type") == "text":
            blocks.append(head + f" lines={r.get('lines')}\n{r.get('content', '')[:2500]}")
        elif cat == "video":
            frames = r.get("sampled_frames") or []
            blocks.append(head + f" {r.get('width')}x{r.get('height')} {r.get('fps')}fps "
                          f"duration={r.get('duration_seconds')}s frames={r.get('frames')}"
                          + (f"\nAI description: {r['ai_description'][:800]}" if r.get("ai_description") else "")
                          + "\nsampled frame urls: " + ", ".join(f["url"] for f in frames[:4]))
        elif r.get("type") == "archive":
            blocks.append(head + f" entries={r.get('entry_count')}: " + ", ".join(r.get("entries", [])[:20]))
        else:
            blocks.append(head + " " + r.get("note", ""))
    blocks.append("[/ATTACHED FILES]")
    return "\n".join(blocks)


def capability_note(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    cats = {r.get("category") for r in records if not r.get("error")}
    notes = []
    if "image" in cats:
        notes.append(
            "The image is loaded as JARVIS's active image. You can act on it with real tools: "
            "rotate/resize/crop/flip/grayscale/brightness/contrast, convert format, remove a detected "
            "shape (inpainting), summarize, or import its geometry into CAD ('use this in CAD').")
    if "video" in cats:
        notes.append("Video metadata and sampled frames already exist; further frame extraction or format conversion can be executed.")
    if cats & {"pdf", "document", "code"}:
        notes.append("Full extracted text is above — quote it when summarizing; never invent file content.")
    return " ".join(notes)


# ---------------------------------------------------------------------------
# Real operations (image editing / CAD import / conversion)
# ---------------------------------------------------------------------------

def _verify_image_output(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            im.verify()
        return path.exists() and path.stat().st_size > 0
    except Exception:
        return False


def _op_output_path(stem_hint: str, ext: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"{stem_hint}_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}{ext}"


def apply_image_edit(source: Path, instruction: str) -> Dict[str, Any]:
    """Execute a real, deterministic image edit from natural language."""
    text = instruction.lower()
    try:
        img = Image.open(source)
        img.load()
    except Exception as exc:
        return {"success": False, "error": f"Cannot open image: {exc}"}

    ops_done: List[str] = []
    out_ext = source.suffix.lower()
    format_target = None
    m = re.search(r"convert (?:it |this )?(?:to|into) (png|jpe?g|webp|bmp)", text)
    if m:
        format_target = {"jpg": "jpeg", "jpeg": "jpeg"}.get(m.group(1), m.group(1))

    m = re.search(r"rotat\w*\s+(?:it\s+)?(?:by\s+)?(-?\d+(?:\.\d+)?)\s*(?:deg|degrees|°)?", text)
    if m and "rotat" in text:
        angle = float(m.group(1))
        img = img.convert("RGBA") if img.mode == "RGBA" else img
        img = img.rotate(angle, expand=True)
        ops_done.append(f"rotated {angle}°")

    if "90 clockwise" in text or "rotate right" in text:
        img = img.rotate(-90, expand=True)
        ops_done.append("rotated 90° clockwise")

    m = re.search(r"(?:resize|scale|make it)\D{0,12}(\d{1,4})\s*(?:x|by|×)\s*(\d{1,4})", text)
    if m:
        img = img.resize((int(m.group(1)), int(m.group(2))))
        ops_done.append(f"resized to {m.group(1)}x{m.group(2)}")
    else:
        m = re.search(r"(\d{1,3})\s*(?:%|percent)\s*(?:smaller|bigger|larger|resize|scale)", text)
        if m:
            factor = (100 - int(m.group(1))) / 100 if "smaller" in text else (100 + int(m.group(1))) / 100
            img = img.resize((max(1, int(img.width * factor)), max(1, int(img.height * factor))))
            ops_done.append(f"scaled by {factor:.2f}x")
        elif re.search(r"half the size|halve", text):
            img = img.resize((max(1, img.width // 2), max(1, img.height // 2)))
            ops_done.append("halved in size")

    m = re.search(r"crop\D{0,10}(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text)
    if m:
        l, t, r, b = (int(g) for g in m.groups())
        img = img.crop((min(l, r), min(t, b), max(l, r), max(t, b)))
        ops_done.append(f"cropped to ({l},{t},{r},{b})")
    elif "crop" in text and re.search(r"cent(?:er|re)\s*(\d{1,3})\s*(?:%|percent)", text):
        pct = int(re.search(r"cent(?:er|re)\s*(\d{1,3})", text).group(1)) / 100
        w, h = int(img.width * pct), int(img.height * pct)
        x0, y0 = (img.width - w) // 2, (img.height - h) // 2
        img = img.crop((x0, y0, x0 + w, y0 + h))
        ops_done.append(f"center-cropped to {pct:.0%}")

    if "grayscale" in text or "black and white" in text:
        img = ImageOps.grayscale(img).convert("RGB") if format_target else ImageOps.grayscale(img)
        ops_done.append("converted to grayscale")

    m = re.search(r"(brighter|brighten|darker)\D{0,10}(\d{1,3})?\s*(%|percent)?", text)
    if m:
        delta = int(m.group(2) or 25) / 100
        factor = 1 + delta if m.group(1) != "darker" else 1 - delta
        img = ImageEnhance.Brightness(img).enhance(max(0.05, factor))
        ops_done.append(f"brightness x{factor:.2f}")

    m = re.search(r"contrast\D{0,12}(\d{1,3})\s*(%|percent)?", text)
    if m:
        factor = 1 + int(m.group(1)) / 100
        img = ImageEnhance.Contrast(img).enhance(max(0.05, factor))
        ops_done.append(f"contrast x{factor:.2f}")

    if re.search(r"flip (horizontally|left|right)", text) or "mirror" in text:
        img = ImageOps.mirror(img)
        ops_done.append("flipped horizontally")
    if re.search(r"flip vertically|upside", text):
        img = ImageOps.flip(img)
        ops_done.append("flipped vertically")

    if re.search(r"(remove|delete|erase|fill)\s+(the\s+)?(background)", text):
        arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        border_px = int(min(gray.shape) * 0.02) or 1
        marker = np.zeros((gray.shape[0] + 2, gray.shape[1] + 2), np.uint8)
        mask_edge = cv2.Canny(gray, 30, 120)
        marker[max(1, border_px):-1, max(1, border_px):-1] = 0
        _, th = cv2.threshold(cv2.bitwise_not(mask_edge), 200, 255, cv2.THRESH_BINARY)
        marker[1:-1, 1:-1] = (th // 255).astype(np.uint8)
        try:
            res = cv2.floodFill(arr.copy(), marker.copy(), (0, 0), (255, 255, 255),
                                loDiff=(10, 10, 10), upDiff=(10, 10, 10),
                                flags=4 | cv2.FLOODFILL_FIXED_RANGE)[1]
            img = Image.fromarray(cv2.cvtColor(res, cv2.COLOR_BGR2RGB))
            ops_done.append("background lightened via flood-fill segmentation")
        except Exception as exc:
            ops_done.append(f"background removal attempted but failed: {exc}")

    if not ops_done:
        return {"success": False,
                "error": "No recognized image operation in that instruction (supported: rotate, resize/scale %, crop, grayscale, brightness, contrast, flip/mirror, background lighten, format convert)."}

    if format_target:
        out_ext = {"jpeg": ".jpg", "png": ".png", "webp": ".webp", "bmp": ".bmp"}.get(format_target, source.suffix.lower())
        ops_done.append(f"converted to {format_target.upper()}")

    if img.mode in ("P", "1") and out_ext in (".jpg", ".jpeg"):
        img = img.convert("RGB")

    out = _op_output_path(source.stem, out_ext)
    try:
        img.save(out)
    except Exception as exc:
        return {"success": False, "error": f"Failed writing edited image: {exc}"}
    if not _verify_image_output(out):
        return {"success": False, "error": "Edited image failed post-write verification."}

    try:
        image_service.load_image(str(out))
    except Exception:
        pass

    return {
        "success": True,
        "operations": ops_done,
        "output": {**_file_record(out), "width": img.width, "height": img.height},
    }


def remove_shape_from_image(source: Path, shape_ref: str, all_shapes: bool = False) -> Dict[str, Any]:
    """Real object removal: detect shapes, mask the referenced one, inpaint."""
    try:
        img = Image.open(source)
        img.load()
        arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    except Exception as exc:
        return {"success": False, "error": f"Cannot open image: {exc}"}

    shapes = _detect_shapes(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
    if not shapes:
        return {"success": False, "error": "No distinct closed shapes were detected in this image, so there is nothing I can safely remove."}

    targets: List[Dict[str, Any]] = []
    if all_shapes:
        targets = shapes
    else:
        ref = shape_ref.lower()
        mnum = re.search(r"\b(\d+)\b", ref)
        by_pos = [s for s in shapes if s["position"].split("-")[1] in ref or ref in s["position"]]
        by_type = [s for s in shapes if s["shape"] in ref]
        candidates = by_pos or by_type or shapes
        if mnum and re.search(r"\b(remove|delete)\b", ref):
            idx = int(mnum.group(1))
            targets = [candidates[idx - 1]] if 1 <= idx <= len(candidates) else [candidates[-1]]
        else:
            targets = [max(candidates, key=lambda s: s["area_px"])]

    mask = np.zeros(arr.shape[:2], np.uint8)
    for t in targets:
        cv2.drawContours(mask, [t["_contour"]], -1, 255, thickness=cv2.FILLED)
        cv2.dilate(mask, np.ones((7, 7), np.uint8), iterations=2, dst=mask)
    if int(np.count_nonzero(mask)) == 0:
        return {"success": False, "error": "The referenced object could not be masked."}

    removed = [f"{t['shape']}#{t['rank']} ({t['position']})" for t in targets]
    try:
        result = cv2.inpaint(arr, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    except Exception as exc:
        return {"success": False, "error": f"Inpainting failed: {exc}"}

    out_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    out = _op_output_path(source.stem, ".png")
    out_img.save(out)
    if not _verify_image_output(out):
        return {"success": False, "error": "Inpainted output failed verification."}
    try:
        image_service.load_image(str(out))
    except Exception:
        pass
    return {
        "success": True,
        "operations": [f"removed {', '.join(removed)} via Telea inpainting"],
        "output": {**_file_record(out), "width": out_img.width, "height": out_img.height},
    }


def image_geometry_to_cad(source: Path, size_mm: float = 100.0) -> Dict[str, Any]:
    """Import real geometry detected in an image as a CAD primitive."""
    try:
        arr = np.array(Image.open(source).convert("RGB"))
    except Exception as exc:
        return {"success": False, "error": f"Cannot read image: {exc}"}
    shapes = _detect_shapes(arr)
    if not shapes:
        return {"success": False, "error": "No usable geometry (rectangle/circle/triangle) was detected in the image."}
    top = shapes[0]
    bbox = top["bbox"]
    longest = max(bbox["w"], bbox["h"], 1)
    scale = size_mm / longest
    try:
        try:
            from app.cad_engine.features.modeling import CADModelingOperations
        except ImportError:
            from cad_engine.features.modeling import CADModelingOperations
    except Exception as exc:
        return {"success": False, "error": f"CAD engine unavailable: {exc}"}

    try:
        if top["shape"] == "circle":
            radius = round(max(bbox["w"], bbox["h"]) * scale / 2, 2)
            feature = CADModelingOperations.create_cylinder(radius, round(size_mm * bbox["h"] / max(bbox["w"], 1), 2),
                                                            name=f"FromImage_{top['shape']}")
            detail = f"cylinder r={radius}mm"
        elif top["shape"] == "rectangle":
            w = round(bbox["w"] * scale, 2)
            h = round(size_mm, 2)
            d = round(bbox["h"] * scale, 2)
            feature = CADModelingOperations.create_box(w, h, d, name=f"FromImage_{top['shape']}")
            detail = f"box {w}x{h}x{d}mm"
        else:
            w = round(bbox["w"] * scale, 2)
            feature = CADModelingOperations.create_box(w, size_mm, w, name=f"FromImage_{top['shape']}")
            detail = f"box {w}x{size_mm}x{w}mm (from {top['shape']} outline)"
        return {
            "success": True,
            "feature_id": feature.id,
            "shape_detected": top["shape"],
            "image_bbox_px": bbox,
            "reference_longest_side_mm": size_mm,
            "created": detail,
            "other_shapes": [s["shape"] for s in shapes[1:5]],
        }
    except Exception as exc:
        return {"success": False, "error": f"CAD creation failed: {exc}"}


IMAGE_INTENT_RE = re.compile(
    r"\b(rotate|resize|scale|crop|grayscale|black and white|brighten|brighter|darker|"
    r"contrast|flip|mirror|upside|convert|remove|delete|erase)\b", re.I)
REMOVE_RE = re.compile(r"\b(remove|delete|erase)\b.*\b(circle|rectangle|shape|object|triangle|blob|box|them?|it)\b", re.I)
CAD_RE = re.compile(r"\b(cad|model|extrude|solid)\b", re.I)
SUMMARIZE_RE = re.compile(r"\b(summar|describ|analy[sz]e|what|read|explain|convert to (pdf|word|text))\b", re.I)


def try_handle_attachment_turn(text: str, records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Deterministic real execution for follow-up commands on live attachments.

    Returns None when this turn should continue into the normal chat cascade.
    """
    usable = [r for r in records if not r.get("error")]
    if not usable:
        return None
    imgs = [r for r in usable if r.get("category") == "image"]
    vids = [r for r in usable if r.get("category") == "video"]

    if imgs and CAD_RE.search(text) and re.search(r"\buse\b|\bimport\b|\bconvert\b|\bmake\b|\bbuild\b", text, re.I):
        res = image_geometry_to_cad(safe_attachment_path(imgs[-1]["path"]))
        if res.get("success"):
            return {
                "reply": f"I imported the {res['shape_detected']} geometry from {imgs[-1]['filename']} into the active CAD document as a {res['created']}, sir. Feature id {res['feature_id'][:8]}.",
                "status": "ok",
                "cad_action": {"action": "create_primitive", "feature_id": res["feature_id"]},
                "attachment_result": res,
            }
        return {"reply": f"I attempted the CAD import but it failed honestly: {res.get('error')}", "status": "error",
                "attachment_result": res}

    if imgs and REMOVE_RE.search(text):
        res = remove_shape_from_image(safe_attachment_path(imgs[-1]["path"]), text)
        if res.get("success"):
            return {"reply": f"Done, sir. I {res['operations'][0]}. The cleaned image is attached below.",
                    "status": "ok", "outputs": [res["output"]], "attachment_result": res}
        return {"reply": f"Object removal did not complete: {res.get('error')}", "status": "error",
                "attachment_result": res}

    if imgs and IMAGE_INTENT_RE.search(text) and not SUMMARIZE_RE.search(text):
        res = apply_image_edit(safe_attachment_path(imgs[-1]["path"]), text)
        if res.get("success"):
            return {"reply": "Image edited for real: " + ", ".join(res["operations"]) + ". The result is attached below, sir.",
                    "status": "ok", "outputs": [res["output"]], "attachment_result": res}
        if "No recognized image operation" in (res.get("error") or ""):
            return None  # let the LLM answer conversationally
        return {"reply": f"The image edit failed: {res.get('error')}", "status": "error",
                "attachment_result": res}

    if vids and re.search(r"\b(convert|extract|frames?|thumbnail|analyse|analyze)\b", text, re.I):
        vid = safe_attachment_path(vids[-1]["path"])
        frames = vids[-1].get("sampled_frames") or []
        if not frames:
            fresh = extract_video(vid, ai_analysis=False)
            frames = fresh.get("sampled_frames", [])
        if frames:
            return {"reply": (f"I decoded {vids[-1]['filename']} ({vids[-1].get('duration_seconds')}s) and wrote "
                              f"{len(frames)} real frame images to the workspace, sir. Previews are attached."),
                    "status": "ok", "outputs": [_file_record(safe_attachment_path(f["path"])) for f in frames]}
        return {"reply": f"Frame extraction failed for {vids[-1]['filename']} — the decoder could not read it.",
                "status": "error"}

    return None


def attachments_to_chat_payload(chat_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize frontend attachment refs (name/path/mime) to internal form."""
    out = []
    for a in chat_files:
        out.append({
            "filename": a.get("filename") or a.get("name") or Path(a.get("path", "file")).name,
            "path": a.get("path", ""),
            "mime_type": a.get("mime_type") or a.get("mimeType") or "",
        })
    return out


# ---------------------------------------------------------------------------
# Chat-turn orchestration (validation, TTL record cache, context reuse)
# ---------------------------------------------------------------------------

ATTACHMENT_REF_RE = re.compile(
    r"\b(this|that|the|these|those|attached|attachment|image|photo|picture|file|pdf|doc|docx|"
    r"document|video|clip|it|them|screenshot|frame|scan|drawing)\b|"
    r"\b(rotate|resize|crop|grayscale|brighten|brighter|darker|contrast|flip|mirror|inpaint|"
    r"remove|erase|convert|summar|analy[sz]e|extract|ocr|translat|describe|read)\b", re.I)

_RECORD_TTL_SECONDS = 900
_RECORD_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _cached_process(att: Dict[str, Any]) -> Dict[str, Any]:
    key = f"{att.get('path')}|{att.get('question')}"
    now = time.time()
    hit = _RECORD_CACHE.get(key)
    if hit and now - hit[0] < _RECORD_TTL_SECONDS:
        return hit[1]
    record = process_attachment(att)
    _RECORD_CACHE[key] = (now, record)
    return record


def resolve_turn_attachments(text: str, chat_files: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """Return (records, reused_context) for one chat turn."""
    payload = attachments_to_chat_payload(chat_files)
    reused = False
    if not payload and SESSION_ATTACHMENTS and ATTACHMENT_REF_RE.search(text or ""):
        payload = session_attachment_payload()[-3:]
        reused = bool(payload)
    if not payload:
        return [], False
    records = [_cached_process(a) for a in payload]
    if not reused:
        remember_attachments(payload)
    # Make the just-loaded image the active image_service image so /api/images
    # editing tools operate on the attachment without an extra load step.
    for r in reversed(records):
        if r.get("category") == "image" and not r.get("error"):
            try:
                image_service.load_image(str(WORKSPACE_ROOT / r["path"]))
            except Exception:
                pass
            break
    return records, reused
