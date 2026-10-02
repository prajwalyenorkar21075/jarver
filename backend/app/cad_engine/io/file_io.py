"""CAD file import/export with real format support."""
import json
import logging
import uuid
from pathlib import Path
from typing import Optional, Any
import cadquery as cq

from app.cad_engine.core.document import CADDokument, Feature, FeatureType, get_active_document

logger = logging.getLogger("jarvis.cad.io")


class CADFileIO:
    """
    Real CAD file import/export operations.
    
    Supports: STL, STEP, OBJ, BREP (3D) and DXF, SVG (2D)
    """
    
    @staticmethod
    def export_stl(feature_id: str, file_path: str, tolerance: float = 0.1) -> bool:
        """Export a feature to STL format."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found")
            
            cq.exporters.export(geom, file_path, exportType='STL', tolerance=tolerance)
            
            logger.info(f"[CAD] Exported STL: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to export STL: {e}")
            raise
    
    @staticmethod
    def import_stl(file_path: str) -> Feature:
        """Import an STL file."""
        try:
            import trimesh
            mesh = trimesh.load(file_path)
            
            result = cq.Workplane("XY").newObject([mesh])
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=Path(file_path).stem,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "source_file": file_path,
                    "format": "stl",
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Imported STL: {file_path}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to import STL: {e}")
            raise
    
    @staticmethod
    def export_step(feature_id: str, file_path: str) -> bool:
        """Export a feature to STEP format."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found")
            
            cq.exporters.export(geom, file_path, exportType='STEP')
            
            logger.info(f"[CAD] Exported STEP: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to export STEP: {e}")
            raise
    
    @staticmethod
    def import_step(file_path: str) -> Feature:
        """Import a STEP file."""
        try:
            result = cq.importers.importStep(file_path)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=Path(file_path).stem,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "source_file": file_path,
                    "format": "step",
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Imported STEP: {file_path}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to import STEP: {e}")
            raise
    
    @staticmethod
    def export_brep(feature_id: str, file_path: str) -> bool:
        """Export a feature to BREP format."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found")
            
            cq.exporters.export(geom, file_path, exportType='BREP')
            
            logger.info(f"[CAD] Exported BREP: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to export BREP: {e}")
            raise
    
    @staticmethod
    def import_brep(file_path: str) -> Feature:
        """Import a BREP file."""
        try:
            from OCP.BRep import BRep_Builder
            from OCP.BRepTools import BRepTools_ReadShape
            
            reader = BRepTools_ReadShape(file_path)
            shape = reader.Shape()
            
            result = cq.Workplane("XY").newObject([shape])
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=Path(file_path).stem,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "source_file": file_path,
                    "format": "brep",
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Imported BREP: {file_path}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to import BREP: {e}")
            raise
    
    @staticmethod
    def export_obj(feature_id: str, file_path: str) -> bool:
        """Export a feature to OBJ format (via STL conversion)."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found")
            
            stl_path = file_path.replace('.obj', '.stl')
            cq.exporters.export(geom, stl_path, exportType='STL')
            
            import trimesh
            mesh = trimesh.load(stl_path)
            mesh.export(file_path, file_type='obj')
            
            Path(stl_path).unlink()
            
            logger.info(f"[CAD] Exported OBJ: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to export OBJ: {e}")
            raise
    
    @staticmethod
    def export_dxf(sketch_id: str, file_path: str) -> bool:
        """Export a sketch to DXF format."""
        try:
            from app.cad_engine.sketches.sketch import Sketch
            
            doc = get_active_document()
            sketch_data = doc.features.get(sketch_id)
            
            if sketch_data is None:
                raise ValueError(f"Sketch {sketch_id} not found")
            
            sketch = Sketch.from_dict(sketch_data.parameters.get("sketch_data", {}))
            wp = sketch.to_cadquery()
            
            if wp is None:
                raise ValueError("Failed to convert sketch to CadQuery")
            
            cq.exporters.export(wp, file_path, exportType='DXF')
            
            logger.info(f"[CAD] Exported DXF: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to export DXF: {e}")
            raise
    
    @staticmethod
    def save_document(file_path: str, doc: Optional[CADDokument] = None) -> bool:
        """Save document to native .jarviscad format."""
        try:
            if doc is None:
                doc = get_active_document()
            
            data = doc.to_dict()
            
            geometry_data = {}
            for feature_id, geom in doc._geometry_cache.items():
                try:
                    brep_path = Path(file_path).parent / f"{feature_id}.brep"
                    cq.exporters.export(geom, str(brep_path), exportType='BREP')
                    geometry_data[feature_id] = str(brep_path)
                except Exception as e:
                    logger.warning(f"[CAD] Failed to export geometry for {feature_id}: {e}")
            
            data["geometry_files"] = geometry_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"[CAD] Saved document: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[CAD] Failed to save document: {e}")
            raise
    
    @staticmethod
    def load_document(file_path: str) -> CADDokument:
        """Load document from native .jarviscad format."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            doc = CADDokument.from_dict(data)
            
            geometry_files = data.get("geometry_files", {})
            for feature_id, brep_path in geometry_files.items():
                try:
                    if Path(brep_path).exists():
                        from OCP.BRepTools import BRepTools_ReadShape
                        reader = BRepTools_ReadShape(brep_path)
                        shape = reader.Shape()
                        result = cq.Workplane("XY").newObject([shape])
                        doc._geometry_cache[feature_id] = result
                except Exception as e:
                    logger.warning(f"[CAD] Failed to load geometry for {feature_id}: {e}")
            
            from app.cad_engine.core.document import set_active_document
            set_active_document(doc)
            
            logger.info(f"[CAD] Loaded document: {file_path}")
            return doc
        
        except Exception as e:
            logger.error(f"[CAD] Failed to load document: {e}")
            raise


file_io = CADFileIO()
