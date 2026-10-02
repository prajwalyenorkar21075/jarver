"""CAD Engine API endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional, Any
import tempfile
import os
from pathlib import Path

from app.cad_engine.core.document import (
    CADDokument, Feature, FeatureType, get_active_document, 
    set_active_document, new_document
)
from app.cad_engine.features.modeling import CADModelingOperations
from app.cad_engine.core.measurement import CADMeasurement
from app.cad_engine.io.file_io import CADFileIO
from app.cad_engine.sketches.sketch import Sketch, ConstraintType
from pydantic import BaseModel

router = APIRouter(prefix="/api/cad", tags=["cad"])


class CADCommandRequest(BaseModel):
    command: str
    context: Optional[dict] = None


class CADContextUpdateRequest(BaseModel):
    selected_feature_id: Optional[str] = None
    selected_feature_name: Optional[str] = None
    active_sketch_id: Optional[str] = None
    active_workplane: Optional[str] = None
    workspace: Optional[str] = None
    units: Optional[str] = None
    grid_snap: Optional[bool] = None
    object_snap: Optional[bool] = None
    section_view: Optional[bool] = None


# ============================================================================
# Unified CAD Command Pipeline & Meshes
# ============================================================================

@router.post("/command/execute")
async def execute_command_endpoint(req: CADCommandRequest):
    """Execute a natural-language or structured CAD command through the complete pipeline."""
    try:
        from app.cad_engine.commands import get_command_executor
        executor = get_command_executor()
        result = executor.execute(req.command, req.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution error: {str(e)}")


@router.get("/document/meshes")
async def get_document_meshes_endpoint(tolerance: float = 0.1):
    """Get all real tessellated 3D meshes and 2D sketches for WebGL rendering."""
    try:
        return CADModelingOperations.get_all_document_meshes(tolerance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract document meshes: {str(e)}")


@router.get("/feature/{feature_id}/mesh")
async def get_feature_mesh_endpoint(feature_id: str, tolerance: float = 0.1):
    """Get real tessellated 3D mesh for a specific feature."""
    try:
        mesh = CADModelingOperations.get_tessellated_mesh(feature_id, tolerance)
        if not mesh:
            raise HTTPException(status_code=404, detail=f"Feature {feature_id} has no 3D geometry.")
        return {"success": True, "mesh": mesh}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract mesh: {str(e)}")


@router.get("/command/registry")
async def get_command_registry_endpoint():
    """List all registered CAD capabilities with schemas."""
    try:
        from app.cad_engine.commands import get_function_registry
        return {"success": True, "functions": get_function_registry().list_functions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_cad_context_endpoint():
    """Get active persistent CAD context."""
    from app.cad_engine.commands import get_cad_context
    return {"success": True, "context": get_cad_context().to_dict()}


@router.post("/context")
async def update_cad_context_endpoint(req: CADContextUpdateRequest):
    """Update active persistent CAD context."""
    from app.cad_engine.commands import get_cad_context
    ctx = get_cad_context()
    ctx.update_from_dict(req.model_dump(exclude_unset=True))
    return {"success": True, "context": ctx.to_dict()}


# ============================================================================
# Document Management
# ============================================================================

@router.post("/document/new")
async def create_document(name: str = "Untitled"):
    """Create a new CAD document."""
    try:
        doc = new_document(name)
        return {
            "success": True,
            "document_id": doc.id,
            "name": doc.name,
            "message": f"Created new document: {name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")


@router.get("/document/current")
async def get_current_document():
    """Get current active document info."""
    try:
        doc = get_active_document()
        return {
            "success": True,
            "document_id": doc.id,
            "name": doc.name,
            "feature_count": len(doc.features),
            "created_at": doc.created_at,
            "modified_at": doc.modified_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.get("/document/tree")
async def get_model_tree():
    """Get the complete model tree."""
    try:
        doc = get_active_document()
        
        def build_tree(feature_id: str) -> dict:
            feature = doc.features.get(feature_id)
            if not feature:
                return None
            
            return {
                "id": feature.id,
                "name": feature.name,
                "type": feature.feature_type.value,
                "status": feature.status.value,
                "visible": feature.visible,
                "parameters": feature.parameters,
                "children": [build_tree(cid) for cid in feature.children_ids if build_tree(cid)],
            }
        
        tree = {
            "id": doc.id,
            "name": doc.name,
            "type": "document",
            "children": [build_tree(fid) for fid in doc.root_feature_ids if build_tree(fid)],
        }
        
        return {"success": True, "tree": tree}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model tree: {str(e)}")


@router.post("/document/save")
async def save_document(file_path: str):
    """Save document to .jarviscad format."""
    try:
        CADFileIO.save_document(file_path)
        return {
            "success": True,
            "message": f"Document saved to {file_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")


@router.post("/document/load")
async def load_document(file_path: str):
    """Load document from .jarviscad format."""
    try:
        doc = CADFileIO.load_document(file_path)
        return {
            "success": True,
            "document_id": doc.id,
            "name": doc.name,
            "feature_count": len(doc.features),
            "message": f"Loaded document: {doc.name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load document: {str(e)}")


# ============================================================================
# 3D Primitives
# ============================================================================

@router.post("/primitive/box")
async def create_box(width: float, height: float, depth: float, name: str = "Box"):
    """Create a box primitive."""
    try:
        feature = CADModelingOperations.create_box(width, height, depth, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "parameters": feature.parameters,
            "message": f"Created box: {width}x{height}x{depth}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create box: {str(e)}")


@router.post("/primitive/cylinder")
async def create_cylinder(radius: float, height: float, name: str = "Cylinder"):
    """Create a cylinder primitive."""
    try:
        feature = CADModelingOperations.create_cylinder(radius, height, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "parameters": feature.parameters,
            "message": f"Created cylinder: radius={radius}mm, height={height}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create cylinder: {str(e)}")


@router.post("/primitive/sphere")
async def create_sphere(radius: float, name: str = "Sphere"):
    """Create a sphere primitive."""
    try:
        feature = CADModelingOperations.create_sphere(radius, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "parameters": feature.parameters,
            "message": f"Created sphere: radius={radius}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sphere: {str(e)}")


@router.post("/primitive/cone")
async def create_cone(radius: float, height: float, name: str = "Cone"):
    """Create a cone primitive."""
    try:
        feature = CADModelingOperations.create_cone(radius, height, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "parameters": feature.parameters,
            "message": f"Created cone: radius={radius}mm, height={height}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create cone: {str(e)}")


@router.post("/primitive/torus")
async def create_torus(major_radius: float, minor_radius: float, name: str = "Torus"):
    """Create a torus primitive."""
    try:
        feature = CADModelingOperations.create_torus(major_radius, minor_radius, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "parameters": feature.parameters,
            "message": f"Created torus: major={major_radius}mm, minor={minor_radius}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create torus: {str(e)}")


# ============================================================================
# Sketches
# ============================================================================

@router.post("/sketch/rectangle")
async def create_sketch_rectangle(x1: float = 0.0, y1: float = 0.0, x2: float = 10.0, y2: float = 10.0,
                                  plane: str = "XY", offset: float = 0.0, name: str = "Sketch"):
    """Create a rectangular sketch on a plane."""
    try:
        sketch = Sketch(name=name, plane=plane)
        sketch.offset = offset
        sketch.add_rectangle(x1, y1, x2, y2)
        doc = get_active_document()
        doc.add_sketch(sketch)
        return {"success": True, "sketch_id": sketch.id, "name": sketch.name,
                "message": f"Created rectangle sketch ({x2 - x1}x{y2 - y1}mm on {plane})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sketch: {str(e)}")


@router.post("/sketch/circle")
async def create_sketch_circle(cx: float = 0.0, cy: float = 0.0, radius: float = 5.0,
                               plane: str = "XY", offset: float = 0.0, name: str = "Sketch"):
    """Create a circular sketch on a plane."""
    try:
        sketch = Sketch(name=name, plane=plane)
        sketch.offset = offset
        sketch.add_circle(cx, cy, radius)
        doc = get_active_document()
        doc.add_sketch(sketch)
        return {"success": True, "sketch_id": sketch.id, "name": sketch.name,
                "message": f"Created circle sketch (r={radius}mm on {plane})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sketch: {str(e)}")


@router.post("/sketch/polygon")
async def create_sketch_polygon(points: str, plane: str = "XY", offset: float = 0.0, name: str = "Sketch"):
    """Create a closed polygon sketch. points is JSON like [[0,0],[10,0],[10,5]]."""
    import json
    try:
        coords = json.loads(points)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="points must be a JSON array of [x, y] pairs")
    if not isinstance(coords, list) or len(coords) < 3 or not all(
            isinstance(p, (list, tuple)) and len(p) == 2 for p in coords):
        raise HTTPException(status_code=422, detail="points needs at least 3 [x, y] pairs")

    try:
        sketch = Sketch(name=name, plane=plane)
        sketch.offset = offset
        n = len(coords)
        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]
            sketch.add_line(float(x1), float(y1), float(x2), float(y2))
        doc = get_active_document()
        doc.add_sketch(sketch)
        return {"success": True, "sketch_id": sketch.id, "name": sketch.name,
                "message": f"Created polygon sketch ({n} vertices on {plane})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sketch: {str(e)}")


@router.get("/sketch/list")
async def list_sketches():
    """List sketches registered in the active document."""
    doc = get_active_document()
    return {
        "success": True,
        "sketches": [
            {"sketch_id": s.id, "name": s.name, "plane": s.plane,
             "entity_count": len(s.entities)}
            for s in doc.list_sketches()
        ],
    }


# ============================================================================
# Feature Operations
# ============================================================================

@router.post("/feature/extrude")
async def extrude_sketch(sketch_id: str, distance: float, name: str = "Extrusion"):
    """Extrude a sketch by a distance."""
    try:
        doc = get_active_document()
        sketch = doc.get_sketch(sketch_id)
        if sketch is None:
            raise HTTPException(
                status_code=404,
                detail=f"Sketch '{sketch_id}' not found. Create one first via /api/cad/sketch/rectangle|circle|polygon.",
            )
        feature = CADModelingOperations.extrude_sketch(sketch, distance, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Extruded sketch by {distance}mm"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extrude: {str(e)}")


@router.post("/feature/revolve")
async def revolve_sketch(sketch_id: str, angle: float = 360.0, name: str = "Revolution"):
    """Revolve a sketch around an axis."""
    try:
        doc = get_active_document()
        sketch = doc.get_sketch(sketch_id)
        if sketch is None:
            raise HTTPException(
                status_code=404,
                detail=f"Sketch '{sketch_id}' not found. Create one first via /api/cad/sketch/rectangle|circle|polygon.",
            )
        feature = CADModelingOperations.revolve_sketch(sketch, angle, name=name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Revolved sketch by {angle} degrees"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revolve: {str(e)}")


@router.post("/feature/union")
async def boolean_union(tool_id: str, base_id: str, name: str = "Union"):
    """Perform boolean union of two bodies."""
    try:
        feature = CADModelingOperations.boolean_union(tool_id, base_id, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": "Union operation completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to union: {str(e)}")


@router.post("/feature/cut")
async def boolean_cut(tool_id: str, base_id: str, name: str = "Cut"):
    """Perform boolean cut of tool from base."""
    try:
        feature = CADModelingOperations.boolean_cut(tool_id, base_id, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": "Cut operation completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cut: {str(e)}")


@router.post("/feature/fillet")
async def fillet_edges(feature_id: str, radius: float, edge_ids: Optional[list[str]] = None, name: str = "Fillet"):
    """Apply fillet to edges."""
    try:
        feature = CADModelingOperations.fillet(feature_id, radius, edge_ids, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Applied fillet with radius {radius}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fillet: {str(e)}")


@router.post("/feature/chamfer")
async def chamfer_edges(feature_id: str, distance: float, edge_ids: Optional[list[str]] = None, name: str = "Chamfer"):
    """Apply chamfer to edges."""
    try:
        feature = CADModelingOperations.chamfer(feature_id, distance, edge_ids, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Applied chamfer with distance {distance}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chamfer: {str(e)}")


@router.post("/feature/shell")
async def shell_body(feature_id: str, thickness: float, face_ids: Optional[list[str]] = None, name: str = "Shell"):
    """Shell a body with specified thickness."""
    try:
        feature = CADModelingOperations.shell(feature_id, thickness, face_ids, name)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Applied shell with thickness {thickness}mm"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to shell: {str(e)}")


@router.post("/feature/hole")
async def create_hole(feature_id: str, diameter: float, depth: Optional[float] = None, x: float = 0.0, y: float = 0.0, face_selector: str = ">Z", name: str = "Hole"):
    """Create a hole in a feature."""
    try:
        feature = CADModelingOperations.create_hole(feature_id, diameter, depth, x, y, face_selector, name)
        return {"success": True, "feature_id": feature.id, "name": feature.name, "parameters": feature.parameters, "message": f"Created {diameter}mm hole"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create hole: {str(e)}")


@router.post("/feature/pattern/circular")
async def pattern_circular(feature_id: str, count: int = 6, angle: float = 360.0, radius: float = 0.0, hole_diameter: Optional[float] = None, name: str = "CircularPattern"):
    """Create circular pattern."""
    try:
        feature = CADModelingOperations.pattern_circular(feature_id, count, angle, radius, hole_diameter, name)
        return {"success": True, "feature_id": feature.id, "name": feature.name, "parameters": feature.parameters, "message": f"Created {count}-item circular pattern"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create circular pattern: {str(e)}")


@router.post("/feature/pattern/linear")
async def pattern_linear(feature_id: str, count_x: int = 2, count_y: int = 1, spacing_x: float = 20.0, spacing_y: float = 20.0, hole_diameter: Optional[float] = None, name: str = "LinearPattern"):
    """Create linear pattern."""
    try:
        feature = CADModelingOperations.pattern_linear(feature_id, count_x, count_y, spacing_x, spacing_y, hole_diameter, name)
        return {"success": True, "feature_id": feature.id, "name": feature.name, "parameters": feature.parameters, "message": f"Created linear pattern"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create linear pattern: {str(e)}")


@router.post("/feature/mirror")
async def mirror_feature(feature_id: str, plane: str = "XY", name: str = "Mirror"):
    """Mirror feature across plane."""
    try:
        feature = CADModelingOperations.mirror(feature_id, plane, name)
        return {"success": True, "feature_id": feature.id, "name": feature.name, "parameters": feature.parameters, "message": f"Mirrored feature across {plane}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mirror: {str(e)}")



# ============================================================================
# Measurements
# ============================================================================

@router.get("/measure/bounding-box/{feature_id}")
async def get_bounding_box(feature_id: str):
    """Get bounding box of a feature."""
    try:
        bbox = CADMeasurement.get_bounding_box(feature_id)
        if bbox is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "bounding_box": bbox}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bounding box: {str(e)}")


@router.get("/measure/volume/{feature_id}")
async def get_volume(feature_id: str):
    """Get volume of a feature."""
    try:
        volume = CADMeasurement.get_volume(feature_id)
        if volume is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "volume": volume, "unit": "mm^3"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get volume: {str(e)}")


@router.get("/measure/surface-area/{feature_id}")
async def get_surface_area(feature_id: str):
    """Get surface area of a feature."""
    try:
        area = CADMeasurement.get_surface_area(feature_id)
        if area is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "surface_area": area, "unit": "mm^2"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get surface area: {str(e)}")


@router.get("/measure/center-of-mass/{feature_id}")
async def get_center_of_mass(feature_id: str):
    """Get center of mass of a feature."""
    try:
        com = CADMeasurement.get_center_of_mass(feature_id)
        if com is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "center_of_mass": com, "unit": "mm"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get center of mass: {str(e)}")


@router.get("/measure/faces/{feature_id}")
async def get_faces(feature_id: str):
    """Get face count and info."""
    try:
        faces = CADMeasurement.get_faces(feature_id)
        if faces is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "face_count": len(faces), "faces": faces}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get faces: {str(e)}")


@router.get("/measure/edges/{feature_id}")
async def get_edges(feature_id: str):
    """Get edge count and info."""
    try:
        edges = CADMeasurement.get_edges(feature_id)
        if edges is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "edge_count": len(edges), "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edges: {str(e)}")


@router.get("/measure/vertices/{feature_id}")
async def get_vertices(feature_id: str):
    """Get vertex count and info."""
    try:
        vertices = CADMeasurement.get_vertices(feature_id)
        if vertices is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "vertex_count": len(vertices), "vertices": vertices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get vertices: {str(e)}")


# ============================================================================
# File Import/Export
# ============================================================================

@router.post("/export/stl/{feature_id}")
async def export_stl(feature_id: str, file_path: str):
    """Export feature to STL format."""
    try:
        CADFileIO.export_stl(feature_id, file_path)
        return {"success": True, "message": f"Exported to STL: {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export STL: {str(e)}")


@router.post("/export/step/{feature_id}")
async def export_step(feature_id: str, file_path: str):
    """Export feature to STEP format."""
    try:
        CADFileIO.export_step(feature_id, file_path)
        return {"success": True, "message": f"Exported to STEP: {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export STEP: {str(e)}")


@router.post("/export/brep/{feature_id}")
async def export_brep(feature_id: str, file_path: str):
    """Export feature to BREP format."""
    try:
        CADFileIO.export_brep(feature_id, file_path)
        return {"success": True, "message": f"Exported to BREP: {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export BREP: {str(e)}")


@router.post("/import/stl")
async def import_stl(file_path: str):
    """Import STL file."""
    try:
        feature = CADFileIO.import_stl(file_path)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Imported STL: {file_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import STL: {str(e)}")


@router.post("/import/step")
async def import_step(file_path: str):
    """Import STEP file."""
    try:
        feature = CADFileIO.import_step(file_path)
        return {
            "success": True,
            "feature_id": feature.id,
            "name": feature.name,
            "message": f"Imported STEP: {file_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import STEP: {str(e)}")


# ============================================================================
# Undo/Redo
# ============================================================================

@router.post("/undo")
async def undo():
    """Undo last operation."""
    try:
        doc = get_active_document()
        command = doc.undo()
        if command is None:
            return {"success": False, "message": "Nothing to undo"}
        return {"success": True, "message": f"Undone: {command.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to undo: {str(e)}")


@router.post("/redo")
async def redo():
    """Redo last undone operation."""
    try:
        doc = get_active_document()
        command = doc.redo()
        if command is None:
            return {"success": False, "message": "Nothing to redo"}
        return {"success": True, "message": f"Redone: {command.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to redo: {str(e)}")


# ============================================================================
# Feature Management
# ============================================================================

@router.get("/feature/{feature_id}")
async def get_feature(feature_id: str):
    """Get feature details."""
    try:
        doc = get_active_document()
        feature = doc.get_feature(feature_id)
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {
            "success": True,
            "feature": feature.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature: {str(e)}")


@router.delete("/feature/{feature_id}")
async def delete_feature(feature_id: str):
    """Delete a feature."""
    try:
        doc = get_active_document()
        success = doc.remove_feature(feature_id)
        if not success:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "message": "Feature deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete feature: {str(e)}")


@router.put("/feature/{feature_id}/rename")
async def rename_feature(feature_id: str, new_name: str):
    """Rename a feature."""
    try:
        doc = get_active_document()
        success = doc.rename_feature(feature_id, new_name)
        if not success:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "message": f"Renamed to {new_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename feature: {str(e)}")


@router.put("/feature/{feature_id}/visibility")
async def set_visibility(feature_id: str, visible: bool):
    """Set feature visibility."""
    try:
        doc = get_active_document()
        success = doc.set_feature_visibility(feature_id, visible)
        if not success:
            raise HTTPException(status_code=404, detail="Feature not found")
        return {"success": True, "message": f"Visibility set to {visible}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set visibility: {str(e)}")


@router.put("/feature/{feature_id}/parameters")
async def update_parameters(feature_id: str, parameters: dict):
    """Update feature parameters and rebuild the geometry."""
    import uuid as _uuid
    from app.cad_engine.core.document import FeatureStatus, Command
    try:
        doc = get_active_document()
        feature = doc.get_feature(feature_id)
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")

        old_params = dict(feature.parameters)
        old_geom = doc._geometry_cache.get(feature_id)
        doc.update_feature_parameters(feature_id, parameters)

        from app.cad_engine.features.modeling import CADModelingOperations
        try:
            new_geom = CADModelingOperations.regenerate_feature(feature)
        except Exception as geom_err:
            feature.status = FeatureStatus.INVALID
            raise HTTPException(status_code=500, detail=f"Parameters stored but geometry rebuild failed: {geom_err}")

        if new_geom is not None:
            doc._geometry_cache[feature_id] = new_geom
            feature.status = FeatureStatus.VALID

        def _restore(p, g):
            feature.parameters.clear()
            feature.parameters.update(p)
            if g is not None:
                doc._geometry_cache[feature_id] = g
            elif feature_id in doc._geometry_cache:
                del doc._geometry_cache[feature_id]

        new_params = dict(feature.parameters)
        doc.push_undo(Command(
            id=str(_uuid.uuid4())[:8],
            name=f"Update {feature.name} parameters",
            feature_id=feature_id,
            parameters=new_params,
            undo_fn=lambda: _restore(old_params, old_geom),
            redo_fn=lambda: _restore(new_params, new_geom),
        ))

        if new_geom is None:
            return {
                "success": True,
                "regenerated": False,
                "message": "Parameters updated, but this feature type cannot be rebuilt from parameters alone; geometry is unchanged.",
            }
        return {
            "success": True,
            "regenerated": True,
            "parameters": feature.parameters,
            "message": "Parameters updated and geometry rebuilt",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update parameters: {str(e)}")
