"""
JARVIS CAD Engine - Real CAD functionality using CadQuery/OpenCASCADE.

This is a production CAD engine, not a mock or demo.
"""

from app.cad_engine.core.document import CADDokument, get_active_document
from app.cad_engine.core.geometry import (
    Point2D, Point3D, Vector2D, Vector3D,
    BoundingBox, Transformation
)

__all__ = [
    'CADDokument',
    'get_active_document',
    'Point2D',
    'Point3D',
    'Vector2D',
    'Vector3D',
    'BoundingBox',
    'Transformation',
]
