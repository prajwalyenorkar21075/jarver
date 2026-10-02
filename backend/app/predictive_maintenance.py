"""Predictive maintenance engine for JARVIS.

Real time-series pipeline over data that actually exists:

    SENSORS → TIME SERIES → DATABASE → FEATURE EXTRACTION → ANOMALY DETECTION
            → TREND ANALYSIS → PREDICTIVE MAINTENANCE → ALERT → REPORT

Data sources (all real, no generated values):
  * PLC tags read through ``industrial_service`` (Modbus/OPC UA/MQTT)
  * Robot joint state from ``robotics_service``
  * Device telemetry collected from psutil for this host
  * Any series an operator posts explicitly to ``/api/maintenance/samples``

If there is not enough real data, the engine says so. An equipment health score
is only produced when it is backed by samples.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import statistics
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.maintenance")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jarvis_persistent.db"

# Minimum samples before a health judgement is allowed
MIN_SAMPLES_FOR_HEALTH = 20
MIN_SAMPLES_FOR_ANOMALY = 8

# Physics-free, documented engineering thresholds. These are defaults a site
# engineer overrides with real machine limits; they are never presented as
# measurements.
DEFAULT_THRESHOLDS = {
    "vibration_rms": {"warn": 4.5, "critical": 7.1, "unit": "mm/s"},
    "temperature": {"warn": 70.0, "critical": 85.0, "unit": "degC"},
    "motor_current": {"warn": 8.0, "critical": 11.0, "unit": "A"},
    "pressure": {"warn": 6.0, "critical": 8.0, "unit": "bar"},
    "cycle_time_ms": {"warn": 2500.0, "critical": 4000.0, "unit": "ms"},
}


@dataclass
class Sample:
    device_id: str
    signal: str
    value: float
    timestamp: float = field(default_factory=time.time)
    unit: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"device_id": self.device_id, "signal": self.signal, "value": self.value,
                "timestamp": self.timestamp, "unit": self.unit, "source": self.source}


@dataclass
class MaintenanceAlert:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    device_id: str = ""
    signal: str = ""
    severity: str = "info"
    kind: str = ""
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    raised_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "device_id": self.device_id, "signal": self.signal,
                "severity": self.severity, "kind": self.kind, "message": self.message,
                "evidence": self.evidence, "raised_at": self.raised_at}


class PredictiveMaintenanceEngine:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._alerts: list[MaintenanceAlert] = []
        self._thresholds = dict(DEFAULT_THRESHOLDS)
        self._ensure_schema()

    # ------------------------------------------------------------------ #
    # Storage
    # ------------------------------------------------------------------ #
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        signal TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT,
                        source TEXT,
                        timestamp REAL NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_device_signal "
                             "ON sensor_samples(device_id, signal, timestamp DESC)")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_alerts (
                        id TEXT PRIMARY KEY,
                        device_id TEXT,
                        signal TEXT,
                        severity TEXT,
                        kind TEXT,
                        message TEXT,
                        evidence TEXT,
                        raised_at REAL
                    )
                """)
                conn.commit()
            logger.info("[MAINTENANCE] sensor_samples table ready")
        except Exception as e:
            logger.warning(f"[MAINTENANCE] schema setup failed: {e}")

    def record_sample(self, device_id: str, signal: str, value: float,
                      unit: str = "", source: str = "") -> dict[str, Any]:
        if value is None:
            return {"success": False, "error": "value is required"}
        try:
            value = float(value)
        except (TypeError, ValueError):
            return {"success": False, "error": f"value must be numeric, got {value!r}"}
        if math.isnan(value) or math.isinf(value):
            return {"success": False, "error": "value must be a finite number"}

        timestamp = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sensor_samples (device_id, signal, value, unit, source, timestamp) "
                "VALUES (?,?,?,?,?,?)",
                (device_id, signal, value, unit, source, timestamp),
            )
            conn.commit()
        return {"success": True, "device_id": device_id, "signal": signal, "value": value,
                "timestamp": timestamp}

    def get_series(self, device_id: str, signal: str, limit: int = 500) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT timestamp, value, unit, source FROM sensor_samples "
                "WHERE device_id=? AND signal=? ORDER BY timestamp DESC LIMIT ?",
                (device_id, signal, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def list_series(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT device_id, signal, COUNT(*) AS samples, MIN(timestamp) AS first_seen,
                       MAX(timestamp) AS last_seen, AVG(value) AS mean_value
                FROM sensor_samples GROUP BY device_id, signal ORDER BY device_id, signal
            """).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Collection from real sources
    # ------------------------------------------------------------------ #
    def collect_from_plc(self, device_id: str, tag_map: dict[str, str] | None = None) -> dict[str, Any]:
        """Read live tags and store them as samples. Fails loudly when unreadable."""
        from .industrial_service import get_industrial_service

        service = get_industrial_service()
        device = service.get_device(device_id)
        if not device:
            return {"success": False, "error": f"Unknown device '{device_id}'"}

        mapping = tag_map or {t["tag"]: t.get("unit", "") for t in device.tags}
        stored, errors = [], []
        for tag, unit in mapping.items():
            result = service.read_tag(device_id, tag)
            if result.get("success"):
                reading = result["reading"]
                value = reading.get("value")
                if isinstance(value, bool):
                    value = 1.0 if value else 0.0
                if isinstance(value, (int, float)):
                    stored.append(self.record_sample(
                        device_id, tag, float(value), unit or reading.get("unit", ""),
                        source=f"plc:{device.protocol}",
                    ))
                else:
                    errors.append({"tag": tag, "error": f"non-numeric value {value!r}"})
            else:
                errors.append({"tag": tag, "error": result.get("error")})
        return {"success": len(stored) > 0, "stored": len(stored), "errors": errors,
                "device_id": device_id}

    def collect_from_robot(self) -> dict[str, Any]:
        """Sample robot joint positions/efforts and battery from the robotics service."""
        from .robotics_service import get_robotics_service

        service = get_robotics_service()
        state = service.robot_state
        stored = []
        for index, position in enumerate(state.joint_state.positions or []):
            name = (state.joint_state.joint_names[index]
                    if index < len(state.joint_state.joint_names) else f"joint_{index + 1}")
            stored.append(self.record_sample("robot", f"{name}.position", float(position),
                                             "rad", source="robotics_service"))
        for index, effort in enumerate(state.joint_state.efforts or []):
            name = (state.joint_state.joint_names[index]
                    if index < len(state.joint_state.joint_names) else f"joint_{index + 1}")
            stored.append(self.record_sample("robot", f"{name}.effort", float(effort),
                                             "Nm", source="robotics_service"))
        stored.append(self.record_sample("robot", "battery_level", float(state.battery_level),
                                         "%", source="robotics_service"))
        return {"success": True, "stored": len(stored), "simulation_mode": service.get_full_status().get("simulation")}

    def collect_host_telemetry(self) -> dict[str, Any]:
        """Sample this machine's real CPU/RAM/disk usage."""
        try:
            import psutil
        except ImportError:
            return {"success": False, "error": "psutil not installed"}
        stored = [
            self.record_sample("host", "cpu_percent", psutil.cpu_percent(interval=0.2), "%", "psutil"),
            self.record_sample("host", "ram_percent", psutil.virtual_memory().percent, "%", "psutil"),
            self.record_sample("host", "disk_percent", psutil.disk_usage("/").percent, "%", "psutil"),
        ]
        return {"success": True, "stored": len(stored)}

    # ------------------------------------------------------------------ #
    # Feature extraction / anomaly detection / trend
    # ------------------------------------------------------------------ #
    @staticmethod
    def extract_features(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0}
        features = {
            "count": len(values),
            "mean": statistics.fmean(values),
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "last": values[-1],
        }
        if len(values) > 1:
            features["stddev"] = statistics.pstdev(values)
            features["slope_per_sample"] = _linear_slope(values)
            mean = features["mean"]
            features["cv_percent"] = (features["stddev"] / mean * 100) if mean else 0.0
            features["rms"] = math.sqrt(sum(v * v for v in values) / len(values))
        else:
            features["stddev"] = 0.0
            features["slope_per_sample"] = 0.0
            features["cv_percent"] = 0.0
            features["rms"] = abs(values[0])
        return features

    def detect_anomalies(self, values: list[float], z_threshold: float = 3.0) -> dict[str, Any]:
        """Z-score outliers plus an IQR fence. Requires enough real samples."""
        if len(values) < MIN_SAMPLES_FOR_ANOMALY:
            return {
                "sufficient_data": False,
                "reason": f"{len(values)} samples available; {MIN_SAMPLES_FOR_ANOMALY} required for anomaly detection",
                "anomalies": [],
            }

        mean = statistics.fmean(values)
        stddev = statistics.pstdev(values)
        anomalies: list[dict[str, Any]] = []
        if stddev > 0:
            for index, value in enumerate(values):
                z = (value - mean) / stddev
                if abs(z) >= z_threshold:
                    anomalies.append({"index": index, "value": value, "z_score": round(z, 3),
                                      "method": "zscore"})

        sorted_values = sorted(values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[(3 * len(sorted_values)) // 4]
        iqr = q3 - q1
        if iqr > 0:
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            for index, value in enumerate(values):
                if value < low or value > high:
                    if not any(a["index"] == index for a in anomalies):
                        anomalies.append({"index": index, "value": value,
                                          "bounds": [round(low, 3), round(high, 3)],
                                          "method": "iqr"})

        return {
            "sufficient_data": True,
            "mean": round(mean, 4),
            "stddev": round(stddev, 4),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies[:50],
        }

    def analyze_trend(self, values: list[float]) -> dict[str, Any]:
        if len(values) < MIN_SAMPLES_FOR_ANOMALY:
            return {"sufficient_data": False,
                    "reason": f"{len(values)} samples available; {MIN_SAMPLES_FOR_ANOMALY} required for trend analysis"}
        slope = _linear_slope(values)
        mean = statistics.fmean(values)
        relative = (slope / mean * 100) if mean else 0.0
        if relative > 1.0:
            direction = "rising"
        elif relative < -1.0:
            direction = "falling"
        else:
            direction = "stable"
        return {
            "sufficient_data": True,
            "slope_per_sample": round(slope, 5),
            "relative_slope_percent": round(relative, 3),
            "direction": direction,
            "first": values[0],
            "last": values[-1],
            "change_percent": round((values[-1] - values[0]) / values[0] * 100, 3) if values[0] else None,
        }

    def threshold_check(self, signal: str, value: float) -> dict[str, Any]:
        thresholds = self._thresholds.get(signal)
        if not thresholds:
            return {"configured": False, "signal": signal, "value": value,
                    "note": "No threshold configured for this signal; set one from the machine datasheet."}
        if value >= thresholds["critical"]:
            status = "critical"
        elif value >= thresholds["warn"]:
            status = "warning"
        else:
            status = "normal"
        return {"configured": True, "signal": signal, "value": value, "status": status,
                "warn": thresholds["warn"], "critical": thresholds["critical"],
                "unit": thresholds.get("unit", "")}

    def set_threshold(self, signal: str, warn: float, critical: float, unit: str = "") -> dict[str, Any]:
        self._thresholds[signal] = {"warn": float(warn), "critical": float(critical), "unit": unit}
        return {"success": True, "signal": signal, "thresholds": self._thresholds[signal]}

    # ------------------------------------------------------------------ #
    # Equipment health
    # ------------------------------------------------------------------ #
    def equipment_health(self, device_id: str) -> dict[str, Any]:
        """Health score for a device, computed only from stored real samples."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT signal, COUNT(*) AS c FROM sensor_samples WHERE device_id=? GROUP BY signal",
                (device_id,),
            ).fetchall()
        signals = {r["signal"]: r["c"] for r in rows}
        total_samples = sum(signals.values())

        if total_samples < MIN_SAMPLES_FOR_HEALTH:
            return {
                "device_id": device_id,
                "health_score": None,
                "status": "insufficient_data",
                "message": (
                    f"Only {total_samples} real samples stored for '{device_id}'. "
                    f"{MIN_SAMPLES_FOR_HEALTH} are required before a health score is meaningful. "
                    "No score is invented."
                ),
                "signals": signals,
            }

        penalties: list[dict[str, Any]] = []
        for signal in signals:
            series = self.get_series(device_id, signal, limit=500)
            values = [s["value"] for s in series]
            if not values:
                continue
            latest = values[-1]
            check = self.threshold_check(signal, latest)
            if check.get("configured"):
                if check["status"] == "critical":
                    penalties.append({"signal": signal, "penalty": 40, "reason": "above critical threshold",
                                      "value": latest})
                elif check["status"] == "warning":
                    penalties.append({"signal": signal, "penalty": 15, "reason": "above warning threshold",
                                      "value": latest})
            trend = self.analyze_trend(values)
            if trend.get("sufficient_data") and trend["direction"] == "rising" and trend["relative_slope_percent"] > 5:
                penalties.append({"signal": signal, "penalty": 10, "reason": "strongly rising trend",
                                  "value": trend["relative_slope_percent"]})
            anomalies = self.detect_anomalies(values)
            if anomalies.get("sufficient_data") and anomalies.get("anomaly_count", 0) > 0:
                penalties.append({"signal": signal, "penalty": min(20, anomalies["anomaly_count"] * 5),
                                  "reason": f"{anomalies['anomaly_count']} anomalies detected",
                                  "value": anomalies["anomaly_count"]})

        score = max(0, 100 - sum(p["penalty"] for p in penalties))
        status = "healthy" if score >= 80 else "attention" if score >= 60 else "degraded" if score >= 40 else "critical"
        return {
            "device_id": device_id,
            "health_score": score,
            "status": status,
            "total_samples": total_samples,
            "signals": signals,
            "penalties": penalties,
            "based_on": "stored real samples only",
        }

    # ------------------------------------------------------------------ #
    # Analysis + recommendations
    # ------------------------------------------------------------------ #
    def analyze(self, device_id: str | None = None, persist_alerts: bool = True) -> dict[str, Any]:
        series_list = self.list_series()
        if device_id:
            series_list = [s for s in series_list if s["device_id"] == device_id]

        if not series_list:
            return {
                "success": False,
                "error": "No sensor samples stored. Collect from a PLC/robot/host first — "
                         "the engine never fabricates readings.",
                "signals_analyzed": 0,
                "alerts": [],
            }

        results: list[dict[str, Any]] = []
        new_alerts: list[MaintenanceAlert] = []

        for entry in series_list:
            dev, signal = entry["device_id"], entry["signal"]
            series = self.get_series(dev, signal, limit=500)
            values = [s["value"] for s in series]
            if not values:
                continue

            features = self.extract_features(values)
            anomalies = self.detect_anomalies(values)
            trend = self.analyze_trend(values)
            threshold = self.threshold_check(signal, values[-1])

            signal_result = {
                "device_id": dev,
                "signal": signal,
                "samples": len(values),
                "features": {k: round(v, 5) if isinstance(v, float) else v for k, v in features.items()},
                "anomalies": anomalies,
                "trend": trend,
                "threshold": threshold,
                "first_timestamp": series[0]["timestamp"],
                "last_timestamp": series[-1]["timestamp"],
            }
            results.append(signal_result)

            if threshold.get("configured"):
                if threshold["status"] == "critical":
                    new_alerts.append(MaintenanceAlert(
                        device_id=dev, signal=signal, severity="high", kind="threshold",
                        message=f"{signal} at {threshold['value']}{threshold['unit']} exceeds the critical limit "
                                f"of {threshold['critical']}{threshold['unit']}",
                        evidence=threshold,
                    ))
                elif threshold["status"] == "warning":
                    new_alerts.append(MaintenanceAlert(
                        device_id=dev, signal=signal, severity="medium", kind="threshold",
                        message=f"{signal} at {threshold['value']}{threshold['unit']} is above the warning limit "
                                f"of {threshold['warn']}{threshold['unit']}",
                        evidence=threshold,
                    ))
            if anomalies.get("sufficient_data") and anomalies.get("anomaly_count", 0) > 0:
                new_alerts.append(MaintenanceAlert(
                    device_id=dev, signal=signal, severity="medium", kind="anomaly",
                    message=f"{anomalies['anomaly_count']} statistical anomalies detected in {signal}",
                    evidence={"mean": anomalies["mean"], "stddev": anomalies["stddev"],
                              "first_anomaly": anomalies["anomalies"][0] if anomalies["anomalies"] else None},
                ))
            if trend.get("sufficient_data") and trend["direction"] == "rising" and trend["relative_slope_percent"] > 5:
                new_alerts.append(MaintenanceAlert(
                    device_id=dev, signal=signal, severity="low", kind="trend",
                    message=f"{signal} is rising steadily ({trend['relative_slope_percent']}% per sample); "
                            "monitor for wear",
                    evidence=trend,
                ))

        if persist_alerts and new_alerts:
            self._alerts.extend(new_alerts)
            self._persist_alerts(new_alerts)

        recommendations = self._recommendations(results)
        health = {d: self.equipment_health(d) for d in {r["device_id"] for r in results}}

        return {
            "success": True,
            "analyzed_at": time.time(),
            "signals_analyzed": len(results),
            "results": results,
            "alerts": [a.to_dict() for a in new_alerts],
            "recommendations": recommendations,
            "equipment_health": health,
            "data_note": "All statistics are computed from stored real samples; nothing is simulated.",
        }

    def _recommendations(self, results: list[dict[str, Any]]) -> list[str]:
        recommendations: list[str] = []
        for result in results:
            signal = result["signal"]
            threshold = result.get("threshold", {})
            trend = result.get("trend", {})
            anomalies = result.get("anomalies", {})
            if threshold.get("configured") and threshold["status"] == "critical":
                recommendations.append(
                    f"Inspect {result['device_id']} for {signal} immediately — reading is above the "
                    f"critical limit. Check bearings, lubrication and alignment before the next cycle."
                )
            elif threshold.get("configured") and threshold["status"] == "warning":
                recommendations.append(
                    f"Schedule a check of {signal} on {result['device_id']} at the next planned stop."
                )
            if anomalies.get("sufficient_data") and anomalies.get("anomaly_count", 0) >= 3:
                recommendations.append(
                    f"{signal} on {result['device_id']} shows repeated outliers — verify the sensor "
                    "and its wiring before concluding the machine is at fault."
                )
            if trend.get("sufficient_data") and trend["direction"] == "rising" and trend["relative_slope_percent"] > 10:
                recommendations.append(
                    f"{signal} on {result['device_id']} is climbing quickly — plan a maintenance window."
                )
        if not recommendations:
            recommendations.append(
                "No threshold, anomaly or trend condition was breached in the stored data. "
                "Keep collecting samples so a baseline can be established."
            )
        return recommendations

    def _persist_alerts(self, alerts: list[MaintenanceAlert]):
        try:
            with self._conn() as conn:
                for alert in alerts:
                    conn.execute(
                        "INSERT OR REPLACE INTO maintenance_alerts "
                        "(id, device_id, signal, severity, kind, message, evidence, raised_at) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (alert.id, alert.device_id, alert.signal, alert.severity, alert.kind,
                         alert.message, json.dumps(alert.evidence), alert.raised_at),
                    )
                conn.commit()
        except Exception as e:
            logger.debug(f"[MAINTENANCE] alert persist skipped: {e}")

    def get_alerts(self, limit: int = 50, device_id: str | None = None) -> list[dict[str, Any]]:
        try:
            with self._conn() as conn:
                if device_id:
                    rows = conn.execute(
                        "SELECT * FROM maintenance_alerts WHERE device_id=? "
                        "ORDER BY raised_at DESC LIMIT ?", (device_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM maintenance_alerts ORDER BY raised_at DESC LIMIT ?", (limit,),
                    ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return [a.to_dict() for a in self._alerts[-limit:]]

    def get_status(self) -> dict[str, Any]:
        series = self.list_series()
        total_samples = sum(s["samples"] for s in series)
        return {
            "tracked_signals": len(series),
            "total_samples": total_samples,
            "devices": sorted({s["device_id"] for s in series}),
            "alerts_stored": len(self.get_alerts(limit=1000)),
            "thresholds_configured": sorted(self._thresholds.keys()),
            "min_samples_for_health": MIN_SAMPLES_FOR_HEALTH,
            "min_samples_for_anomaly": MIN_SAMPLES_FOR_ANOMALY,
            "data_policy": "real samples only; no synthetic readings are ever generated",
        }


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = statistics.fmean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


_engine: PredictiveMaintenanceEngine | None = None


def get_maintenance_engine() -> PredictiveMaintenanceEngine:
    global _engine
    if _engine is None:
        _engine = PredictiveMaintenanceEngine()
    return _engine
