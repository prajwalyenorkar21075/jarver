from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict
import time

logger = logging.getLogger("jarvis.cad.context")


@dataclass
class TupleTarget:
    feature_id: Optional[str]
    feature_name: Optional[str]
    is_ambiguous: bool
    candidates: list[dict]
    error_msg: Optional[str]


@dataclass
class CADContext:
    """
    Persistent conversational and operational CAD state.
    Maintains selection, active entities, active planes, history, and workspace.
    """
    selected_feature_id: Optional[str] = None
    selected_feature_name: Optional[str] = None
    last_created_id: Optional[str] = None
    last_created_name: Optional[str] = None
    active_sketch_id: Optional[str] = None
    active_feature_id: Optional[str] = None
    active_workplane: str = "XY"
    workplane_offset: float = 0.0
    coordinate_system: str = "WCS"  # WCS (World) or UCS (User)
    workspace: str = "model"       # sketch, model, assembly, drawing
    units: str = "mm"
    grid_snap: bool = True
    object_snap: bool = True
    ortho_mode: bool = False
    grid_size: float = 10.0
    section_view: bool = False
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "selected_feature_id": self.selected_feature_id,
            "selected_feature_name": self.selected_feature_name,
            "last_created_id": self.last_created_id,
            "last_created_name": self.last_created_name,
            "active_sketch_id": self.active_sketch_id,
            "active_feature_id": self.active_feature_id,
            "active_workplane": self.active_workplane,
            "workplane_offset": self.workplane_offset,
            "coordinate_system": self.coordinate_system,
            "workspace": self.workspace,
            "units": self.units,
            "grid_snap": self.grid_snap,
            "object_snap": self.object_snap,
            "ortho_mode": self.ortho_mode,
            "grid_size": self.grid_size,
            "section_view": self.section_view,
        }

    def update_from_dict(self, data: dict):
        if "selected_feature_id" in data:
            self.selected_feature_id = data["selected_feature_id"]
        if "selected_feature_name" in data:
            self.selected_feature_name = data["selected_feature_name"]
        if "active_sketch_id" in data:
            self.active_sketch_id = data["active_sketch_id"]
        if "active_workplane" in data:
            self.active_workplane = data["active_workplane"]
        if "coordinate_system" in data:
            self.coordinate_system = data["coordinate_system"]
        if "workspace" in data:
            self.workspace = data["workspace"]
        if "units" in data:
            self.units = data["units"]
        if "grid_snap" in data:
            self.grid_snap = bool(data["grid_snap"])
        if "object_snap" in data:
            self.object_snap = bool(data["object_snap"])
        if "section_view" in data:
            self.section_view = bool(data["section_view"])

    def record_created(self, feature_id: str, name: str):
        self.last_created_id = feature_id
        self.last_created_name = name
        self.selected_feature_id = feature_id
        self.selected_feature_name = name
        self.active_feature_id = feature_id

    def resolve_target(self, target_query: Optional[str], doc) -> TupleTarget:
        """
        Resolves a target reference from natural language against the current CAD state.
        
        Handles:
          - Anaphora: 'it', 'its', 'that', 'this', 'the selected object', 'selected'
          - Type mentions: 'the cylinder', 'box', 'sphere'
          - Specific ID or Name: 'Box-1', 'Cylinder'
          - Recency: 'the last one', 'the recent one'
        
        Returns:
          TupleTarget(feature_id, feature_name, is_ambiguous, candidates, error_msg)
        """
        if not doc or not doc.features:
            return TupleTarget(None, None, False, [], "The model document has no features.")

        q = (target_query or "").strip().lower()

        # 1. Pronoun / current selection reference
        if not q or q in ("it", "its", "that", "this", "selected", "the selected", "the selected object", "the part", "the model", "the object"):
            if self.selected_feature_id and self.selected_feature_id in doc.features:
                feat = doc.features[self.selected_feature_id]
                return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)
            
            if self.last_created_id and self.last_created_id in doc.features:
                feat = doc.features[self.last_created_id]
                return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)

            # If there's only 1 feature in the document, unambiguous!
            if len(doc.features) == 1:
                feat = next(iter(doc.features.values()))
                return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)

            # Multiple objects exist, but none is selected -> Ambiguity!
            candidates = [f.to_dict() for f in doc.features.values() if f.visible]
            return TupleTarget(
                None, None, True, candidates,
                f"Multiple objects exist in the model ({len(candidates)}). Please select or specify which object you want to target."
            )

        # 2. Type-based query: 'cylinder', 'the cylinder', 'box', 'sphere'
        type_keywords = ["box", "cylinder", "sphere", "cone", "torus", "sketch", "extrusion", "hole"]
        matched_type = None
        for tk in type_keywords:
            if tk in q:
                matched_type = tk
                break

        if matched_type:
            matching_features = []
            for feat in doc.features.values():
                params = feat.parameters or {}
                ptype = params.get("primitive_type", "").lower()
                fname = feat.name.lower()
                ftype = feat.feature_type.value.lower()
                if matched_type in ptype or matched_type in fname or matched_type in ftype:
                    matching_features.append(feat)

            # If currently selected feature matches the requested type, prefer it
            if self.selected_feature_id:
                for mf in matching_features:
                    if mf.id == self.selected_feature_id:
                        return TupleTarget(mf.id, mf.name, False, [mf.to_dict()], None)

            if len(matching_features) == 1:
                feat = matching_features[0]
                return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)
            elif len(matching_features) > 1:
                # Ambiguity! Multiple cylinders/boxes match!
                candidates = [f.to_dict() for f in matching_features]
                return TupleTarget(
                    None, None, True, candidates,
                    f"There are {len(matching_features)} {matched_type}s in the model. Please select or specify which {matched_type} you mean."
                )

        # 3. Search by name or ID match
        for feat in doc.features.values():
            if q in feat.id.lower() or q in feat.name.lower():
                return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)

        # 4. Fallback to selection or last created
        if self.selected_feature_id and self.selected_feature_id in doc.features:
            feat = doc.features[self.selected_feature_id]
            return TupleTarget(feat.id, feat.name, False, [feat.to_dict()], None)

        candidates = [f.to_dict() for f in doc.features.values()]
        return TupleTarget(
            None, None, True, candidates,
            f"Could not find object matching '{target_query}'. Please select the object in the viewport or model tree."
        )


# Global singleton persistent context
_global_cad_context = CADContext()


def get_cad_context() -> CADContext:
    return _global_cad_context
