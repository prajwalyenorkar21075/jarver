"""3D modeling operations using CadQuery."""
import uuid
import logging
from typing import Optional, Any
import cadquery as cq

from app.cad_engine.core.document import Feature, FeatureType, FeatureStatus, get_active_document
from app.cad_engine.sketches.sketch import Sketch

logger = logging.getLogger("jarvis.cad.modeling")


class CADModelingOperations:
    """
    Real 3D CAD modeling operations using CadQuery.
    
    All operations modify actual geometry, not mocks.
    """
    
    @staticmethod
    def create_box(width: float, height: float, depth: float, name: str = "Box") -> Feature:
        """Create a box primitive."""
        try:
            result = cq.Workplane("XY").box(width, height, depth)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "primitive_type": "box",
                    "width": width,
                    "height": height,
                    "depth": depth,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Created box: {width}x{height}x{depth}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to create box: {e}")
            raise
    
    @staticmethod
    def create_cylinder(radius: float, height: float, name: str = "Cylinder") -> Feature:
        """Create a cylinder primitive."""
        try:
            result = cq.Workplane("XY").circle(radius).extrude(height)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "primitive_type": "cylinder",
                    "radius": radius,
                    "height": height,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Created cylinder: r={radius}, h={height}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to create cylinder: {e}")
            raise
    
    @staticmethod
    def create_sphere(radius: float, name: str = "Sphere") -> Feature:
        """Create a sphere primitive."""
        try:
            result = cq.Workplane("XY").sphere(radius)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "primitive_type": "sphere",
                    "radius": radius,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Created sphere: r={radius}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to create sphere: {e}")
            raise
    
    @staticmethod
    def create_cone(radius: float, height: float, name: str = "Cone") -> Feature:
        """Create a cone primitive."""
        try:
            result = cq.Workplane("XY").newObject([cq.Solid.makeCone(radius, 0, height)])
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "primitive_type": "cone",
                    "radius": radius,
                    "height": height,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Created cone: r={radius}, h={height}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to create cone: {e}")
            raise
    
    @staticmethod
    def create_torus(major_radius: float, minor_radius: float, name: str = "Torus") -> Feature:
        """Create a torus primitive."""
        try:
            result = cq.Workplane("XY").circle(major_radius).circle(major_radius - 2 * minor_radius).revolve(360, (major_radius, 0, 0), (major_radius, 1, 0))
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "primitive_type": "torus",
                    "major_radius": major_radius,
                    "minor_radius": minor_radius,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Created torus: R={major_radius}, r={minor_radius}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to create torus: {e}")
            raise
    
    @staticmethod
    def extrude_sketch(sketch: Sketch, distance: float, name: str = "Extrusion") -> Feature:
        """Extrude a sketch to create a solid."""
        try:
            wp = sketch.to_cadquery()
            if wp is None:
                raise ValueError("Failed to convert sketch to CadQuery")
            
            result = wp.extrude(distance)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.EXTRUDE,
                parameters={
                    "sketch_id": sketch.id,
                    "distance": distance,
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Extruded sketch by {distance}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to extrude sketch: {e}")
            raise
    
    @staticmethod
    def revolve_sketch(sketch: Sketch, angle: float, axis: tuple[float, float, float] = (1, 0, 0), name: str = "Revolution") -> Feature:
        """Revolve a sketch around an axis."""
        try:
            wp = sketch.to_cadquery()
            if wp is None:
                raise ValueError("Failed to convert sketch to CadQuery")
            
            result = wp.revolve(angle, (0, 0, 0), axis)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.REVOLVE,
                parameters={
                    "sketch_id": sketch.id,
                    "angle": angle,
                    "axis": list(axis),
                },
            )
            
            doc = get_active_document()
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Revolved sketch by {angle} degrees")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to revolve sketch: {e}")
            raise
    
    @staticmethod
    def boolean_union(feature_id1: str, feature_id2: str, name: str = "Union") -> Feature:
        """Union two solids."""
        try:
            doc = get_active_document()
            
            geom1 = doc._geometry_cache.get(feature_id1)
            geom2 = doc._geometry_cache.get(feature_id2)
            
            if geom1 is None or geom2 is None:
                raise ValueError("One or both features not found in geometry cache")
            
            result = geom1.union(geom2)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.UNION,
                parameters={
                    "feature_id1": feature_id1,
                    "feature_id2": feature_id2,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Union of {feature_id1} and {feature_id2}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to union: {e}")
            raise
    
    @staticmethod
    def boolean_cut(feature_id1: str, feature_id2: str, name: str = "Cut") -> Feature:
        """Cut one solid from another."""
        try:
            doc = get_active_document()
            
            geom1 = doc._geometry_cache.get(feature_id1)
            geom2 = doc._geometry_cache.get(feature_id2)
            
            if geom1 is None or geom2 is None:
                raise ValueError("One or both features not found in geometry cache")
            
            result = geom1.cut(geom2)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.CUT,
                parameters={
                    "feature_id1": feature_id1,
                    "feature_id2": feature_id2,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Cut {feature_id2} from {feature_id1}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to cut: {e}")
            raise
    
    @staticmethod
    def boolean_intersect(feature_id1: str, feature_id2: str, name: str = "Intersect") -> Feature:
        """Intersect two solids."""
        try:
            doc = get_active_document()
            
            geom1 = doc._geometry_cache.get(feature_id1)
            geom2 = doc._geometry_cache.get(feature_id2)
            
            if geom1 is None or geom2 is None:
                raise ValueError("One or both features not found in geometry cache")
            
            result = geom1.intersect(geom2)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.INTERSECT,
                parameters={
                    "feature_id1": feature_id1,
                    "feature_id2": feature_id2,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Intersect of {feature_id1} and {feature_id2}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to intersect: {e}")
            raise
    
    @staticmethod
    def fillet(feature_id: str, radius: float, edge_selector: Optional[str] = None, name: str = "Fillet") -> Feature:
        """Apply fillet to edges."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError("Feature not found in geometry cache")
            
            if edge_selector:
                result = geom.edges(edge_selector).fillet(radius)
            else:
                result = geom.edges().fillet(radius)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.FILLET,
                parameters={
                    "feature_id": feature_id,
                    "radius": radius,
                    "edge_selector": edge_selector,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Fillet r={radius} applied")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to apply fillet: {e}")
            raise
    
    @staticmethod
    def chamfer(feature_id: str, distance: float, edge_selector: Optional[str] = None, name: str = "Chamfer") -> Feature:
        """Apply chamfer to edges."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError("Feature not found in geometry cache")
            
            if edge_selector:
                result = geom.edges(edge_selector).chamfer(distance)
            else:
                result = geom.edges().chamfer(distance)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.CHAMFER,
                parameters={
                    "feature_id": feature_id,
                    "distance": distance,
                    "edge_selector": edge_selector,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Chamfer d={distance} applied")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to apply chamfer: {e}")
            raise
    
    @staticmethod
    def shell(feature_id: str, thickness: float, face_selector: Optional[str] = None, name: str = "Shell") -> Feature:
        """Shell a solid (hollow with specified thickness)."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError("Feature not found in geometry cache")
            
            if face_selector:
                result = geom.faces(face_selector).shell(thickness)
            else:
                result = geom.shell(thickness)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.SHELL,
                parameters={
                    "feature_id": feature_id,
                    "thickness": thickness,
                    "face_selector": face_selector,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Shell thickness={thickness} applied")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to apply shell: {e}")
            raise
    
    @staticmethod
    def transform_feature(feature_id: str, translation: Optional[tuple[float, float, float]] = None, rotation: Optional[tuple[float, float, float]] = None, scale: Optional[tuple[float, float, float]] = None, name: Optional[str] = None) -> Feature:
        """Apply transformation to a feature."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            
            if geom is None:
                raise ValueError("Feature not found in geometry cache")
            
            result = geom
            
            if translation:
                result = result.translate(translation)
            
            if rotation:
                for i, angle in enumerate(rotation):
                    if angle != 0:
                        axis = [(1, 0, 0), (0, 1, 0), (0, 0, 1)][i]
                        result = result.rotate((0, 0, 0), axis, angle)
            
            if scale:
                result = result.scale(scale[0])
            
            feature_name = name or f"Transformed_{feature_id[:8]}"
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=feature_name,
                feature_type=FeatureType.PRIMITIVE,
                parameters={
                    "feature_id": feature_id,
                    "translation": list(translation) if translation else None,
                    "rotation": list(rotation) if rotation else None,
                    "scale": list(scale) if scale else None,
                },
            )
            
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            
            logger.info(f"[CAD] Transformed feature {feature_id}")
            return feature
        
        except Exception as e:
            logger.error(f"[CAD] Failed to transform: {e}")
            raise

    @staticmethod
    def regenerate_feature(feature: Feature) -> Any:
        """Rebuild a feature's geometry from its current parameters.

        Returns the new CadQuery workplane, or None when the feature type
        cannot be rebuilt from parameters alone.
        """
        doc = get_active_document()
        p = feature.parameters

        if feature.feature_type == FeatureType.PRIMITIVE:
            ptype = p.get("primitive_type")
            if ptype == "box":
                return cq.Workplane("XY").box(p["width"], p["height"], p["depth"])
            if ptype == "cylinder":
                return cq.Workplane("XY").circle(p["radius"]).extrude(p["height"])
            if ptype == "sphere":
                return cq.Workplane("XY").sphere(p["radius"])
            if ptype == "cone":
                return cq.Workplane("XY").newObject([cq.Solid.makeCone(p["radius"], 0, p["height"])])
            if ptype == "torus":
                mr, nr = p["major_radius"], p["minor_radius"]
                return (cq.Workplane("XY").circle(mr)
                        .circle(mr - 2 * nr)
                        .revolve(360, (mr, 0, 0), (mr, 1, 0)))
            return None

        if feature.feature_type == FeatureType.EXTRUDE:
            sketch = doc.get_sketch(p.get("sketch_id", ""))
            if sketch is None:
                return None
            return sketch.to_cadquery().extrude(p["distance"])

        if feature.feature_type == FeatureType.REVOLVE:
            sketch = doc.get_sketch(p.get("sketch_id", ""))
            if sketch is None:
                return None
            axis = tuple(p.get("axis", (1, 0, 0)))
            return sketch.to_cadquery().revolve(p["angle"], (0, 0, 0), axis)

        if feature.feature_type == FeatureType.HOLE:
            base_geom = doc._geometry_cache.get(p.get("base_feature_id", ""))
            if base_geom is None:
                return None
            wp = base_geom.faces(p.get("face_selector", ">Z")).workplane()
            if p.get("x", 0) != 0 or p.get("y", 0) != 0:
                wp = wp.center(p.get("x", 0), p.get("y", 0))
            if p.get("depth"):
                return wp.hole(p["diameter"], p["depth"])
            return wp.hole(p["diameter"])

        return None

    @staticmethod
    def create_hole(feature_id: str, diameter: float, depth: Optional[float] = None, x: float = 0.0, y: float = 0.0, face_selector: str = ">Z", name: str = "Hole") -> Feature:
        """Create a hole in an existing solid feature."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found in geometry cache")
            
            wp = geom.faces(face_selector).workplane()
            if x != 0.0 or y != 0.0:
                wp = wp.center(x, y)
            if depth is not None and depth > 0:
                result = wp.hole(diameter, depth)
            else:
                result = wp.hole(diameter)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.HOLE,
                parameters={
                    "base_feature_id": feature_id,
                    "diameter": diameter,
                    "depth": depth,
                    "x": x,
                    "y": y,
                    "face_selector": face_selector,
                },
                parent_id=feature_id,
            )
            doc._geometry_cache[feature.id] = result
            doc._geometry_cache[feature_id] = result
            doc.add_feature(feature, parent_id=feature_id)
            logger.info(f"[CAD] Created hole: dia={diameter}mm, depth={depth}mm on {feature_id}")
            return feature
        except Exception as e:
            logger.error(f"[CAD] Failed to create hole: {e}")
            raise

    @staticmethod
    def pattern_circular(feature_id: str, count: int = 6, angle: float = 360.0, radius: float = 0.0, hole_diameter: Optional[float] = None, name: str = "CircularPattern") -> Feature:
        """Create a circular pattern (e.g. 6 equally spaced holes or rotated solid array)."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found in geometry cache")
            
            if hole_diameter is not None and hole_diameter > 0 and radius > 0:
                result = geom.faces(">Z").workplane().polarArray(radius, 0, angle, count).hole(hole_diameter)
            else:
                result = geom
                step = angle / count
                for i in range(1, count):
                    cur_ang = i * step
                    rot = geom.rotate((0, 0, 0), (0, 0, 1), cur_ang)
                    result = result.union(rot)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PATTERN,
                parameters={
                    "base_feature_id": feature_id,
                    "pattern_type": "circular",
                    "count": count,
                    "angle": angle,
                    "radius": radius,
                    "hole_diameter": hole_diameter,
                },
                parent_id=feature_id,
            )
            doc._geometry_cache[feature.id] = result
            doc._geometry_cache[feature_id] = result
            doc.add_feature(feature, parent_id=feature_id)
            logger.info(f"[CAD] Created circular pattern: {count} items over {angle} deg")
            return feature
        except Exception as e:
            logger.error(f"[CAD] Failed to create circular pattern: {e}")
            raise

    @staticmethod
    def pattern_linear(feature_id: str, count_x: int = 2, count_y: int = 1, spacing_x: float = 20.0, spacing_y: float = 20.0, hole_diameter: Optional[float] = None, name: str = "LinearPattern") -> Feature:
        """Create a linear array / rectangular pattern."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found in geometry cache")
            
            if hole_diameter is not None and hole_diameter > 0:
                result = geom.faces(">Z").workplane().rarray(spacing_x, spacing_y, count_x, count_y).hole(hole_diameter)
            else:
                result = geom
                for ix in range(count_x):
                    for iy in range(count_y):
                        if ix == 0 and iy == 0:
                            continue
                        copy_s = geom.translate((ix * spacing_x, iy * spacing_y, 0))
                        result = result.union(copy_s)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.PATTERN,
                parameters={
                    "base_feature_id": feature_id,
                    "pattern_type": "linear",
                    "count_x": count_x,
                    "count_y": count_y,
                    "spacing_x": spacing_x,
                    "spacing_y": spacing_y,
                    "hole_diameter": hole_diameter,
                },
                parent_id=feature_id,
            )
            doc._geometry_cache[feature.id] = result
            doc._geometry_cache[feature_id] = result
            doc.add_feature(feature, parent_id=feature_id)
            logger.info(f"[CAD] Created linear pattern: {count_x}x{count_y}")
            return feature
        except Exception as e:
            logger.error(f"[CAD] Failed to create linear pattern: {e}")
            raise

    @staticmethod
    def mirror(feature_id: str, plane: str = "XY", name: str = "Mirror") -> Feature:
        """Mirror a feature across a principal plane (XY, XZ, YZ)."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            if geom is None:
                raise ValueError(f"Feature {feature_id} not found in geometry cache")
            
            result = geom.mirror(plane)
            
            feature = Feature(
                id=str(uuid.uuid4()),
                name=name,
                feature_type=FeatureType.MIRROR,
                parameters={
                    "base_feature_id": feature_id,
                    "plane": plane,
                },
            )
            doc._geometry_cache[feature.id] = result
            doc.add_feature(feature)
            logger.info(f"[CAD] Mirrored feature {feature_id} across {plane}")
            return feature
        except Exception as e:
            logger.error(f"[CAD] Failed to mirror feature: {e}")
            raise

    @staticmethod
    def get_tessellated_mesh(feature_id: str, tolerance: float = 0.1, angular_tolerance: float = 0.1) -> Optional[dict]:
        """Tessellate CadQuery Brep geometry into triangular mesh for WebGL rendering."""
        try:
            doc = get_active_document()
            geom = doc._geometry_cache.get(feature_id)
            if geom is None:
                return None
            
            feature = doc.get_feature(feature_id)
            shape = geom.val()
            vertices, triangles = shape.tessellate(tolerance, angular_tolerance)
            
            flat_verts = []
            for v in vertices:
                flat_verts.extend([round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)])
            
            flat_indices = []
            for t in triangles:
                flat_indices.extend([int(t[0]), int(t[1]), int(t[2])])
            
            bbox = shape.BoundingBox()
            
            return {
                "feature_id": feature_id,
                "name": feature.name if feature else "Feature",
                "type": feature.feature_type.value if feature else "solid",
                "parameters": feature.parameters if feature else {},
                "vertices": flat_verts,
                "indices": flat_indices,
                "bbox": {
                    "min": [round(bbox.xmin, 3), round(bbox.ymin, 3), round(bbox.zmin, 3)],
                    "max": [round(bbox.xmax, 3), round(bbox.ymax, 3), round(bbox.zmax, 3)],
                    "size": [
                        round(bbox.xmax - bbox.xmin, 3),
                        round(bbox.ymax - bbox.ymin, 3),
                        round(bbox.zmax - bbox.zmin, 3),
                    ],
                },
            }
        except Exception as e:
            logger.error(f"[CAD] Failed to tessellate mesh for {feature_id}: {e}")
            return None

    @staticmethod
    def get_all_document_meshes(tolerance: float = 0.1) -> dict:
        """Get all tessellated solid meshes and 2D sketches in the active document."""
        doc = get_active_document()
        meshes = []
        for fid, feat in doc.features.items():
            if not feat.visible:
                continue
            if fid in doc._geometry_cache:
                mesh = CADModelingOperations.get_tessellated_mesh(fid, tolerance)
                if mesh:
                    meshes.append(mesh)
        
        sketches_data = []
        for s in doc.list_sketches():
            sketches_data.append({
                "sketch_id": s.id,
                "name": s.name,
                "plane": s.plane,
                "offset": s.offset,
                "segments": s.to_segments_3d(),
            })
        
        return {
            "success": True,
            "document_id": doc.id,
            "document_name": doc.name,
            "meshes": meshes,
            "sketches": sketches_data,
        }


modeling_ops = CADModelingOperations()
