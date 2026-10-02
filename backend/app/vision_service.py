"""Real-time Computer Vision service for JARVIS.

Provides: camera input, object detection, object tracking, scene understanding,
visual events, confidence scores. Supports simulation mode when no camera is available.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from collections import defaultdict

import numpy as np

logger = logging.getLogger("jarvis.vision")


class DetectionModel(str, Enum):
    YOLO_V8_NANO = "yolov8n"
    YOLO_V8_SMALL = "yolov8s"
    YOLO_V8_MEDIUM = "yolov8m"
    SIMULATION = "simulation"


@dataclass
class Detection:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    class_name: str = ""
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    center: tuple[int, int] = (0, 0)
    track_id: int | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "center": list(self.center),
            "track_id": self.track_id,
            "timestamp": self.timestamp,
        }


@dataclass
class VisualEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: str = ""
    description: str = ""
    objects_involved: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "description": self.description,
            "objects_involved": self.objects_involved,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class VisionFrame:
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    width: int = 0
    height: int = 0
    detections: list[Detection] = field(default_factory=list)
    events: list[VisualEvent] = field(default_factory=list)
    scene_description: str = ""
    fps: float = 0.0
    processing_ms: float = 0.0
    source: str = "camera"

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
            "detections": [d.to_dict() for d in self.detections],
            "events": [e.to_dict() for e in self.events],
            "scene_description": self.scene_description,
            "fps": round(self.fps, 1),
            "processing_ms": round(self.processing_ms, 1),
            "source": self.source,
            "detection_count": len(self.detections),
        }


class CameraInput:
    def __init__(self, camera_id: int = 0, simulation: bool = True):
        self._camera_id = camera_id
        self._simulation = simulation
        self._cap = None
        self._running = False
        self._frame_count = 0
        self._last_frame: np.ndarray | None = None
        logger.info(f"[VISION] CameraInput initialized (simulation={simulation})")

    async def start(self):
        if self._simulation:
            self._running = True
            logger.info("[VISION] Camera started in simulation mode")
            return True

        try:
            import cv2
            self._cap = cv2.VideoCapture(self._camera_id)
            if self._cap.isOpened():
                self._running = True
                logger.info(f"[VISION] Camera {self._camera_id} opened")
                return True
            else:
                logger.warning("[VISION] Camera not available, falling back to simulation")
                self._simulation = True
                self._running = True
                return True
        except Exception as e:
            logger.warning(f"[VISION] Camera init failed: {e}, using simulation")
            self._simulation = True
            self._running = True
            return True

    async def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("[VISION] Camera stopped")

    async def capture_frame(self) -> np.ndarray | None:
        if not self._running:
            return None

        if self._simulation:
            return self._generate_simulation_frame()

        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                self._frame_count += 1
                self._last_frame = frame
                return frame
        return None

    def _generate_simulation_frame(self) -> np.ndarray:
        self._frame_count += 1
        h, w = 480, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = (40, 40, 40)

        t = self._frame_count * 0.05
        num_objects = 3
        for i in range(num_objects):
            cx = int(w * (0.2 + 0.3 * i) + 30 * np.sin(t + i))
            cy = int(h * 0.5 + 20 * np.cos(t + i * 0.7))
            radius = 30 + i * 10
            color = [(0, 255, 0), (255, 0, 0), (0, 0, 255)][i % 3]
            cv2_circle(frame, (cx, cy), radius, color, -1)

        self._last_frame = frame
        return frame

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def frame_count(self) -> int:
        return self._frame_count


def cv2_circle(frame, center, radius, color, thickness):
    try:
        import cv2
        cv2.circle(frame, center, radius, color, thickness)
    except ImportError:
        pass


class ObjectDetector:
    def __init__(self, model_name: str = "simulation", confidence_threshold: float = 0.5):
        self._model_name = model_name
        self._confidence_threshold = confidence_threshold
        self._model = None
        self._simulation = model_name == "simulation"
        self._load_model()

    def _load_model(self):
        if self._simulation:
            logger.info("[VISION] Object detector in simulation mode")
            return

        try:
            from ultralytics import YOLO
            self._model = YOLO(f"{self._model_name}.pt")
            logger.info(f"[VISION] Loaded YOLO model: {self._model_name}")
        except Exception as e:
            logger.warning(f"[VISION] YOLO load failed: {e}, using simulation")
            self._simulation = True

    async def detect(self, frame: np.ndarray) -> list[Detection]:
        if frame is None:
            return []

        if self._simulation:
            return self._simulate_detections(frame)

        try:
            results = self._model(frame, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf < self._confidence_threshold:
                        continue
                    cls_id = int(box.cls[0])
                    cls_name = r.names[cls_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detections.append(Detection(
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=((x1 + x2) // 2, (y1 + y2) // 2),
                    ))
            return detections
        except Exception as e:
            logger.error(f"[VISION] Detection failed: {e}")
            return []

    def _simulate_detections(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        t = time.time()
        detections = []

        classes = ["person", "chair", "monitor"]
        colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255)]

        for i, (cls, color) in enumerate(zip(classes, colors)):
            cx = int(w * (0.2 + 0.3 * i) + 30 * np.sin(t + i))
            cy = int(h * 0.5 + 20 * np.cos(t + i * 0.7))
            size = 60 + i * 20
            conf = 0.85 + 0.1 * np.sin(t * 0.5 + i)
            detections.append(Detection(
                class_name=cls,
                confidence=round(conf, 3),
                bbox=(cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2),
                center=(cx, cy),
                track_id=i + 1,
            ))
        return detections


class ObjectTracker:
    def __init__(self, max_disappeared: int = 30):
        self._tracks: dict[int, dict[str, Any]] = {}
        self._next_id = 1
        self._max_disappeared = max_disappeared

    async def update(self, detections: list[Detection]) -> list[Detection]:
        if not detections:
            for tid in list(self._tracks.keys()):
                self._tracks[tid]["disappeared"] += 1
                if self._tracks[tid]["disappeared"] > self._max_disappeared:
                    del self._tracks[tid]
            return detections

        for det in detections:
            if det.track_id is None:
                matched = self._match_track(det)
                if matched is not None:
                    det.track_id = matched
                    self._tracks[matched]["disappeared"] = 0
                    self._tracks[matched]["last_seen"] = time.time()
                else:
                    det.track_id = self._next_id
                    self._tracks[self._next_id] = {
                        "disappeared": 0,
                        "last_seen": time.time(),
                        "class_name": det.class_name,
                    }
                    self._next_id += 1
        return detections

    def _match_track(self, detection: Detection) -> int | None:
        best_dist = float("inf")
        best_id = None
        for tid, track in self._tracks.items():
            if track["disappeared"] > self._max_disappeared:
                continue
            dist = abs(detection.center[0] - track.get("last_center", (0, 0))[0])
            if dist < best_dist and dist < 100:
                best_dist = dist
                best_id = tid
        if best_id is not None:
            self._tracks[best_id]["last_center"] = detection.center
        return best_id


class VisionService:
    def __init__(self, simulation: bool = True, model: str = "simulation"):
        self._camera = CameraInput(simulation=simulation)
        self._detector = ObjectDetector(model_name=model)
        self._tracker = ObjectTracker()
        self._running = False
        self._frame_history: list[VisionFrame] = []
        self._max_history = 60
        self._total_frames = 0
        self._events: list[VisualEvent] = []
        self._prev_classes: set[str] = set()
        logger.info(f"[VISION] VisionService initialized (simulation={simulation})")

    async def start(self):
        await self._camera.start()
        self._running = True
        logger.info("[VISION] VisionService started")

    async def stop(self):
        self._running = False
        await self._camera.stop()
        logger.info("[VISION] VisionService stopped")

    async def process_frame(self, frame: np.ndarray | None = None) -> VisionFrame:
        start_time = time.time()

        if frame is None:
            frame = await self._camera.capture_frame()

        vf = VisionFrame(source="simulation" if self._camera._simulation else "camera")

        if frame is None:
            vf.processing_ms = (time.time() - start_time) * 1000
            return vf

        vf.width = frame.shape[1]
        vf.height = frame.shape[0]

        detections = await self._detector.detect(frame)
        detections = await self._tracker.update(detections)
        vf.detections = detections

        vf.events = self._detect_events(detections)

        vf.scene_description = self._describe_scene(detections)

        self._total_frames += 1
        elapsed = time.time() - start_time
        vf.processing_ms = elapsed * 1000
        vf.fps = 1.0 / elapsed if elapsed > 0 else 0.0

        self._frame_history.append(vf)
        if len(self._frame_history) > self._max_history:
            self._frame_history = self._frame_history[-self._max_history:]

        return vf

    def _detect_events(self, detections: list[Detection]) -> list[VisualEvent]:
        events = []
        current_classes = {d.class_name for d in detections}

        new_objects = current_classes - self._prev_classes
        for cls in new_objects:
            events.append(VisualEvent(
                event_type="object_appeared",
                description=f"New {cls} detected in scene",
                objects_involved=[cls],
                confidence=0.9,
            ))

        gone_objects = self._prev_classes - current_classes
        for cls in gone_objects:
            events.append(VisualEvent(
                event_type="object_disappeared",
                description=f"{cls} no longer in scene",
                objects_involved=[cls],
                confidence=0.8,
            ))

        self._prev_classes = current_classes
        self._events.extend(events)
        if len(self._events) > 100:
            self._events = self._events[-100:]
        return events

    def _describe_scene(self, detections: list[Detection]) -> str:
        if not detections:
            return "No objects detected in the scene"
        counts: dict[str, int] = defaultdict(int)
        for d in detections:
            counts[d.class_name] += 1
        parts = [f"{count} {cls}{'s' if count > 1 else ''}" for cls, count in counts.items()]
        return f"Scene contains: {', '.join(parts)}"

    async def run_continuous(self, callback=None):
        while self._running:
            vf = await self.process_frame()
            if callback:
                await callback(vf)
            await asyncio.sleep(0.033)

    def get_latest_frame(self) -> dict[str, Any] | None:
        if self._frame_history:
            return self._frame_history[-1].to_dict()
        return None

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "total_frames": self._total_frames,
            "camera_active": self._camera.is_running,
            "simulation_mode": self._camera._simulation,
            "detector_model": self._detector._model_name,
            "active_tracks": len(self._tracker._tracks),
            "recent_events": len(self._events),
            "latest_frame": self._frame_history[-1].to_dict() if self._frame_history else None,
        }


_vision_service: VisionService | None = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService(simulation=True)
    return _vision_service
