"""Image reading and processing service for JARVIS."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger("jarvis.image_service")


class ImageService:
    """Handles image reading, analysis, and editing operations."""

    def __init__(self):
        self.current_image: Optional[Image.Image] = None
        self.current_image_path: Optional[str] = None
        self.image_history: list[Image.Image] = []
        self.history_index: int = -1

    def load_image(self, image_path: str) -> dict:
        """Load an image from file path."""
        try:
            path = Path(image_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {image_path}"}

            img = Image.open(path)
            self.current_image = img.copy()
            self.current_image_path = str(path)
            self.image_history = [img.copy()]
            self.history_index = 0

            return {
                "success": True,
                "path": str(path),
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format or path.suffix[1:].upper(),
                "size_bytes": path.stat().st_size,
            }
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return {"success": False, "error": str(e)}

    def load_image_from_base64(self, base64_data: str) -> dict:
        """Load an image from base64 encoded data."""
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]

            image_bytes = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(image_bytes))
            self.current_image = img.copy()
            self.current_image_path = None
            self.image_history = [img.copy()]
            self.history_index = 0

            return {
                "success": True,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": img.format or "UNKNOWN",
            }
        except Exception as e:
            logger.error(f"Failed to load image from base64: {e}")
            return {"success": False, "error": str(e)}

    def get_image_info(self) -> dict:
        """Get information about the current image."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        img = self.current_image
        info = {
            "success": True,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "format": img.format,
            "channels": len(img.getbands()),
        }

        if self.current_image_path:
            path = Path(self.current_image_path)
            info["path"] = str(path)
            info["size_bytes"] = path.stat().st_size
            info["filename"] = path.name

        return info

    def get_image_as_base64(self, format: str = "PNG") -> dict:
        """Get current image as base64 encoded string."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            buffer = io.BytesIO()
            self.current_image.save(buffer, format=format)
            buffer.seek(0)
            base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            mime_type = f"image/{format.lower()}"
            return {
                "success": True,
                "data": f"data:{mime_type};base64,{base64_data}",
                "format": format,
            }
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return {"success": False, "error": str(e)}

    def save_image(self, output_path: str, format: Optional[str] = None) -> dict:
        """Save the current image to a file."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            path = Path(output_path)
            if format is None:
                format = path.suffix[1:].upper() if path.suffix else "PNG"

            self.current_image.save(path, format=format)

            return {
                "success": True,
                "path": str(path),
                "format": format,
                "size_bytes": path.stat().st_size,
            }
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return {"success": False, "error": str(e)}

    def _save_to_history(self):
        """Save current state to history for undo support."""
        if not self.current_image:
            return

        # Remove any future states if we're not at the end
        if self.history_index < len(self.image_history) - 1:
            self.image_history = self.image_history[: self.history_index + 1]

        self.image_history.append(self.current_image.copy())
        self.history_index = len(self.image_history) - 1

        # Limit history size
        if len(self.image_history) > 20:
            self.image_history.pop(0)
            self.history_index -= 1

    def undo(self) -> dict:
        """Undo the last edit operation."""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_image = self.image_history[self.history_index].copy()
            return {"success": True, "message": "Undo successful"}
        return {"success": False, "error": "Nothing to undo"}

    def redo(self) -> dict:
        """Redo the last undone operation."""
        if self.history_index < len(self.image_history) - 1:
            self.history_index += 1
            self.current_image = self.image_history[self.history_index].copy()
            return {"success": True, "message": "Redo successful"}
        return {"success": False, "error": "Nothing to redo"}

    def resize(self, width: int, height: int, maintain_aspect: bool = True) -> dict:
        """Resize the current image."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            if maintain_aspect:
                self.current_image.thumbnail((width, height), Image.Resampling.LANCZOS)
            else:
                self.current_image = self.current_image.resize(
                    (width, height), Image.Resampling.LANCZOS
                )

            self._save_to_history()

            return {
                "success": True,
                "width": self.current_image.width,
                "height": self.current_image.height,
            }
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return {"success": False, "error": str(e)}

    def crop(self, left: int, top: int, right: int, bottom: int) -> dict:
        """Crop the current image."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            self.current_image = self.current_image.crop((left, top, right, bottom))
            self._save_to_history()

            return {
                "success": True,
                "width": self.current_image.width,
                "height": self.current_image.height,
            }
        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            return {"success": False, "error": str(e)}

    def rotate(self, angle: float, expand: bool = True) -> dict:
        """Rotate the current image."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            self.current_image = self.current_image.rotate(angle, expand=expand)
            self._save_to_history()

            return {
                "success": True,
                "width": self.current_image.width,
                "height": self.current_image.height,
            }
        except Exception as e:
            logger.error(f"Failed to rotate image: {e}")
            return {"success": False, "error": str(e)}

    def apply_filter(self, filter_name: str) -> dict:
        """Apply a filter to the current image."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            filters = {
                "blur": ImageFilter.BLUR,
                "contour": ImageFilter.CONTOUR,
                "detail": ImageFilter.DETAIL,
                "edge_enhance": ImageFilter.EDGE_ENHANCE,
                "edge_enhance_more": ImageFilter.EDGE_ENHANCE_MORE,
                "emboss": ImageFilter.EMBOSS,
                "find_edges": ImageFilter.FIND_EDGES,
                "sharpen": ImageFilter.SHARPEN,
                "smooth": ImageFilter.SMOOTH,
                "smooth_more": ImageFilter.SMOOTH_MORE,
            }

            if filter_name not in filters:
                return {"success": False, "error": f"Unknown filter: {filter_name}"}

            self.current_image = self.current_image.filter(filters[filter_name])
            self._save_to_history()

            return {"success": True, "filter": filter_name}
        except Exception as e:
            logger.error(f"Failed to apply filter: {e}")
            return {"success": False, "error": str(e)}

    def adjust_brightness(self, factor: float) -> dict:
        """Adjust image brightness (0.0 to 2.0, 1.0 is original)."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            enhancer = ImageEnhance.Brightness(self.current_image)
            self.current_image = enhancer.enhance(factor)
            self._save_to_history()

            return {"success": True, "brightness": factor}
        except Exception as e:
            logger.error(f"Failed to adjust brightness: {e}")
            return {"success": False, "error": str(e)}

    def adjust_contrast(self, factor: float) -> dict:
        """Adjust image contrast (0.0 to 2.0, 1.0 is original)."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            enhancer = ImageEnhance.Contrast(self.current_image)
            self.current_image = enhancer.enhance(factor)
            self._save_to_history()

            return {"success": True, "contrast": factor}
        except Exception as e:
            logger.error(f"Failed to adjust contrast: {e}")
            return {"success": False, "error": str(e)}

    def convert_to_grayscale(self) -> dict:
        """Convert image to grayscale."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            self.current_image = ImageOps.grayscale(self.current_image)
            self._save_to_history()

            return {"success": True, "mode": "L"}
        except Exception as e:
            logger.error(f"Failed to convert to grayscale: {e}")
            return {"success": False, "error": str(e)}

    def flip_horizontal(self) -> dict:
        """Flip image horizontally."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            self.current_image = ImageOps.mirror(self.current_image)
            self._save_to_history()

            return {"success": True, "operation": "flip_horizontal"}
        except Exception as e:
            logger.error(f"Failed to flip image: {e}")
            return {"success": False, "error": str(e)}

    def flip_vertical(self) -> dict:
        """Flip image vertically."""
        if not self.current_image:
            return {"success": False, "error": "No image loaded"}

        try:
            self.current_image = ImageOps.flip(self.current_image)
            self._save_to_history()

            return {"success": True, "operation": "flip_vertical"}
        except Exception as e:
            logger.error(f"Failed to flip image: {e}")
            return {"success": False, "error": str(e)}


# Global instance
image_service = ImageService()
