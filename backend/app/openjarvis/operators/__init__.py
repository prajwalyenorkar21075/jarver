"""Operators -- persistent, scheduled autonomous agents.

Ported from OpenJarvis (Stanford Hazy Research / Scaling Intelligence Lab).
Adapted for JARVIS backend integration.
"""

from app.openjarvis.operators.loader import load_operator
from app.openjarvis.operators.manager import OperatorManager
from app.openjarvis.operators.types import OperatorManifest

__all__ = ["OperatorManifest", "OperatorManager", "load_operator"]
