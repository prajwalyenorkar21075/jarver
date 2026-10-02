"""CAD Document management with undo/redo and feature history."""
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger("jarvis.cad.document")


class FeatureType(Enum):
    """Types of CAD features."""
    SKETCH = "sketch"
    EXTRUDE = "extrude"
    REVOLVE = "revolve"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    UNION = "union"
    CUT = "cut"
    INTERSECT = "intersect"
    PRIMITIVE = "primitive"
    PATTERN = "pattern"
    SHELL = "shell"
    HOLE = "hole"
    MIRROR = "mirror"
    ARRAY = "array"
    LOFT = "loft"
    SWEEP = "sweep"
    TRANSFORM = "transform"


class FeatureStatus(Enum):
    """Feature computation status."""
    VALID = "valid"
    INVALID = "invalid"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class Feature:
    """A CAD feature in the model tree."""
    id: str
    name: str
    feature_type: FeatureType
    parameters: dict[str, Any]
    parent_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.VALID
    visible: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "parameters": self.parameters,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "status": self.status.value,
            "visible": self.visible,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Feature':
        return Feature(
            id=data["id"],
            name=data["name"],
            feature_type=FeatureType(data["feature_type"]),
            parameters=data["parameters"],
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            status=FeatureStatus(data.get("status", "valid")),
            visible=data.get("visible", True),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Command:
    """A command that can be undone/redone."""
    id: str
    name: str
    feature_id: str
    parameters: dict[str, Any]
    inverse_parameters: Optional[dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    undo_fn: Optional[Any] = None
    redo_fn: Optional[Any] = None


class CADDokument:
    """
    CAD Document - manages the complete CAD model with feature history.
    
    This is a real CAD document, not a mock. It uses CadQuery for geometry
    and maintains a full feature tree with undo/redo support.
    """

    def __init__(self, name: str = "Untitled"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.created_at = time.time()
        self.modified_at = time.time()
        
        self.features: dict[str, Feature] = {}
        self.feature_order: list[str] = []
        self.root_feature_ids: list[str] = []
        
        self.undo_stack: list[Command] = []
        self.redo_stack: list[Command] = []
        self.max_undo_levels = 100
        
        self._geometry_cache: dict[str, Any] = {}
        self._sketches: dict[str, Any] = {}
        self._dirty = True
        
        self.metadata: dict[str, Any] = {
            "units": "mm",
            "version": "1.0",
        }
        
        logger.info(f"[CAD] Created document: {name}")

    def add_feature(self, feature: Feature, parent_id: Optional[str] = None) -> str:
        """Add a feature to the document (undoable)."""
        self._apply_add_feature(feature, parent_id)

        geometry = self._geometry_cache.get(feature.id)

        def do_undo(f=feature, pid=parent_id):
            self._apply_remove_feature(f.id)

        def do_redo(f=feature, pid=parent_id, g=geometry):
            self._apply_add_feature(f, pid)
            if g is not None:
                self._geometry_cache[f.id] = g

        self.push_undo(Command(
            id=str(uuid.uuid4())[:8],
            name=f"Add {feature.name}",
            feature_id=feature.id,
            parameters=dict(feature.parameters),
            undo_fn=do_undo,
            redo_fn=do_redo,
        ))
        return feature.id

    def _apply_add_feature(self, feature: Feature, parent_id: Optional[str] = None) -> str:
        self.features[feature.id] = feature

        if parent_id:
            feature.parent_id = parent_id
            if parent_id in self.features:
                self.features[parent_id].children_ids.append(feature.id)
        else:
            if feature.id not in self.root_feature_ids:
                self.root_feature_ids.append(feature.id)

        if feature.id not in self.feature_order:
            self.feature_order.append(feature.id)

        self._dirty = True
        self.modified_at = time.time()

        logger.info(f"[CAD] Added feature: {feature.name} ({feature.feature_type.value})")
        return feature.id

    def add_sketch(self, sketch) -> str:
        """Register a 2D sketch so feature operations can reference it by id."""
        self._sketches[sketch.id] = sketch
        self._dirty = True
        self.modified_at = time.time()
        return sketch.id

    def get_sketch(self, sketch_id: str):
        return self._sketches.get(sketch_id)

    def list_sketches(self) -> list:
        return list(self._sketches.values())

    def remove_feature(self, feature_id: str) -> bool:
        """Remove a feature and its children (undoable)."""
        if feature_id not in self.features:
            return False

        subtree = self._collect_subtree(feature_id)
        feature_name = subtree[0][0].name if subtree else feature_id

        self._apply_remove_feature(feature_id)

        def do_undo(items=subtree):
            for f, parent_id, geom in items:
                self._apply_add_feature(f, parent_id)
                if geom is not None:
                    self._geometry_cache[f.id] = geom

        def do_redo(fid=feature_id):
            self._apply_remove_feature(fid)

        self.push_undo(Command(
            id=str(uuid.uuid4())[:8],
            name=f"Remove {feature_name}",
            feature_id=feature_id,
            parameters={},
            undo_fn=do_undo,
            redo_fn=do_redo,
        ))
        return True

    def _collect_subtree(self, feature_id: str) -> list:
        """Collect (feature, parent_id, geometry) for a feature and its descendants."""
        items = []
        feature = self.features.get(feature_id)
        if not feature:
            return items
        items.append((feature, feature.parent_id, self._geometry_cache.get(feature.id)))
        for child_id in feature.children_ids:
            items.extend(self._collect_subtree(child_id))
        return items

    def _apply_remove_feature(self, feature_id: str) -> bool:
        """Remove a feature and its children without touching the undo stack."""
        if feature_id not in self.features:
            return False

        feature = self.features[feature_id]

        for child_id in feature.children_ids[:]:
            self._apply_remove_feature(child_id)

        if feature.parent_id and feature.parent_id in self.features:
            parent = self.features[feature.parent_id]
            if feature_id in parent.children_ids:
                parent.children_ids.remove(feature_id)

        if feature_id in self.root_feature_ids:
            self.root_feature_ids.remove(feature_id)

        if feature_id in self.feature_order:
            self.feature_order.remove(feature_id)

        del self.features[feature_id]

        if feature_id in self._geometry_cache:
            del self._geometry_cache[feature_id]

        self._dirty = True
        self.modified_at = time.time()

        logger.info(f"[CAD] Removed feature: {feature.name}")
        return True

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID."""
        return self.features.get(feature_id)

    def update_feature_parameters(self, feature_id: str, parameters: dict[str, Any]) -> bool:
        """Update feature parameters."""
        if feature_id not in self.features:
            return False
        
        self.features[feature_id].parameters.update(parameters)
        self.features[feature_id].status = FeatureStatus.PENDING
        self._dirty = True
        self.modified_at = time.time()
        
        logger.info(f"[CAD] Updated parameters for: {self.features[feature_id].name}")
        return True

    def set_feature_visibility(self, feature_id: str, visible: bool) -> bool:
        """Set feature visibility."""
        if feature_id not in self.features:
            return False
        
        self.features[feature_id].visible = visible
        self._dirty = True
        return True

    def rename_feature(self, feature_id: str, new_name: str) -> bool:
        """Rename a feature."""
        if feature_id not in self.features:
            return False
        
        self.features[feature_id].name = new_name
        self.modified_at = time.time()
        return True

    def reorder_features(self, feature_id: str, new_index: int) -> bool:
        """Reorder a feature in the tree (where safe)."""
        if feature_id not in self.feature_order:
            return False
        
        old_index = self.feature_order.index(feature_id)
        
        if new_index < 0 or new_index >= len(self.feature_order):
            return False
        
        self.feature_order.pop(old_index)
        self.feature_order.insert(new_index, feature_id)
        self._dirty = True
        
        return True

    def push_undo(self, command: Command):
        """Push a command to the undo stack."""
        self.undo_stack.append(command)
        
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)
        
        self.redo_stack.clear()

    def undo(self) -> Optional[Command]:
        """Undo the last command, applying its inverse to the model."""
        if not self.undo_stack:
            return None
        
        command = self.undo_stack.pop()
        if command.undo_fn is not None:
            command.undo_fn()
        self.redo_stack.append(command)
        
        logger.info(f"[CAD] Undo: {command.name}")
        return command

    def redo(self) -> Optional[Command]:
        """Redo the last undone command, re-applying it to the model."""
        if not self.redo_stack:
            return None
        
        command = self.redo_stack.pop()
        if command.redo_fn is not None:
            command.redo_fn()
        self.undo_stack.append(command)
        
        logger.info(f"[CAD] Redo: {command.name}")
        return command

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def get_model_tree(self) -> dict:
        """Get the complete model tree structure."""
        def build_tree(feature_id: str) -> dict:
            feature = self.features[feature_id]
            return {
                "id": feature.id,
                "name": feature.name,
                "type": feature.feature_type.value,
                "status": feature.status.value,
                "visible": feature.visible,
                "children": [build_tree(cid) for cid in feature.children_ids],
            }
        
        return {
            "id": self.id,
            "name": self.name,
            "roots": [build_tree(fid) for fid in self.root_feature_ids],
        }

    def get_all_features(self) -> list[dict]:
        """Get all features as a list."""
        return [f.to_dict() for f in self.features.values()]

    def get_bounding_box(self) -> Optional[dict]:
        """Get the bounding box of the entire model."""
        from app.cad_engine.core.geometry import BoundingBox, Point3D
        
        if not self._geometry_cache:
            return None
        
        all_boxes = []
        for geom in self._geometry_cache.values():
            if hasattr(geom, 'val') and hasattr(geom.val(), 'BoundingBox'):
                bbox = geom.val().BoundingBox()
                all_boxes.append((bbox.xmin, bbox.ymin, bbox.zmin, bbox.xmax, bbox.ymax, bbox.zmax))
        
        if not all_boxes:
            return None
        
        min_x = min(b[0] for b in all_boxes)
        min_y = min(b[1] for b in all_boxes)
        min_z = min(b[2] for b in all_boxes)
        max_x = max(b[3] for b in all_boxes)
        max_y = max(b[4] for b in all_boxes)
        max_z = max(b[5] for b in all_boxes)
        
        return {
            "min": {"x": min_x, "y": min_y, "z": min_z},
            "max": {"x": max_x, "y": max_y, "z": max_z},
            "width": max_x - min_x,
            "height": max_y - min_y,
            "depth": max_z - min_z,
        }

    def to_dict(self) -> dict:
        """Serialize document to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "features": {fid: f.to_dict() for fid, f in self.features.items()},
            "feature_order": self.feature_order,
            "root_feature_ids": self.root_feature_ids,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> 'CADDokument':
        """Deserialize document from dictionary."""
        doc = CADDokument(data["name"])
        doc.id = data["id"]
        doc.created_at = data["created_at"]
        doc.modified_at = data["modified_at"]
        doc.features = {fid: Feature.from_dict(fdata) for fid, fdata in data["features"].items()}
        doc.feature_order = data["feature_order"]
        doc.root_feature_ids = data["root_feature_ids"]
        doc.metadata = data.get("metadata", {})
        return doc


_active_document: Optional[CADDokument] = None


def get_active_document() -> CADDokument:
    """Get the currently active CAD document."""
    global _active_document
    if _active_document is None:
        _active_document = CADDokument("Default")
    return _active_document


def set_active_document(doc: CADDokument):
    """Set the active CAD document."""
    global _active_document
    _active_document = doc
    logger.info(f"[CAD] Active document set: {doc.name}")


def new_document(name: str = "Untitled") -> CADDokument:
    """Create a new document and set it as active."""
    doc = CADDokument(name)
    set_active_document(doc)
    return doc
