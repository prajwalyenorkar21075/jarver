"""Digital Twin + Robot Cell Inspection for JARVIS.

    REAL ROBOT / PLC / SENSORS
    ↕
    DIGITAL TWIN
    ↕
    ROS2
    ↕
    J.A.R.V.I.S. AI

Expected State vs Actual State comparison with anomaly flagging.
Robot cell inspection correlates: robot state, joints, PLC state, sensor
state, camera/vision, alarms, network/security status, machine status.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("jarvis.twin")


@dataclass
class TwinSnapshot:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "timestamp": self.timestamp, "source": self.source,
                "state": self.state, "simulated": self.simulated}


class DigitalTwin:
    """Keeps expected vs actual state, flags deviations."""

    def __init__(self, max_history: int = 200):
        self._expected: dict[str, TwinSnapshot] = {}
        self._actual: dict[str, TwinSnapshot] = {}
        self._deviations: list[dict[str, Any]] = []
        self._max_history = max_history

    def set_expected(self, entity: str, state: dict[str, Any], source: str = "operator") -> dict[str, Any]:
        snap = TwinSnapshot(source=source, state=state, simulated=False)
        self._expected[entity] = snap
        return snap.to_dict()

    def update_actual(self, entity: str, state: dict[str, Any], source: str = "live",
                      simulated: bool = False) -> dict[str, Any]:
        snap = TwinSnapshot(source=source, state=state, simulated=simulated)
        self._actual[entity] = snap
        deviation = self.compare(entity)
        return {"actual": snap.to_dict(), "deviation": deviation}

    def compare(self, entity: str, joint_tolerance_rad: float = 0.05,
                numeric_tolerance: float = 0.05) -> dict[str, Any]:
        expected = self._expected.get(entity)
        actual = self._actual.get(entity)
        if not expected or not actual:
            return {"entity": entity, "compared": False,
                    "reason": "need both expected and actual state before comparing"}
        mismatches: list[dict[str, Any]] = []
        _compare_recursive(expected.state, actual.state, "", mismatches,
                           joint_tolerance_rad, numeric_tolerance)
        result = {
            "entity": entity,
            "compared": True,
            "match": len(mismatches) == 0,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches[:20],
            "expected_at": expected.timestamp,
            "actual_at": actual.timestamp,
            "actual_simulated": actual.simulated,
        }
        if mismatches:
            self._deviations.append({**result, "detected_at": time.time()})
            if len(self._deviations) > self._max_history:
                self._deviations = self._deviations[-self._max_history:]
        return result

    def get_state(self, entity: str) -> dict[str, Any]:
        return {
            "entity": entity,
            "expected": self._expected[entity].to_dict() if entity in self._expected else None,
            "actual": self._actual[entity].to_dict() if entity in self._actual else None,
        }

    def list_entities(self) -> list[str]:
        return sorted(set(self._expected) | set(self._actual))

    def deviations(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._deviations[-limit:]

    def get_status(self) -> dict[str, Any]:
        return {"entities": self.list_entities(),
                "expected_count": len(self._expected), "actual_count": len(self._actual),
                "deviation_count": len(self._deviations)}


def _compare_recursive(expected: Any, actual: Any, path: str,
                       out: list[dict[str, Any]], tol: float, num_tol: float):
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected:
            _compare_recursive(expected.get(key), actual.get(key, "__missing__"),
                               f"{path}.{key}" if path else str(key), out, tol, num_tol)
        return
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        for i, (e, a) in enumerate(zip(expected, actual)):
            _compare_recursive(e, a, f"{path}[{i}]", out, tol, num_tol)
        if len(expected) != len(actual):
            out.append({"path": path, "expected": f"len={len(expected)}",
                        "actual": f"len={len(actual)}", "kind": "length"})
        return
    if actual == "__missing__":
        out.append({"path": path, "expected": expected, "actual": "missing", "kind": "missing"})
        return
    if isinstance(expected, bool) or isinstance(actual, bool):
        if bool(expected) != bool(actual):
            out.append({"path": path, "expected": expected, "actual": actual, "kind": "boolean"})
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        tolerance = tol if "joint" in path.lower() or "position" in path.lower() else num_tol
        base = max(abs(float(expected)), 1e-9)
        if abs(float(actual) - float(expected)) / base > tolerance and abs(float(actual) - float(expected)) > tolerance:
            out.append({"path": path, "expected": expected, "actual": actual, "kind": "numeric"})
        return
    if expected != actual:
        out.append({"path": path, "expected": expected, "actual": actual, "kind": "value"})


class RobotCellInspector:
    """Correlates the whole cell into one verified report."""

    async def inspect(self, cell: str = "robot_cell_1", run_vision: bool = False) -> dict[str, Any]:
        started = time.time()
        sections: dict[str, Any] = {}
        errors: list[str] = []

        # 1-2. Robot state + joints (real service)
        try:
            from .robotics_service import get_robotics_service
            robot = get_robotics_service()
            full = robot.get_full_status()
            sections["robot"] = full["robot_state"]
            sections["robot_simulation"] = full.get("simulation", True)
            sections["navigation"] = full.get("navigation", {})
        except Exception as e:
            errors.append(f"robot: {e}")
            sections["robot"] = None

        # 3. PLC / automation state (real reads; honest failures)
        try:
            from .industrial_service import get_industrial_service
            ind = get_industrial_service()
            devices = ind.list_devices(cell=cell) or ind.list_devices()
            plc_sections = []
            for device in devices:
                if device.get("kind") in ("plc", "hmi", "scada"):
                    plc_sections.append(ind.machine_state(device["id"]))
            sections["plc"] = plc_sections
            sections["alarms"] = ind.active_alarms()
            sections["industrial_mode"] = ind.control_mode
        except Exception as e:
            errors.append(f"plc: {e}")
            sections["plc"] = []

        # 4. Sensor values = tag histories + host telemetry where present
        try:
            from .predictive_maintenance import get_maintenance_engine
            maint = get_maintenance_engine()
            sections["sensor_series"] = maint.list_series()
        except Exception as e:
            errors.append(f"sensors: {e}")
            sections["sensor_series"] = []

        # 5-6. Camera + vision
        try:
            from .vision_service import get_vision_service
            vision = get_vision_service()
            if run_vision:
                frame = await vision.process_frame()
                sections["vision"] = frame.to_dict()
            else:
                latest = vision.get_latest_frame()
                sections["vision"] = latest or {"status": "no frame processed yet — request run_vision=true"}
            sections["vision_stats"] = vision.get_stats()
        except Exception as e:
            errors.append(f"vision: {e}")
            sections["vision"] = None

        # 7. Machine alarms already in sections["alarms"]

        # 8. Network/security status (real DB-backed summary)
        try:
            from .cybersecurity import get_security_db, get_alert_manager
            db = get_security_db()
            alerts = get_alert_manager()
            stats = db.get_security_stats()
            sections["security"] = {
                "alert_summary": alerts.get_alert_summary(),
                "security_stats": stats,
            }
        except Exception as e:
            errors.append(f"security: {e}")
            sections["security"] = None

        # 9-11. Correlate + anomaly detect + validate
        findings: list[dict[str, Any]] = []
        if sections.get("alarms"):
            for alarm in sections["alarms"]:
                findings.append({"severity": alarm.get("severity", "medium"), "area": "alarms",
                                 "message": f"Active alarm {alarm.get('code')}: {alarm.get('message')}"})
        for plc in sections.get("plc") or []:
            if plc.get("state") in ("emergency_stop", "fault"):
                findings.append({"severity": "high", "area": "plc",
                                 "message": f"{plc.get('device_id')} reports state={plc.get('state')}"})
            for err in plc.get("errors") or []:
                findings.append({"severity": "low", "area": "plc",
                                 "message": f"Unreadable tag {err.get('tag')}: {(err.get('error') or '')[:100]}"})
        sec = sections.get("security") or {}
        active_alerts = (sec.get("alert_summary") or {}).get("total_active", 0)
        if active_alerts:
            findings.append({"severity": "medium", "area": "security",
                             "message": f"{active_alerts} active security alerts — see security dashboard"})
        if sections.get("robot_simulation"):
            findings.append({"severity": "info", "area": "robot",
                             "message": "Robot data comes from the kinematic simulation (no ROS2 hardware linked)"})
        vision_data = sections.get("vision") or {}
        for det in vision_data.get("detections", []) or []:
            if det.get("confidence", 1) < 0.5:
                findings.append({"severity": "low", "area": "vision",
                                 "message": f"Low-confidence detection: {det.get('class_name')} ({det.get('confidence')})"})

        validated = _validate_sections(sections)

        report = {
            "report_id": str(uuid.uuid4())[:10],
            "cell": cell,
            "inspected_at": time.time(),
            "duration_ms": round((time.time() - started) * 1000, 2),
            "sections": sections,
            "findings": findings,
            "finding_count": len(findings),
            "validation": validated,
            "errors": errors,
            "verdict": _verdict(findings),
        }
        try:
            from .core.observability import get_observability
            trace = get_observability().start_trace(
                user_input=f"inspect robot cell {cell}", intent="robot_cell_inspection",
                agent="robot_cell_inspector", tool="inspect", source="robot_cell_inspector")
            trace.finish("completed", {"report_id": report["report_id"],
                                       "findings": len(findings), "verdict": report["verdict"]})
            trace.validation_status = "validated" if validated["ok"] else "partial"
            trace.validation_detail = validated["summary"]
            get_observability().record(trace)
        except Exception:
            pass
        return report


def _validate_sections(sections: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "robot_present": sections.get("robot") is not None,
        "plc_read_attempted": isinstance(sections.get("plc"), list),
        "vision_present": sections.get("vision") is not None,
        "security_present": sections.get("security") is not None,
    }
    ok = all(checks.values())
    return {"ok": ok, "checks": checks,
            "summary": "all sections collected" if ok else
                       f"missing: {[k for k, v in checks.items() if not v]}"}


def _verdict(findings: list[dict[str, Any]]) -> str:
    severities = [f.get("severity") for f in findings]
    if "high" in severities or "critical" in severities:
        return "attention required — high-severity findings present"
    if "medium" in severities:
        return "operational with warnings"
    return "nominal — no actionable findings"


_twin: DigitalTwin | None = None
_inspector: RobotCellInspector | None = None


def get_digital_twin() -> DigitalTwin:
    global _twin
    if _twin is None:
        _twin = DigitalTwin()
    return _twin


def get_cell_inspector() -> RobotCellInspector:
    global _inspector
    if _inspector is None:
        _inspector = RobotCellInspector()
    return _inspector
