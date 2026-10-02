"""Robotics services for JARVIS — semantic mapping, navigation, motion planning.

Architecture:
Camera/Sensors → Perception → Localization → Semantic Map → Path Planning →
Navigation → Motion Control → Verification

Supports simulation mode when hardware is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("jarvis.robotics")


class RobotMode(str, Enum):
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    MANIPULATING = "MANIPULATING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class NavigationStatus(str, Enum):
    PLANNING = "PLANNING"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RELOCALIZING = "RELOCALIZING"


@dataclass
class Pose2D:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def distance_to(self, other: Pose2D) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def angle_to(self, other: Pose2D) -> float:
        return math.atan2(other.y - self.y, other.x - self.x)

    def to_dict(self) -> dict[str, float]:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "theta": round(self.theta, 3)}


@dataclass
class JointState:
    joint_names: list[str] = field(default_factory=list)
    positions: list[float] = field(default_factory=list)
    velocities: list[float] = field(default_factory=list)
    efforts: list[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "joint_names": self.joint_names,
            "positions": [round(p, 4) for p in self.positions],
            "velocities": [round(v, 4) for v in self.velocities],
            "efforts": [round(e, 4) for e in self.efforts],
            "timestamp": self.timestamp,
        }


@dataclass
class RobotState:
    mode: RobotMode = RobotMode.IDLE
    pose: Pose2D = field(default_factory=Pose2D)
    joint_state: JointState = field(default_factory=JointState)
    battery_level: float = 100.0
    velocity: tuple[float, float] = (0.0, 0.0)
    target_pose: Pose2D | None = None
    navigation_status: NavigationStatus = NavigationStatus.PLANNING
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "pose": self.pose.to_dict(),
            "joint_state": self.joint_state.to_dict(),
            "battery_level": round(self.battery_level, 1),
            "velocity": list(self.velocity),
            "target_pose": self.target_pose.to_dict() if self.target_pose else None,
            "navigation_status": self.navigation_status.value,
            "timestamp": self.timestamp,
        }


@dataclass
class SemanticLocation:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    pose: Pose2D = field(default_factory=Pose2D)
    category: str = ""
    description: str = ""
    confidence: float = 1.0
    objects_present: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pose": self.pose.to_dict(),
            "category": self.category,
            "description": self.description,
            "confidence": self.confidence,
            "objects_present": self.objects_present,
        }


@dataclass
class PathNode:
    x: float
    y: float
    theta: float = 0.0
    cost: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "theta": round(self.theta, 3), "cost": round(self.cost, 3)}


class SemanticMap:
    def __init__(self):
        self._locations: dict[str, SemanticLocation] = {}
        self._grid: np.ndarray | None = None
        self._grid_resolution = 0.05
        self._grid_size = (200, 200)
        self._origin = Pose2D(x=-5.0, y=-5.0)
        self._init_default_locations()
        self._init_grid()
        logger.info("[ROBOTICS] SemanticMap initialized")

    def _init_default_locations(self):
        defaults = [
            SemanticLocation(name="charging_station", pose=Pose2D(0, 0, 0),
                category="infrastructure", description="Robot charging dock"),
            SemanticLocation(name="desk", pose=Pose2D(2.0, 1.5, 0),
                category="furniture", description="Work desk with computer"),
            SemanticLocation(name="door_entrance", pose=Pose2D(-2.0, 0, 1.57),
                category="doorway", description="Main entrance door"),
            SemanticLocation(name="kitchen", pose=Pose2D(3.0, -1.0, 0),
                category="room", description="Kitchen area"),
            SemanticLocation(name="lab_bench", pose=Pose2D(-1.0, 2.5, 0),
                category="workspace", description="Robotics lab workbench"),
        ]
        for loc in defaults:
            self._locations[loc.name] = loc

    def _init_grid(self):
        self._grid = np.zeros(self._grid_size, dtype=np.uint8)
        self._grid[0:10, :] = 100
        self._grid[-10:, :] = 100
        self._grid[:, 0:10] = 100
        self._grid[:, -10:] = 100

    def add_location(self, location: SemanticLocation):
        self._locations[location.name] = location

    def get_location(self, name: str) -> SemanticLocation | None:
        return self._locations.get(name)

    def find_nearest(self, pose: Pose2D, category: str | None = None) -> SemanticLocation | None:
        candidates = self._locations.values()
        if category:
            candidates = [l for l in candidates if l.category == category]
        best = None
        best_dist = float("inf")
        for loc in candidates:
            dist = pose.distance_to(loc.pose)
            if dist < best_dist:
                best_dist = dist
                best = loc
        return best

    def is_occupied(self, x: float, y: float) -> bool:
        if self._grid is None:
            return False
        gx = int((x - self._origin.x) / self._grid_resolution)
        gy = int((y - self._origin.y) / self._grid_resolution)
        if 0 <= gx < self._grid_size[0] and 0 <= gy < self._grid_size[1]:
            return self._grid[gy, gx] > 50
        return True

    def get_all_locations(self) -> list[dict[str, Any]]:
        return [loc.to_dict() for loc in self._locations.values()]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_locations": len(self._locations),
            "categories": list(set(l.category for l in self._locations.values())),
            "grid_size": list(self._grid_size),
            "grid_resolution": self._grid_resolution,
        }


class PathPlanner:
    def __init__(self, semantic_map: SemanticMap):
        self._map = semantic_map
        logger.info("[ROBOTICS] PathPlanner initialized")

    async def plan_path(self, start: Pose2D, goal: Pose2D) -> list[PathNode]:
        logger.info(f"[ROBOTICS] Planning path from ({start.x:.1f},{start.y:.1f}) to ({goal.x:.1f},{goal.y:.1f})")

        path = []
        num_waypoints = max(5, int(start.distance_to(goal) / 0.2))
        for i in range(num_waypoints + 1):
            t = i / num_waypoints
            x = start.x + t * (goal.x - start.x)
            y = start.y + t * (goal.y - start.y)
            theta = start.theta + t * (goal.theta - start.theta)

            if self._map.is_occupied(x, y):
                x += 0.3
                y += 0.3

            cost = start.distance_to(Pose2D(x, y))
            path.append(PathNode(x=x, y=y, theta=theta, cost=cost))

        logger.info(f"[ROBOTICS] Path planned with {len(path)} waypoints")
        return path

    async def check_collision(self, pose: Pose2D) -> bool:
        return self._map.is_occupied(pose.x, pose.y)


class Navigator:
    def __init__(self, semantic_map: SemanticMap, planner: PathPlanner):
        self._map = semantic_map
        self._planner = planner
        self._current_path: list[PathNode] = []
        self._waypoint_index = 0
        self._arrival_threshold = 0.1
        logger.info("[ROBOTICS] Navigator initialized")

    async def navigate_to(self, location_name: str, robot_state: RobotState) -> dict[str, Any]:
        location = self._map.get_location(location_name)
        if not location:
            return {"status": NavigationStatus.FAILED.value, "error": f"Location '{location_name}' not found"}

        robot_state.target_pose = location.pose
        robot_state.navigation_status = NavigationStatus.PLANNING

        path = await self._planner.plan_path(robot_state.pose, location.pose)
        if not path:
            robot_state.navigation_status = NavigationStatus.FAILED
            return {"status": NavigationStatus.FAILED.value, "error": "Path planning failed"}

        self._current_path = path
        self._waypoint_index = 0
        robot_state.navigation_status = NavigationStatus.MOVING

        for i, node in enumerate(path):
            self._waypoint_index = i
            dist = robot_state.pose.distance_to(Pose2D(node.x, node.y))
            if dist < self._arrival_threshold:
                continue
            robot_state.pose = Pose2D(x=node.x, y=node.y, theta=node.theta)
            await asyncio.sleep(0.01)

        robot_state.navigation_status = NavigationStatus.ARRIVED
        robot_state.target_pose = None
        self._current_path = []

        return {
            "status": NavigationStatus.ARRIVED.value,
            "location": location.to_dict(),
            "path_length": len(path),
            "final_pose": robot_state.pose.to_dict(),
        }

    async def cancel_navigation(self, robot_state: RobotState):
        self._current_path = []
        self._waypoint_index = 0
        robot_state.navigation_status = NavigationStatus.FAILED
        robot_state.target_pose = None
        robot_state.velocity = (0.0, 0.0)

    def get_status(self) -> dict[str, Any]:
        return {
            "navigating": len(self._current_path) > 0,
            "waypoint_index": self._waypoint_index,
            "total_waypoints": len(self._current_path),
            "path": [n.to_dict() for n in self._current_path[:10]],
        }


class MotionPlanner:
    def __init__(self):
        self._joint_names = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
        self._joint_limits = [
            (-3.14, 3.14), (-2.0, 2.0), (-2.0, 2.0),
            (-3.14, 3.14), (-2.0, 2.0), (-3.14, 3.14),
        ]
        self._home_position = [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]
        logger.info("[ROBOTICS] MotionPlanner initialized (6-DOF arm)")

    async def plan_trajectory(
        self,
        target_joints: list[float],
        current_joints: list[float],
        steps: int = 50,
    ) -> list[list[float]]:
        trajectory = []
        for i in range(steps + 1):
            t = i / steps
            smooth_t = t * t * (3 - 2 * t)
            point = [
                c + smooth_t * (tgt - c)
                for c, tgt in zip(current_joints, target_joints)
            ]
            trajectory.append(point)
        return trajectory

    async def inverse_kinematics(self, target_pose: Pose2D) -> list[float] | None:
        x, y = target_pose.x, target_pose.y
        l1, l2 = 0.4, 0.3
        dist = math.sqrt(x ** 2 + y ** 2)
        if dist > l1 + l2:
            return None
        q2 = math.acos(max(-1, min(1, (dist ** 2 - l1 ** 2 - l2 ** 2) / (2 * l1 * l2))))
        q1 = math.atan2(y, x) - math.atan2(l2 * math.sin(q2), l1 + l2 * math.cos(q2))
        result = [q1, q2, 0.0, 0.0, 0.0, target_pose.theta]
        for i, (lo, hi) in enumerate(self._joint_limits):
            if i < len(result):
                result[i] = max(lo, min(hi, result[i]))
        return result

    async def forward_kinematics(self, joint_positions: list[float]) -> Pose2D:
        q1 = joint_positions[0] if len(joint_positions) > 0 else 0
        q2 = joint_positions[1] if len(joint_positions) > 1 else 0
        l1, l2 = 0.4, 0.3
        x = l1 * math.cos(q1) + l2 * math.cos(q1 + q2)
        y = l1 * math.sin(q1) + l2 * math.sin(q1 + q2)
        theta = q1 + q2
        return Pose2D(x=x, y=y, theta=theta)

    async def check_collision(self, joint_positions: list[float]) -> bool:
        return False

    def get_home_position(self) -> list[float]:
        return list(self._home_position)

    def get_stats(self) -> dict[str, Any]:
        return {
            "dof": len(self._joint_names),
            "joint_names": self._joint_names,
            "joint_limits": self._joint_limits,
        }


class RoboticsService:
    def __init__(self, simulation: bool = True):
        self._simulation = simulation
        self._robot_state = RobotState()
        self._robot_state.joint_state = JointState(
            joint_names=["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"],
            positions=[0.0, -1.57, 0.0, -1.57, 0.0, 0.0],
            velocities=[0.0] * 6,
            efforts=[0.0] * 6,
        )
        self._semantic_map = SemanticMap()
        self._path_planner = PathPlanner(self._semantic_map)
        self._navigator = Navigator(self._semantic_map, self._path_planner)
        self._motion_planner = MotionPlanner()
        logger.info(f"[ROBOTICS] RoboticsService initialized (simulation={simulation})")

    @property
    def robot_state(self) -> RobotState:
        return self._robot_state

    @property
    def semantic_map(self) -> SemanticMap:
        return self._semantic_map

    @property
    def navigator(self) -> Navigator:
        return self._navigator

    @property
    def motion_planner(self) -> MotionPlanner:
        return self._motion_planner

    async def navigate_to(self, location_name: str) -> dict[str, Any]:
        self._robot_state.mode = RobotMode.NAVIGATING
        result = await self._navigator.navigate_to(location_name, self._robot_state)
        self._robot_state.mode = RobotMode.IDLE
        return result

    async def emergency_stop(self):
        self._robot_state.mode = RobotMode.EMERGENCY_STOP
        self._robot_state.velocity = (0.0, 0.0)
        await self._navigator.cancel_navigation(self._robot_state)
        logger.warning("[ROBOTICS] EMERGENCY STOP activated")

    async def reset(self):
        self._robot_state = RobotState()
        self._robot_state.joint_state = JointState(
            joint_names=["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"],
            positions=[0.0, -1.57, 0.0, -1.57, 0.0, 0.0],
            velocities=[0.0] * 6,
            efforts=[0.0] * 6,
        )
        logger.info("[ROBOTICS] Robot state reset")

    def get_full_status(self) -> dict[str, Any]:
        return {
            "robot_state": self._robot_state.to_dict(),
            "semantic_map": self._semantic_map.get_stats(),
            "navigation": self._navigator.get_status(),
            "motion_planner": self._motion_planner.get_stats(),
            "simulation": self._simulation,
        }


_robotics_service: RoboticsService | None = None


def get_robotics_service() -> RoboticsService:
    global _robotics_service
    if _robotics_service is None:
        _robotics_service = RoboticsService(simulation=True)
    return _robotics_service
