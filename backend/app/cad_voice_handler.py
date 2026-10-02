"""CAD voice command handler for JARVIS.

Processes CAD-specific voice commands and routes them to the CAD API.
Supports natural language commands for creating primitives, performing
operations, and navigating the CAD viewport.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("jarvis.cad_voice")


class CADCommandHandler:
    """Handles CAD-specific voice commands."""

    def __init__(self):
        self.primitive_patterns = {
            "box": r"\b(box|cube|rectangular)\b",
            "cylinder": r"\b(cylinder|cylindrical|tube|pipe)\b",
            "sphere": r"\b(sphere|ball|spherical)\b",
            "cone": r"\b(cone|conical|pyramid)\b",
            "torus": r"\b(torus|donut|ring|toroidal)\b",
        }

        self.operation_patterns = {
            "extrude": r"\b(extrude|push|pull)\b",
            "revolve": r"\b(revolve|rotate|spin)\b",
            "cut": r"\b(cut|subtract|remove)\b",
            "union": r"\b(union|combine|merge|join)\b",
            "fillet": r"\b(fillet|round|smooth)\b",
            "chamfer": r"\b(chamfer|bevel|angle)\b",
            "shell": r"\b(shell|hollow|thin)\b",
        }

        self.navigation_patterns = {
            "open_cad": r"\b(open|show|display|launch)\b.*\b(cad|3d|viewport|model)\b",
            "zoom": r"\b(zoom)\b.*\b(in|out|extents)\b",
            "fit": r"\b(fit|frame|center)\b.*\b(view|model|object)\b",
        }

    def parse_cad_command(self, text: str) -> Optional[dict]:
        """Parse a CAD voice command and return action details."""
        text_lower = text.lower().strip()

        # Check for primitive creation
        for primitive_type, pattern in self.primitive_patterns.items():
            if re.search(pattern, text_lower):
                dimensions = self._extract_dimensions(text_lower)
                return {
                    "action": "create_primitive",
                    "primitive_type": primitive_type,
                    "dimensions": dimensions,
                    "raw_command": text,
                }

        # Check for operations
        for operation, pattern in self.operation_patterns.items():
            if re.search(pattern, text_lower):
                parameters = self._extract_operation_params(text_lower, operation)
                return {
                    "action": "perform_operation",
                    "operation": operation,
                    "parameters": parameters,
                    "raw_command": text,
                }

        # Check for navigation
        for nav_action, pattern in self.navigation_patterns.items():
            if re.search(pattern, text_lower):
                return {
                    "action": "navigate",
                    "navigation": nav_action,
                    "raw_command": text,
                }

        return None

    def _extract_dimensions(self, text: str) -> dict:
        """Extract dimension values from command text."""
        dimensions = {}

        # Look for patterns like "10 by 20 by 30" or "10x20x30"
        dim_pattern = r"(\d+(?:\.\d+)?)\s*(?:by|x|\*)\s*(\d+(?:\.\d+)?)\s*(?:by|x|\*)\s*(\d+(?:\.\d+)?)"
        match = re.search(dim_pattern, text)
        if match:
            dimensions["width"] = float(match.group(1))
            dimensions["height"] = float(match.group(2))
            dimensions["depth"] = float(match.group(3))
            return dimensions

        # Look for single dimension like "radius 5" or "height 10"
        radius_pattern = r"\b(?:radius|r)\s+(\d+(?:\.\d+)?)"
        match = re.search(radius_pattern, text)
        if match:
            dimensions["radius"] = float(match.group(1))

        height_pattern = r"\b(?:height|h)\s+(\d+(?:\.\d+)?)"
        match = re.search(height_pattern, text)
        if match:
            dimensions["height"] = float(match.group(1))

        width_pattern = r"\b(?:width|w)\s+(\d+(?:\.\d+)?)"
        match = re.search(width_pattern, text)
        if match:
            dimensions["width"] = float(match.group(1))

        return dimensions

    def _extract_operation_params(self, text: str, operation: str) -> dict:
        """Extract operation-specific parameters."""
        params = {}

        # Extract distance/radius for fillet/chamfer
        distance_pattern = r"\b(?:distance|radius|r)\s+(\d+(?:\.\d+)?)"
        match = re.search(distance_pattern, text)
        if match:
            params["distance"] = float(match.group(1))

        # Extract angle for revolve/chamfer
        angle_pattern = r"\b(?:angle|degrees?)\s+(\d+(?:\.\d+)?)"
        match = re.search(angle_pattern, text)
        if match:
            params["angle"] = float(match.group(1))

        return params

    def generate_response(self, command: dict) -> str:
        """Generate a human-readable response for a CAD command."""
        action = command.get("action")

        if action == "create_primitive":
            prim_type = command.get("primitive_type", "unknown")
            dims = command.get("dimensions", {})
            if dims:
                dim_str = ", ".join([f"{k}={v}" for k, v in dims.items()])
                return f"Creating {prim_type} with {dim_str}"
            return f"Creating {prim_type} with default dimensions"

        elif action == "perform_operation":
            operation = command.get("operation", "unknown")
            return f"Performing {operation} operation"

        elif action == "navigate":
            nav = command.get("navigation", "unknown")
            return f"Opening CAD viewport"

        return "Processing CAD command"


# Global instance
cad_command_handler = CADCommandHandler()
