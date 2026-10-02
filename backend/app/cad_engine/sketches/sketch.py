"""2D Sketch system with parametric constraints."""
import uuid
import math
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
import logging

logger = logging.getLogger("jarvis.cad.sketch")


class ConstraintType(Enum):
    """Types of sketch constraints."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    COINCIDENT = "coincident"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    TANGENT = "tangent"
    EQUAL = "equal"
    CONCENTRIC = "concentric"
    SYMMETRIC = "symmetric"
    DISTANCE = "distance"
    ANGLE = "angle"
    RADIUS = "radius"
    DIAMETER = "diameter"
    FIXED = "fixed"


@dataclass
class SketchEntity:
    """Base class for sketch entities."""
    id: str
    entity_type: str
    construction: bool = False
    constraints: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "construction": self.construction,
            "constraints": self.constraints,
        }


@dataclass
class SketchPoint(SketchEntity):
    """A point in the sketch."""
    x: float = 0.0
    y: float = 0.0
    
    def __init__(self, x: float, y: float, construction: bool = False):
        super().__init__(
            id=str(uuid.uuid4()),
            entity_type="point",
            construction=construction
        )
        self.x = x
        self.y = y
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"x": self.x, "y": self.y})
        return d


@dataclass
class SketchLine(SketchEntity):
    """A line segment in the sketch."""
    start_id: str = ""
    end_id: str = ""
    
    def __init__(self, start_id: str, end_id: str, construction: bool = False):
        super().__init__(
            id=str(uuid.uuid4()),
            entity_type="line",
            construction=construction
        )
        self.start_id = start_id
        self.end_id = end_id
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"start_id": self.start_id, "end_id": self.end_id})
        return d


@dataclass
class SketchCircle(SketchEntity):
    """A circle in the sketch."""
    center_id: str = ""
    radius: float = 0.0
    
    def __init__(self, center_id: str, radius: float, construction: bool = False):
        super().__init__(
            id=str(uuid.uuid4()),
            entity_type="circle",
            construction=construction
        )
        self.center_id = center_id
        self.radius = radius
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"center_id": self.center_id, "radius": self.radius})
        return d


@dataclass
class SketchArc(SketchEntity):
    """An arc in the sketch."""
    center_id: str = ""
    start_id: str = ""
    end_id: str = ""
    radius: float = 0.0
    
    def __init__(self, center_id: str, start_id: str, end_id: str, radius: float, construction: bool = False):
        super().__init__(
            id=str(uuid.uuid4()),
            entity_type="arc",
            construction=construction
        )
        self.center_id = center_id
        self.start_id = start_id
        self.end_id = end_id
        self.radius = radius
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "center_id": self.center_id,
            "start_id": self.start_id,
            "end_id": self.end_id,
            "radius": self.radius,
        })
        return d


@dataclass
class SketchRectangle(SketchEntity):
    """A rectangle defined by corner points."""
    p1_id: str = ""
    p2_id: str = ""
    p3_id: str = ""
    p4_id: str = ""
    
    def __init__(self, p1_id: str, p2_id: str, p3_id: str, p4_id: str, construction: bool = False):
        super().__init__(
            id=str(uuid.uuid4()),
            entity_type="rectangle",
            construction=construction
        )
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.p3_id = p3_id
        self.p4_id = p4_id
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "p1_id": self.p1_id,
            "p2_id": self.p2_id,
            "p3_id": self.p3_id,
            "p4_id": self.p4_id,
        })
        return d


@dataclass
class Constraint:
    """A sketch constraint."""
    id: str
    constraint_type: ConstraintType
    entity_ids: list[str]
    value: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "constraint_type": self.constraint_type.value,
            "entity_ids": self.entity_ids,
            "value": self.value,
            "metadata": self.metadata,
        }


class Sketch:
    """
    2D Sketch with parametric constraints.
    
    This is a real sketch system that can be converted to CadQuery geometry.
    """
    
    def __init__(self, name: str = "Sketch", plane: str = "XY"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.plane = plane
        self.offset = 0.0
        
        self.entities: dict[str, SketchEntity] = {}
        self.points: dict[str, SketchPoint] = {}
        self.constraints: dict[str, Constraint] = {}
        
        self._dirty = True
        
        logger.info(f"[CAD] Created sketch: {name} on {plane} plane")
    
    def add_point(self, x: float, y: float, construction: bool = False) -> str:
        """Add a point to the sketch."""
        point = SketchPoint(x, y, construction)
        self.points[point.id] = point
        self.entities[point.id] = point
        self._dirty = True
        return point.id
    
    def add_line(self, x1: float, y1: float, x2: float, y2: float, construction: bool = False) -> str:
        """Add a line to the sketch."""
        p1 = SketchPoint(x1, y1)
        p2 = SketchPoint(x2, y2)
        self.points[p1.id] = p1
        self.points[p2.id] = p2
        self.entities[p1.id] = p1
        self.entities[p2.id] = p2
        
        line = SketchLine(p1.id, p2.id, construction)
        self.entities[line.id] = line
        self._dirty = True
        return line.id
    
    def add_circle(self, cx: float, cy: float, radius: float, construction: bool = False) -> str:
        """Add a circle to the sketch."""
        center = SketchPoint(cx, cy)
        self.points[center.id] = center
        self.entities[center.id] = center
        
        circle = SketchCircle(center.id, radius, construction)
        self.entities[circle.id] = circle
        self._dirty = True
        return circle.id
    
    def add_arc(self, cx: float, cy: float, x1: float, y1: float, x2: float, y2: float, radius: float, construction: bool = False) -> str:
        """Add an arc to the sketch."""
        center = SketchPoint(cx, cy)
        start = SketchPoint(x1, y1)
        end = SketchPoint(x2, y2)
        self.points[center.id] = center
        self.points[start.id] = start
        self.points[end.id] = end
        self.entities[center.id] = center
        self.entities[start.id] = start
        self.entities[end.id] = end
        
        arc = SketchArc(center.id, start.id, end.id, radius, construction)
        self.entities[arc.id] = arc
        self._dirty = True
        return arc.id
    
    def add_rectangle(self, x1: float, y1: float, x2: float, y2: float, construction: bool = False) -> str:
        """Add a rectangle to the sketch."""
        p1 = SketchPoint(x1, y1)
        p2 = SketchPoint(x2, y1)
        p3 = SketchPoint(x2, y2)
        p4 = SketchPoint(x1, y2)
        
        for p in [p1, p2, p3, p4]:
            self.points[p.id] = p
            self.entities[p.id] = p
        
        rect = SketchRectangle(p1.id, p2.id, p3.id, p4.id, construction)
        self.entities[rect.id] = rect
        self._dirty = True
        return rect.id

    def add_polyline(self, coords: list[tuple[float, float]], closed: bool = False, construction: bool = False) -> list[str]:
        """Add a series of connected lines forming a polyline."""
        if len(coords) < 2:
            return []
        line_ids = []
        n = len(coords)
        count = n if closed else n - 1
        for i in range(count):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]
            lid = self.add_line(float(x1), float(y1), float(x2), float(y2), construction=construction)
            line_ids.append(lid)
        return line_ids

    def offset_entities(self, distance: float) -> list[str]:
        """Offset all lines in the sketch by a normal distance."""
        new_lines = []
        for entity in list(self.entities.values()):
            if isinstance(entity, SketchLine):
                p1 = self.points.get(entity.start_id)
                p2 = self.points.get(entity.end_id)
                if not p1 or not p2:
                    continue
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                length = math.sqrt(dx * dx + dy * dy)
                if length == 0:
                    continue
                # Normal vector (-dy, dx)
                nx = -dy / length * distance
                ny = dx / length * distance
                nlid = self.add_line(p1.x + nx, p1.y + ny, p2.x + nx, p2.y + ny, construction=False)
                new_lines.append(nlid)
            elif isinstance(entity, SketchCircle):
                center = self.points.get(entity.center_id)
                if center:
                    new_r = max(0.1, entity.radius + distance)
                    cid = self.add_circle(center.x, center.y, new_r, construction=False)
                    new_lines.append(cid)
        return new_lines

    def to_segments_3d(self) -> list[dict]:
        """Return 3D line segments for viewport visualization."""
        segments = []
        def to_3d(x: float, y: float) -> list[float]:
            if self.plane == "XZ":
                return [round(x, 3), round(self.offset, 3), round(y, 3)]
            elif self.plane == "YZ":
                return [round(self.offset, 3), round(x, 3), round(y, 3)]
            else: # XY
                return [round(x, 3), round(y, 3), round(self.offset, 3)]

        for entity in self.entities.values():
            if isinstance(entity, SketchLine):
                p1 = self.points.get(entity.start_id)
                p2 = self.points.get(entity.end_id)
                if p1 and p2:
                    segments.append({
                        "id": entity.id,
                        "type": "line",
                        "construction": entity.construction,
                        "points": [to_3d(p1.x, p1.y), to_3d(p2.x, p2.y)],
                    })
            elif isinstance(entity, SketchCircle):
                center = self.points.get(entity.center_id)
                if center:
                    pts = []
                    steps = 36
                    for s in range(steps + 1):
                        ang = 2.0 * math.pi * s / steps
                        px = center.x + entity.radius * math.cos(ang)
                        py = center.y + entity.radius * math.sin(ang)
                        pts.append(to_3d(px, py))
                    segments.append({
                        "id": entity.id,
                        "type": "circle",
                        "construction": entity.construction,
                        "points": pts,
                    })
            elif isinstance(entity, SketchRectangle):
                p1 = self.points.get(entity.p1_id)
                p2 = self.points.get(entity.p2_id)
                p3 = self.points.get(entity.p3_id)
                p4 = self.points.get(entity.p4_id)
                if p1 and p2 and p3 and p4:
                    pts = [to_3d(p1.x, p1.y), to_3d(p2.x, p2.y), to_3d(p3.x, p3.y), to_3d(p4.x, p4.y), to_3d(p1.x, p1.y)]
                    segments.append({
                        "id": entity.id,
                        "type": "rectangle",
                        "construction": entity.construction,
                        "points": pts,
                    })
            elif isinstance(entity, SketchArc):
                center = self.points.get(entity.center_id)
                p1 = self.points.get(entity.start_id)
                p2 = self.points.get(entity.end_id)
                if center and p1 and p2:
                    a1 = math.atan2(p1.y - center.y, p1.x - center.x)
                    a2 = math.atan2(p2.y - center.y, p2.x - center.x)
                    if a2 < a1:
                        a2 += 2 * math.pi
                    steps = 18
                    pts = []
                    for s in range(steps + 1):
                        ang = a1 + (a2 - a1) * s / steps
                        px = center.x + entity.radius * math.cos(ang)
                        py = center.y + entity.radius * math.sin(ang)
                        pts.append(to_3d(px, py))
                    segments.append({
                        "id": entity.id,
                        "type": "arc",
                        "construction": entity.construction,
                        "points": pts,
                    })
        return segments
    
    def add_constraint(self, constraint_type: ConstraintType, entity_ids: list[str], value: Optional[float] = None) -> str:
        """Add a constraint to the sketch."""
        constraint = Constraint(
            id=str(uuid.uuid4()),
            constraint_type=constraint_type,
            entity_ids=entity_ids,
            value=value
        )
        self.constraints[constraint.id] = constraint
        
        for entity_id in entity_ids:
            if entity_id in self.entities:
                self.entities[entity_id].constraints.append(constraint.id)
        
        self._dirty = True
        logger.info(f"[CAD] Added constraint: {constraint_type.value}")
        return constraint.id
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and its constraints."""
        if entity_id not in self.entities:
            return False
        
        entity = self.entities[entity_id]
        
        for constraint_id in entity.constraints:
            if constraint_id in self.constraints:
                del self.constraints[constraint_id]
        
        if entity_id in self.points:
            del self.points[entity_id]
        
        del self.entities[entity_id]
        self._dirty = True
        return True
    
    def to_cadquery(self):
        """Convert sketch to CadQuery workplane."""
        try:
            import cadquery as cq
            
            plane_map = {
                "XY": cq.Plane.XY(),
                "XZ": cq.Plane.XZ(),
                "YZ": cq.Plane.YZ(),
            }
            plane = plane_map.get(self.plane, cq.Plane.XY())
            
            wp = cq.Workplane(plane).workplane(offset=self.offset)
            
            for entity in self.entities.values():
                if entity.construction:
                    continue
                
                if isinstance(entity, SketchLine):
                    p1 = self.points[entity.start_id]
                    p2 = self.points[entity.end_id]
                    wp = wp.moveTo(p1.x, p1.y).lineTo(p2.x, p2.y)
                
                elif isinstance(entity, SketchCircle):
                    center = self.points[entity.center_id]
                    wp = wp.moveTo(center.x, center.y).circle(entity.radius)
                
                elif isinstance(entity, SketchRectangle):
                    p1 = self.points[entity.p1_id]
                    p3 = self.points[entity.p3_id]
                    center_x = (p1.x + p3.x) / 2
                    center_y = (p1.y + p3.y) / 2
                    width = abs(p3.x - p1.x)
                    height = abs(p3.y - p1.y)
                    wp = wp.moveTo(center_x, center_y).rect(width, height)
            
            return wp
        
        except Exception as e:
            logger.error(f"[CAD] Failed to convert sketch to CadQuery: {e}")
            return None
    
    def to_dict(self) -> dict:
        """Serialize sketch to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "plane": self.plane,
            "offset": self.offset,
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "constraints": {cid: c.to_dict() for cid, c in self.constraints.items()},
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Sketch':
        """Deserialize sketch from dictionary."""
        sketch = Sketch(data["name"], data["plane"])
        sketch.id = data["id"]
        sketch.offset = data.get("offset", 0.0)
        
        for eid, edata in data["entities"].items():
            entity_type = edata["entity_type"]
            
            if entity_type == "point":
                point = SketchPoint(edata["x"], edata["y"], edata.get("construction", False))
                point.id = eid
                sketch.points[eid] = point
                sketch.entities[eid] = point
            
            elif entity_type == "line":
                line = SketchLine(edata["start_id"], edata["end_id"], edata.get("construction", False))
                line.id = eid
                sketch.entities[eid] = line
            
            elif entity_type == "circle":
                circle = SketchCircle(edata["center_id"], edata["radius"], edata.get("construction", False))
                circle.id = eid
                sketch.entities[eid] = circle
            
            elif entity_type == "rectangle":
                rect = SketchRectangle(edata["p1_id"], edata["p2_id"], edata["p3_id"], edata["p4_id"], edata.get("construction", False))
                rect.id = eid
                sketch.entities[eid] = rect
        
        for cid, cdata in data.get("constraints", {}).items():
            constraint = Constraint(
                id=cid,
                constraint_type=ConstraintType(cdata["constraint_type"]),
                entity_ids=cdata["entity_ids"],
                value=cdata.get("value")
            )
            sketch.constraints[cid] = constraint
        
        return sketch
