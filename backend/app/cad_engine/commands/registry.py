"""CAD Function Registry with validation, execution, and verification."""
import logging
import uuid
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field

from app.cad_engine.core.document import Feature, FeatureType, get_active_document
from app.cad_engine.features.modeling import CADModelingOperations
from app.cad_engine.core.measurement import CADMeasurement
from app.cad_engine.io.file_io import CADFileIO
from app.cad_engine.sketches.sketch import Sketch, ConstraintType

logger = logging.getLogger("jarvis.cad.registry")


@dataclass
class CADFunction:
    """An executable CAD capability."""
    name: str
    category: str
    description: str
    parameters_schema: dict
    handler: Callable[..., Any]
    validator: Optional[Callable[[dict, Any, Any], tuple[bool, Optional[str]]]] = None
    verifier: Optional[Callable[[dict, dict, Any], tuple[bool, Optional[str]]]] = None


class CADFunctionRegistry:
    """Central registry of executable CAD functions."""

    def __init__(self):
        self._functions: dict[str, CADFunction] = {}
        self._register_all_builtins()

    def register(self, fn: CADFunction):
        self._functions[fn.name.upper()] = fn

    def get(self, name: str) -> Optional[CADFunction]:
        return self._functions.get(name.upper())

    def list_functions(self) -> list[dict]:
        return [
            {
                "name": fn.name,
                "category": fn.category,
                "description": fn.description,
                "parameters_schema": fn.parameters_schema,
            }
            for fn in self._functions.values()
        ]

    def _register_all_builtins(self):
        # 1. 3D Primitives
        self.register(CADFunction(
            name="CREATE_BOX",
            category="primitives",
            description="Create a rectangular solid with width, height, depth in mm.",
            parameters_schema={
                "width": {"type": "float", "default": 100.0, "unit": "mm"},
                "height": {"type": "float", "default": 50.0, "unit": "mm"},
                "depth": {"type": "float", "default": 20.0, "unit": "mm"},
                "name": {"type": "string", "default": "Box"},
            },
            validator=lambda p, ctx, doc: (
                True if p.get("width", 0) > 0 and p.get("height", 0) > 0 and p.get("depth", 0) > 0
                else (False, "Box width, height, and depth must all be positive numbers.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_box(
                width=float(p.get("width", 100.0)),
                height=float(p.get("height", 50.0)),
                depth=float(p.get("depth", 20.0)),
                name=p.get("name", "Box")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and getattr(res, "id", None) in doc.features
                else (False, "Feature verification failed: Box not registered in active document.")
            )
        ))

        self.register(CADFunction(
            name="CREATE_CYLINDER",
            category="primitives",
            description="Create a cylinder solid with radius and height in mm.",
            parameters_schema={
                "radius": {"type": "float", "default": 20.0, "unit": "mm"},
                "height": {"type": "float", "default": 60.0, "unit": "mm"},
                "name": {"type": "string", "default": "Cylinder"},
            },
            validator=lambda p, ctx, doc: (
                True if p.get("radius", 0) > 0 and p.get("height", 0) > 0
                else (False, "Cylinder radius and height must be positive numbers.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_cylinder(
                radius=float(p.get("radius", 20.0)),
                height=float(p.get("height", 60.0)),
                name=p.get("name", "Cylinder")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and getattr(res, "id", None) in doc.features
                else (False, "Feature verification failed: Cylinder not found in document.")
            )
        ))

        self.register(CADFunction(
            name="CREATE_SPHERE",
            category="primitives",
            description="Create a sphere solid with radius in mm.",
            parameters_schema={
                "radius": {"type": "float", "default": 25.0, "unit": "mm"},
                "name": {"type": "string", "default": "Sphere"},
            },
            validator=lambda p, ctx, doc: (
                True if p.get("radius", 0) > 0 else (False, "Sphere radius must be positive.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_sphere(
                radius=float(p.get("radius", 25.0)),
                name=p.get("name", "Sphere")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and getattr(res, "id", None) in doc.features
                else (False, "Feature verification failed: Sphere not in document.")
            )
        ))

        self.register(CADFunction(
            name="CREATE_CONE",
            category="primitives",
            description="Create a cone solid with radius and height in mm.",
            parameters_schema={
                "radius": {"type": "float", "default": 20.0, "unit": "mm"},
                "height": {"type": "float", "default": 40.0, "unit": "mm"},
                "name": {"type": "string", "default": "Cone"},
            },
            validator=lambda p, ctx, doc: (
                True if p.get("radius", 0) > 0 and p.get("height", 0) > 0
                else (False, "Cone radius and height must be positive.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_cone(
                radius=float(p.get("radius", 20.0)),
                height=float(p.get("height", 40.0)),
                name=p.get("name", "Cone")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and getattr(res, "id", None) in doc.features
                else (False, "Feature verification failed: Cone not in document.")
            )
        ))

        self.register(CADFunction(
            name="CREATE_TORUS",
            category="primitives",
            description="Create a torus solid with major and minor radius in mm.",
            parameters_schema={
                "major_radius": {"type": "float", "default": 30.0, "unit": "mm"},
                "minor_radius": {"type": "float", "default": 6.0, "unit": "mm"},
                "name": {"type": "string", "default": "Torus"},
            },
            validator=lambda p, ctx, doc: (
                True if p.get("major_radius", 0) > p.get("minor_radius", 0) > 0
                else (False, "Torus major radius must be greater than minor radius.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_torus(
                major_radius=float(p.get("major_radius", 30.0)),
                minor_radius=float(p.get("minor_radius", 6.0)),
                name=p.get("name", "Torus")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and getattr(res, "id", None) in doc.features
                else (False, "Feature verification failed: Torus not in document.")
            )
        ))

        # 2. Holes & Machining
        self.register(CADFunction(
            name="CREATE_HOLE",
            category="features",
            description="Make a hole on a face of the target solid.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "diameter": {"type": "float", "default": 10.0, "unit": "mm"},
                "depth": {"type": "float", "default": None, "unit": "mm"},
                "x": {"type": "float", "default": 0.0, "unit": "mm"},
                "y": {"type": "float", "default": 0.0, "unit": "mm"},
                "face_selector": {"type": "string", "default": ">Z"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and p.get("diameter", 0) > 0
                else (False, "A valid feature_id and positive hole diameter are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.create_hole(
                feature_id=p["feature_id"],
                diameter=float(p.get("diameter", 10.0)),
                depth=p.get("depth"),
                x=float(p.get("x", 0.0)),
                y=float(p.get("y", 0.0)),
                face_selector=p.get("face_selector", ">Z"),
                name=p.get("name", f"Hole_{int(p.get('diameter', 10))}mm")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Hole feature could not be verified in the document.")
            )
        ))

        # 3. Sketch Features (Extrude, Revolve)
        self.register(CADFunction(
            name="EXTRUDE",
            category="features",
            description="Extrude a 2D sketch profile into a 3D solid.",
            parameters_schema={
                "sketch_id": {"type": "string", "required": True},
                "distance": {"type": "float", "default": 25.0, "unit": "mm"},
                "name": {"type": "string", "default": "Extrusion"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("sketch_id") and p.get("distance", 0) != 0
                else (False, "A valid sketch_id and non-zero extrusion distance are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.extrude_sketch(
                sketch=doc.get_sketch(p["sketch_id"]),
                distance=float(p.get("distance", 25.0)),
                name=p.get("name", "Extrusion")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Extrusion verification failed.")
            )
        ))

        self.register(CADFunction(
            name="REVOLVE",
            category="features",
            description="Revolve a sketch profile around an axis.",
            parameters_schema={
                "sketch_id": {"type": "string", "required": True},
                "angle": {"type": "float", "default": 360.0, "unit": "deg"},
                "name": {"type": "string", "default": "Revolution"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("sketch_id") and p.get("angle", 0) != 0
                else (False, "A valid sketch_id and non-zero revolution angle are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.revolve_sketch(
                sketch=doc.get_sketch(p["sketch_id"]),
                angle=float(p.get("angle", 360.0)),
                name=p.get("name", "Revolution")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Revolve verification failed.")
            )
        ))

        # 4. Modifiers (Fillet, Chamfer, Shell)
        self.register(CADFunction(
            name="FILLET",
            category="modifiers",
            description="Apply rounded fillet to edges of a solid.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "radius": {"type": "float", "default": 3.0, "unit": "mm"},
                "edge_selector": {"type": "string", "default": None},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and p.get("radius", 0) > 0
                else (False, "A valid feature_id and positive fillet radius are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.fillet(
                feature_id=p["feature_id"],
                radius=float(p.get("radius", 3.0)),
                edge_selector=p.get("edge_selector"),
                name=p.get("name", f"Fillet_r{p.get('radius', 3)}")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Fillet verification failed.")
            )
        ))

        self.register(CADFunction(
            name="CHAMFER",
            category="modifiers",
            description="Apply beveled chamfer to edges of a solid.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "distance": {"type": "float", "default": 2.0, "unit": "mm"},
                "edge_selector": {"type": "string", "default": None},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and p.get("distance", 0) > 0
                else (False, "A valid feature_id and positive chamfer distance are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.chamfer(
                feature_id=p["feature_id"],
                distance=float(p.get("distance", 2.0)),
                edge_selector=p.get("edge_selector"),
                name=p.get("name", f"Chamfer_d{p.get('distance', 2)}")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Chamfer verification failed.")
            )
        ))

        self.register(CADFunction(
            name="SHELL",
            category="modifiers",
            description="Hollow out a solid leaving a specified wall thickness.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "thickness": {"type": "float", "default": 2.0, "unit": "mm"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and p.get("thickness", 0) > 0
                else (False, "A valid feature_id and positive shell thickness are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.shell(
                feature_id=p["feature_id"],
                thickness=float(p.get("thickness", 2.0)),
                name=p.get("name", f"Shell_t{p.get('thickness', 2)}")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Shell verification failed.")
            )
        ))

        # 5. Booleans (Union, Cut, Intersect)
        self.register(CADFunction(
            name="BOOLEAN_UNION",
            category="booleans",
            description="Merge two solid bodies into one.",
            parameters_schema={
                "feature_id1": {"type": "string", "required": True},
                "feature_id2": {"type": "string", "required": True},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id1") and p.get("feature_id2")
                else (False, "Two feature IDs are required for a Boolean Union.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.boolean_union(
                feature_id1=p["feature_id1"],
                feature_id2=p["feature_id2"],
                name=p.get("name", "Union")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Boolean union failed.")
            )
        ))

        self.register(CADFunction(
            name="BOOLEAN_CUT",
            category="booleans",
            description="Subtract tool solid from base solid.",
            parameters_schema={
                "base_id": {"type": "string", "required": True},
                "tool_id": {"type": "string", "required": True},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("base_id") and p.get("tool_id")
                else (False, "Both base_id and tool_id are required for Boolean Cut.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.boolean_cut(
                feature_id1=p["base_id"],
                feature_id2=p["tool_id"],
                name=p.get("name", "Cut")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Boolean cut failed.")
            )
        ))

        self.register(CADFunction(
            name="BOOLEAN_INTERSECT",
            category="booleans",
            description="Keep only the intersecting volume of two solids.",
            parameters_schema={
                "feature_id1": {"type": "string", "required": True},
                "feature_id2": {"type": "string", "required": True},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id1") and p.get("feature_id2")
                else (False, "Two features are required for intersection.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.boolean_intersect(
                feature_id1=p["feature_id1"],
                feature_id2=p["feature_id2"],
                name=p.get("name", "Intersect")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Boolean intersect failed.")
            )
        ))

        # 6. Patterns & Arrays
        self.register(CADFunction(
            name="PATTERN_CIRCULAR",
            category="patterns",
            description="Create polar array of solid copies or holes.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "count": {"type": "integer", "default": 6},
                "angle": {"type": "float", "default": 360.0, "unit": "deg"},
                "radius": {"type": "float", "default": 0.0, "unit": "mm"},
                "hole_diameter": {"type": "float", "default": None, "unit": "mm"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and int(p.get("count", 0)) > 1
                else (False, "feature_id and count >= 2 are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.pattern_circular(
                feature_id=p["feature_id"],
                count=int(p.get("count", 6)),
                angle=float(p.get("angle", 360.0)),
                radius=float(p.get("radius", 0.0)),
                hole_diameter=p.get("hole_diameter"),
                name=p.get("name", f"CircularPattern_{p.get('count', 6)}x")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Circular pattern verification failed.")
            )
        ))

        self.register(CADFunction(
            name="PATTERN_LINEAR",
            category="patterns",
            description="Create linear rectangular array of solid copies or holes.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "count_x": {"type": "integer", "default": 2},
                "count_y": {"type": "integer", "default": 1},
                "spacing_x": {"type": "float", "default": 20.0, "unit": "mm"},
                "spacing_y": {"type": "float", "default": 20.0, "unit": "mm"},
                "hole_diameter": {"type": "float", "default": None, "unit": "mm"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id")
                else (False, "feature_id is required for linear pattern.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.pattern_linear(
                feature_id=p["feature_id"],
                count_x=int(p.get("count_x", 2)),
                count_y=int(p.get("count_y", 1)),
                spacing_x=float(p.get("spacing_x", 20.0)),
                spacing_y=float(p.get("spacing_y", 20.0)),
                hole_diameter=p.get("hole_diameter"),
                name=p.get("name", "LinearPattern")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Linear pattern verification failed.")
            )
        ))

        self.register(CADFunction(
            name="MIRROR",
            category="patterns",
            description="Mirror a feature across XY, XZ, or YZ plane.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "plane": {"type": "string", "default": "XY"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and p.get("plane") in ("XY", "XZ", "YZ")
                else (False, "A valid feature_id and plane (XY, XZ, YZ) are required.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.mirror(
                feature_id=p["feature_id"],
                plane=p.get("plane", "XY"),
                name=p.get("name", f"Mirror_{p.get('plane', 'XY')}")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Mirror verification failed.")
            )
        ))

        # 7. Transformations (Move, Rotate, Scale)
        self.register(CADFunction(
            name="TRANSFORM_MOVE",
            category="transform",
            description="Translate a feature along X, Y, or Z axis in mm.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "x": {"type": "float", "default": 0.0, "unit": "mm"},
                "y": {"type": "float", "default": 0.0, "unit": "mm"},
                "z": {"type": "float", "default": 0.0, "unit": "mm"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id")
                else (False, "feature_id is required to move an object.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.transform_feature(
                feature_id=p["feature_id"],
                translation=(float(p.get("x", 0.0)), float(p.get("y", 0.0)), float(p.get("z", 0.0))),
                name=p.get("name", "Moved")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Move verification failed.")
            )
        ))

        self.register(CADFunction(
            name="TRANSFORM_ROTATE",
            category="transform",
            description="Rotate a feature around an axis in degrees.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "angle": {"type": "float", "default": 45.0, "unit": "deg"},
                "axis": {"type": "string", "default": "y"},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id")
                else (False, "feature_id is required to rotate an object.")
            ),
            handler=lambda p, ctx, doc: CADModelingOperations.transform_feature(
                feature_id=p["feature_id"],
                rotation=(
                    float(p.get("angle", 0.0)) if p.get("axis", "y").lower() == "x" else 0.0,
                    float(p.get("angle", 0.0)) if p.get("axis", "y").lower() == "y" else 0.0,
                    float(p.get("angle", 0.0)) if p.get("axis", "y").lower() == "z" else 0.0,
                ),
                name=p.get("name", "Rotated")
            ),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.id in doc.features
                else (False, "Rotate verification failed.")
            )
        ))

        # 8. Parametric Updates & Deletion
        self.register(CADFunction(
            name="UPDATE_PARAMETERS",
            category="parametric",
            description="Update parameters of a feature and rebuild its geometry.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
                "parameters": {"type": "dict", "required": True},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") and isinstance(p.get("parameters"), dict)
                else (False, "feature_id and parameters dict are required.")
            ),
            handler=lambda p, ctx, doc: self._handle_update_parameters(p["feature_id"], p["parameters"], doc),
            verifier=lambda p, res, doc: (
                (True, None) if res and res.get("success")
                else (False, "Parameter update failed to rebuild geometry.")
            )
        ))

        self.register(CADFunction(
            name="DELETE_FEATURE",
            category="document",
            description="Delete a feature from the document.",
            parameters_schema={
                "feature_id": {"type": "string", "required": True},
            },
            validator=lambda p, ctx, doc: (
                (True, None) if p.get("feature_id") in doc.features
                else (False, "Feature ID not found in document.")
            ),
            handler=lambda p, ctx, doc: {"success": doc.remove_feature(p["feature_id"])},
            verifier=lambda p, res, doc: (
                (True, None) if p["feature_id"] not in doc.features
                else (False, "Delete verification failed: Feature still exists.")
            )
        ))

        # 9. Measurements & Dimensions
        self.register(CADFunction(
            name="MEASURE_BOUNDING_BOX",
            category="measure",
            description="Calculate bounding box dimensions of a solid.",
            parameters_schema={"feature_id": {"type": "string", "required": True}},
            validator=lambda p, ctx, doc: ((True, None) if p.get("feature_id") else (False, "feature_id required.")),
            handler=lambda p, ctx, doc: CADMeasurement.get_bounding_box(p["feature_id"]),
            verifier=lambda p, res, doc: ((True, None) if res is not None else (False, "Measurement failed."))
        ))

        self.register(CADFunction(
            name="MEASURE_VOLUME",
            category="measure",
            description="Calculate exact solid volume in mm³.",
            parameters_schema={"feature_id": {"type": "string", "required": True}},
            validator=lambda p, ctx, doc: ((True, None) if p.get("feature_id") else (False, "feature_id required.")),
            handler=lambda p, ctx, doc: {"volume": CADMeasurement.get_volume(p["feature_id"]), "unit": "mm³"},
            verifier=lambda p, res, doc: ((True, None) if res and res.get("volume") is not None else (False, "Volume calculation failed."))
        ))

        # 10. Undo / Redo
        self.register(CADFunction(
            name="UNDO",
            category="lifecycle",
            description="Revert the last CAD operation.",
            parameters_schema={},
            handler=lambda p, ctx, doc: {"command": doc.undo()},
            verifier=lambda p, res, doc: ((True, None) if res and res.get("command") else (False, "Nothing to undo."))
        ))

        self.register(CADFunction(
            name="REDO",
            category="lifecycle",
            description="Re-execute the last undone CAD operation.",
            parameters_schema={},
            handler=lambda p, ctx, doc: {"command": doc.redo()},
            verifier=lambda p, res, doc: ((True, None) if res and res.get("command") else (False, "Nothing to redo."))
        ))

    def _handle_update_parameters(self, feature_id: str, new_params: dict, doc) -> dict:
        feat = doc.get_feature(feature_id)
        if not feat:
            raise ValueError(f"Feature {feature_id} not found.")
        merged = dict(feat.parameters)
        merged.update(new_params)
        feat.parameters = merged
        new_geom = CADModelingOperations.regenerate_feature(feat)
        if new_geom is not None:
            doc._geometry_cache[feature_id] = new_geom
            return {"success": True, "parameters": feat.parameters, "regenerated": True}
        return {"success": True, "parameters": feat.parameters, "regenerated": False}


# Singleton registry instance
_global_registry = CADFunctionRegistry()


def get_function_registry() -> CADFunctionRegistry:
    return _global_registry
