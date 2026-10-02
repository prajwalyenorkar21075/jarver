"""Geometry measurement and analysis."""
import math
import logging
from typing import Optional, Any
import cadquery as cq

from app.cad_engine.core.document import get_active_document
from app.cad_engine.core.geometry import BoundingBox, Point3D

logger = logging.getLogger("jarvis.cad.measure")


class CADMeasurement:
    """Real geometry measurement operations."""
    
    @staticmethod
    def get_bounding_box(feature_id: str) -> Optional[dict]:
        """Get bounding box of a feature."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return None
            
            bbox = geom.val().BoundingBox()
            
            return {
                "min": {"x": bbox.xmin, "y": bbox.ymin, "z": bbox.zmin},
                "max": {"x": bbox.xmax, "y": bbox.ymax, "z": bbox.zmax},
                "width": bbox.xmax - bbox.xmin,
                "height": bbox.ymax - bbox.ymin,
                "depth": bbox.zmax - bbox.zmin,
            }
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get bounding box: {e}")
            return None
    
    @staticmethod
    def get_volume(feature_id: str) -> Optional[float]:
        """Get volume of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return None
            
            return geom.val().Volume()
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get volume: {e}")
            return None
    
    @staticmethod
    def get_surface_area(feature_id: str) -> Optional[float]:
        """Get surface area of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return None
            
            return geom.val().Area()
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get surface area: {e}")
            return None
    
    @staticmethod
    def get_center_of_mass(feature_id: str) -> Optional[dict]:
        """Get center of mass of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return None
            
            com = geom.val().Center()
            
            return {
                "x": com.x,
                "y": com.y,
                "z": com.z,
            }
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get center of mass: {e}")
            return None
    
    @staticmethod
    def measure_distance(point1: tuple[float, float, float], point2: tuple[float, float, float]) -> float:
        """Measure distance between two points."""
        return math.sqrt(
            (point2[0] - point1[0])**2 +
            (point2[1] - point1[1])**2 +
            (point2[2] - point1[2])**2
        )
    
    @staticmethod
    def measure_angle(vector1: tuple[float, float, float], vector2: tuple[float, float, float]) -> float:
        """Measure angle between two vectors in degrees."""
        dot = sum(a * b for a, b in zip(vector1, vector2))
        mag1 = math.sqrt(sum(a * a for a in vector1))
        mag2 = math.sqrt(sum(b * b for b in vector2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        cos_angle = dot / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        
        return math.degrees(math.acos(cos_angle))
    
    @staticmethod
    def get_faces(feature_id: str) -> list[dict]:
        """Get information about all faces of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return []
            
            faces = geom.faces().vals()
            
            face_data = []
            for i, face in enumerate(faces):
                face_data.append({
                    "index": i,
                    "area": face.Area(),
                    "center": {
                        "x": face.Center().x,
                        "y": face.Center().y,
                        "z": face.Center().z,
                    },
                })
            
            return face_data
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get faces: {e}")
            return []
    
    @staticmethod
    def get_edges(feature_id: str) -> list[dict]:
        """Get information about all edges of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return []
            
            edges = geom.edges().vals()
            
            edge_data = []
            for i, edge in enumerate(edges):
                edge_data.append({
                    "index": i,
                    "length": edge.Length(),
                })
            
            return edge_data
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get edges: {e}")
            return []
    
    @staticmethod
    def get_vertices(feature_id: str) -> list[dict]:
        """Get information about all vertices of a solid."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return []
            
            vertices = geom.vertices().vals()
            
            vertex_data = []
            for i, vertex in enumerate(vertices):
                vertex_data.append({
                    "index": i,
                    "x": vertex.X,
                    "y": vertex.Y,
                    "z": vertex.Z,
                })
            
            return vertex_data
        
        except Exception as e:
            logger.error(f"[CAD] Failed to get vertices: {e}")
            return []
    
    @staticmethod
    def validate_geometry(feature_id: str) -> dict:
        """Validate geometry and return status."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                return {
                    "valid": False,
                    "error": "Feature not found",
                }
            
            shape = geom.val()
            
            is_valid = shape.isValid()
            
            return {
                "valid": is_valid,
                "volume": shape.Volume() if is_valid else None,
                "area": shape.Area() if is_valid else None,
                "faces": len(shape.Faces()) if is_valid else 0,
                "edges": len(shape.Edges()) if is_valid else 0,
                "vertices": len(shape.Vertices()) if is_valid else 0,
            }
        
        except Exception as e:
            logger.error(f"[CAD] Failed to validate geometry: {e}")
            return {
                "valid": False,
                "error": str(e),
            }


measurement = CADMeasurement()
