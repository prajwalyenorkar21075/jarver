"""Core geometry types and operations."""
import math
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Point2D:
    """2D point with x, y coordinates."""
    x: float
    y: float

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    @staticmethod
    def from_tuple(t: tuple[float, float]) -> 'Point2D':
        return Point2D(t[0], t[1])


@dataclass
class Point3D:
    """3D point with x, y, z coordinates."""
    x: float
    y: float
    z: float

    def distance_to(self, other: 'Point3D') -> float:
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @staticmethod
    def from_tuple(t: tuple[float, float, float]) -> 'Point3D':
        return Point3D(t[0], t[1], t[2])

    def to_vector(self) -> 'Vector3D':
        return Vector3D(self.x, self.y, self.z)


@dataclass
class Vector2D:
    """2D vector."""
    x: float
    y: float

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> 'Vector2D':
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)

    def dot(self, other: 'Vector2D') -> float:
        return self.x * other.x + self.y * other.y


@dataclass
class Vector3D:
    """3D vector."""
    x: float
    y: float
    z: float

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vector3D':
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)

    def dot(self, other: 'Vector3D') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def to_point(self) -> Point3D:
        return Point3D(self.x, self.y, self.z)


@dataclass
class BoundingBox:
    """3D axis-aligned bounding box."""
    min_point: Point3D
    max_point: Point3D

    @property
    def width(self) -> float:
        return self.max_point.x - self.min_point.x

    @property
    def height(self) -> float:
        return self.max_point.y - self.min_point.y

    @property
    def depth(self) -> float:
        return self.max_point.z - self.min_point.z

    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
            (self.min_point.z + self.max_point.z) / 2
        )

    @property
    def volume(self) -> float:
        return self.width * self.height * self.depth

    def contains(self, point: Point3D) -> bool:
        return (
            self.min_point.x <= point.x <= self.max_point.x and
            self.min_point.y <= point.y <= self.max_point.y and
            self.min_point.z <= point.z <= self.max_point.z
        )


@dataclass
class Transformation:
    """3D transformation (translation, rotation, scale)."""
    translation: Vector3D = None
    rotation: Vector3D = None  # Euler angles in radians
    scale: Vector3D = None

    def __post_init__(self):
        if self.translation is None:
            self.translation = Vector3D(0, 0, 0)
        if self.rotation is None:
            self.rotation = Vector3D(0, 0, 0)
        if self.scale is None:
            self.scale = Vector3D(1, 1, 1)

    def to_matrix(self) -> np.ndarray:
        """Convert to 4x4 transformation matrix."""
        cx, cy, cz = [math.cos(a) for a in (self.rotation.x, self.rotation.y, self.rotation.z)]
        sx, sy, sz = [math.sin(a) for a in (self.rotation.x, self.rotation.y, self.rotation.z)]

        rotation_matrix = np.array([
            [cy * cz, -cy * sz, sy, 0],
            [cx * sz + sx * sy * cz, cx * cz - sx * sy * sz, -sx * cy, 0],
            [sx * sz - cx * sy * cz, sx * cz + cx * sy * sz, cx * cy, 0],
            [0, 0, 0, 1]
        ])

        scale_matrix = np.array([
            [self.scale.x, 0, 0, 0],
            [0, self.scale.y, 0, 0],
            [0, 0, self.scale.z, 0],
            [0, 0, 0, 1]
        ])

        translation_matrix = np.array([
            [1, 0, 0, self.translation.x],
            [0, 1, 0, self.translation.y],
            [0, 0, 1, self.translation.z],
            [0, 0, 0, 1]
        ])

        return translation_matrix @ rotation_matrix @ scale_matrix
