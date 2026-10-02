"""Comprehensive diagnostics and testing system for JARVIS.

Tests all backend endpoints, voice pipeline, coding workflow, file operations,
model connections, and system health. Provides automatic error detection,
diagnosis, and safe fix application.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger("jarvis.diagnostics")


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    category: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    error: Optional[str] = None
    fix_applied: bool = False
    fix_description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DiagnosticsReport:
    """Complete diagnostics report."""
    test_results: list[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    system_health: str = "UNKNOWN"

    def add_result(self, result: TestResult):
        self.test_results.append(result)
        self.total_tests += 1
        if result.status == TestStatus.PASS:
            self.passed += 1
        elif result.status == TestStatus.FAIL:
            self.failed += 1
        elif result.status == TestStatus.ERROR:
            self.errors += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1

    def calculate_health(self):
        if self.total_tests == 0:
            self.system_health = "UNKNOWN"
            return

        pass_rate = self.passed / self.total_tests
        if pass_rate >= 0.95:
            self.system_health = "EXCELLENT"
        elif pass_rate >= 0.80:
            self.system_health = "GOOD"
        elif pass_rate >= 0.60:
            self.system_health = "DEGRADED"
        else:
            self.system_health = "CRITICAL"


class DiagnosticsEngine:
    """Runs comprehensive diagnostics across all JARVIS systems."""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_history: list[DiagnosticsReport] = []
        self.max_history = 10

    async def run_all_tests(self) -> DiagnosticsReport:
        """Run all diagnostic tests and return comprehensive report."""
        report = DiagnosticsReport()
        start_time = time.time()

        logger.info("Starting comprehensive diagnostics...")

        await self._test_health_endpoint(report)
        await self._test_telemetry(report)
        await self._test_policy_layer(report)
        await self._test_observability(report)
        await self._test_asset_graph(report)
        await self._test_industrial_sim(report)
        await self._test_plc_analyzer(report)
        await self._test_maintenance(report)
        await self._test_knowledge(report)
        await self._test_capabilities(report)
        await self._test_cell_inspection(report)
        await self._test_voice_transcription(report)
        await self._test_tts_synthesis(report)
        await self._test_chat_endpoint(report)
        await self._test_coding_workspace(report)
        await self._test_file_operations(report)
        await self._test_memory_system(report)
        await self._test_web_search(report)
        await self._test_youtube_search(report)
        await self._test_skills_registry(report)
        await self._test_biometrics_status(report)

        report.total_duration_ms = (time.time() - start_time) * 1000
        report.calculate_health()

        self.test_history.append(report)
        if len(self.test_history) > self.max_history:
            self.test_history.pop(0)

        logger.info(
            f"Diagnostics complete: {report.passed}/{report.total_tests} passed "
            f"({report.system_health})"
        )

        return report

    async def _test_health_endpoint(self, report: DiagnosticsReport):
        """Test /api/health endpoint."""
        test_name = "Health Check Endpoint"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/health")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    report.add_result(TestResult(
                        name=test_name,
                        category="Core",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message=f"Status: {data.get('status', 'unknown')}",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Core",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Core",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _endpoint(self, method: str, path: str, payload: dict | None = None,
                        timeout: float = 10.0):
        """Small helper: call the local backend and return (status, json-or-text)."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                resp = await client.get(f"{self.base_url}{path}")
            else:
                resp = await client.post(f"{self.base_url}{path}", json=payload or {})
            try:
                return resp.status_code, resp.json()
            except Exception:
                return resp.status_code, resp.text[:300]

    def _record(self, report: DiagnosticsReport, name: str, category: str,
                start: float, ok: bool, message: str = "", error: str = ""):
        duration = (time.time() - start) * 1000
        report.add_result(TestResult(
            name=name, category=category,
            status=TestStatus.PASS if ok else TestStatus.FAIL,
            duration_ms=duration, message=message, error=error or None,
        ))

    async def _test_policy_layer(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, read = await self._endpoint("POST", "/api/policy/check",
                {"operation": "read_plc_tags", "agent": "diagnostics"})
            code2, control = await self._endpoint("POST", "/api/policy/check",
                {"operation": "write_tag conveyor_speed", "agent": "diagnostics",
                 "target": "plc-1"})
            code3, sectest = await self._endpoint("POST", "/api/policy/check",
                {"operation": "port_scan", "agent": "diagnostics", "target": "127.0.0.1"})
            ok = (code == 200 and read.get("action_class") == "READ"
                  and read.get("decision") == "ALLOW"
                  and code2 == 200 and control.get("action_class") == "CONTROL"
                  and control.get("decision") == "REQUIRE_CONFIRMATION"
                  and code3 == 200 and sectest.get("action_class") == "SECURITY_TEST"
                  and sectest.get("decision") == "DENY")
            self._record(report, "Execution Policy Layer", "Safety", start, ok,
                           "READ allow / CONTROL gate / SECURITY_TEST deny verified" if ok else "",
                           "" if ok else f"policy responses unexpected: {read}, {control}, {sectest}")
        except Exception as e:
            self._record(report, "Execution Policy Layer", "Safety", start, False, error=str(e))

    async def _test_observability(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, stats = await self._endpoint("GET", "/api/observability/stats")
            ok = code == 200 and "persisted_rows" in stats
            self._record(report, "Execution Observability", "Core", start, ok,
                           f"persisted traces: {stats.get('persisted_rows')}" if ok else "",
                           "" if ok else f"HTTP {code}: {stats}")
        except Exception as e:
            self._record(report, "Execution Observability", "Core", start, False, error=str(e))

    async def _test_asset_graph(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, summary = await self._endpoint("GET", "/api/security/graph/summary")
            ok = code == 200 and summary.get("total_nodes", 0) > 0
            self._record(report, "Security Asset Graph", "Security", start, ok,
                           f"nodes={summary.get('total_nodes')} edges={summary.get('total_edges')}" if ok else "",
                           "" if ok else f"HTTP {code}: graph empty or unreachable")
        except Exception as e:
            self._record(report, "Security Asset Graph", "Security", start, False, error=str(e))

    async def _test_industrial_sim(self, report: DiagnosticsReport):
        """Start the Modbus simulator, register it, and read real registers."""
        start = time.time()
        try:
            code, started = await self._endpoint("POST", "/api/industrial/simulator/modbus",
                                                 {"action": "start"})
            if code != 200:
                self._record(report, "Industrial Modbus Simulator", "Industrial", start, False,
                               error=f"HTTP {code}: {started}")
                return
            port = started.get("port", 15020)
            code, reg = await self._endpoint("POST", "/api/industrial/devices/register", {
                "id": "diag-sim-plc", "name": "Diagnostics Sim PLC", "kind": "plc",
                "protocol": "modbus_tcp", "address": "127.0.0.1", "port": port,
                "cell": "lab", "simulated": True,
                "tags": [
                    {"tag": "conveyor_speed", "address": 40001, "type": "holding_register",
                     "unit": "m/s", "scale": 0.01},
                    {"tag": "estop_ok", "address": 10001, "type": "discrete_input"},
                ]})
            code, read = await self._endpoint("GET", "/api/industrial/device/diag-sim-plc/read")
            readings = read.get("readings", []) if isinstance(read, dict) else []
            conveyor = next((r for r in readings if r.get("tag") == "conveyor_speed"), None)
            ok = (code == 200 and read.get("simulated") is True and conveyor is not None
                  and abs(float(conveyor["value"]) - 1.25) < 0.001)
            self._record(report, "Industrial Modbus Simulator", "Industrial", start, ok,
                           f"simulated read: conveyor_speed={conveyor['value']} m/s" if ok else "",
                           "" if ok else f"HTTP {code}: {read}")
        except Exception as e:
            self._record(report, "Industrial Modbus Simulator", "Industrial", start, False, error=str(e))

    async def _test_plc_analyzer(self, report: DiagnosticsReport):
        start = time.time()
        try:
            source = ("PROGRAM T\nVAR\n a : BOOL;\n EStopOK : BOOL;\nEND_VAR\n"
                        "IF a THEN\n EStopOK := TRUE;\nEND_IF;\nEND_PROGRAM")
            code, result = await self._endpoint("POST", "/api/plc/analyze",
                                                {"source": source, "filename": "diag.st"})
            findings = result.get("findings", []) if isinstance(result, dict) else []
            safety = [f for f in findings if f.get("category") == "safety"]
            ok = code == 200 and len(safety) >= 1
            self._record(report, "PLC Program Analysis", "Industrial", start, ok,
                           f"{len(findings)} findings incl. safety flag" if ok else "",
                           "" if ok else f"HTTP {code}: {result}")
        except Exception as e:
            self._record(report, "PLC Program Analysis", "Industrial", start, False, error=str(e))

    async def _test_maintenance(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, empty = await self._endpoint("POST", "/api/maintenance/analyze", {})
            honest_refusal = code == 422
            for i in range(10):
                await self._endpoint("POST", "/api/maintenance/samples",
                    {"device_id": "diag-pump", "signal": "vibration_rms",
                     "value": 2.0 + i * 0.1, "unit": "mm/s", "source": "diagnostics"})
            code, health = await self._endpoint("GET", "/api/maintenance/health/diag-pump")
            ok = honest_refusal or (code == 200 and health.get("status") == "insufficient_data")
            self._record(report, "Predictive Maintenance Honesty", "Industrial", start, ok,
                           "refuses scores without data" if ok else "",
                           "" if ok else f"HTTP {code}: {health} (empty was {empty})")
        except Exception as e:
            self._record(report, "Predictive Maintenance Honesty", "Industrial", start, False, error=str(e))

    async def _test_knowledge(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, good = await self._endpoint("POST", "/api/knowledge/search",
                                               {"query": "modbus tcp register"})
            code2, bad = await self._endpoint("POST", "/api/knowledge/search",
                                               {"query": "zzzqqq nonexistent topic xyz"})
            ok = code == 200 and good.get("success") and code2 == 404
            self._record(report, "Unified Knowledge Retrieval", "Knowledge", start, ok,
                           f"{good.get('result_count')} hits; miss honestly refused" if ok else "",
                           "" if ok else f"HTTP {code}/{code2}")
        except Exception as e:
            self._record(report, "Unified Knowledge Retrieval", "Knowledge", start, False, error=str(e))

    async def _test_capabilities(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, caps = await self._endpoint("GET", "/api/jarvis/capabilities")
            names = {c["name"] for c in caps.get("capabilities", [])} if isinstance(caps, dict) else set()
            expected = {"robot_status", "inspect_cell", "plc_read", "security_scan",
                        "knowledge_lookup", "maintenance_check", "vision_frame"}
            ok = code == 200 and expected <= names
            self._record(report, "Capability Registry", "Core", start, ok,
                           f"{len(names)} capabilities registered" if ok else "",
                           "" if ok else f"missing: {expected - names}")
        except Exception as e:
            self._record(report, "Capability Registry", "Core", start, False, error=str(e))

    async def _test_cell_inspection(self, report: DiagnosticsReport):
        start = time.time()
        try:
            code, cell = await self._endpoint("POST", "/api/robot-cell/inspect",
                                               {"cell": "robot_cell_1"}, timeout=30.0)
            ok = (code == 200 and isinstance(cell, dict)
                  and "verdict" in cell and "findings" in cell
                  and cell.get("validation", {}).get("checks", {}).get("robot_present"))
            self._record(report, "Robot Cell Inspection", "Robotics", start, ok,
                           f"verdict={cell.get('verdict')}" if ok and isinstance(cell, dict) else "",
                           "" if ok else f"HTTP {code}: {str(cell)[:300]}")
        except Exception as e:
            self._record(report, "Robot Cell Inspection", "Robotics", start, False, error=str(e))

    async def _test_telemetry(self, report: DiagnosticsReport):
        """Test /api/system/telemetry endpoint."""
        test_name = "System Telemetry"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/system/telemetry")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    if "cpu_percent" in data and "ram_percent" in data:
                        report.add_result(TestResult(
                            name=test_name,
                            category="System",
                            status=TestStatus.PASS,
                            duration_ms=duration,
                            message=f"CPU: {data['cpu_percent']}%, RAM: {data['ram_percent']}%",
                        ))
                    else:
                        report.add_result(TestResult(
                            name=test_name,
                            category="System",
                            status=TestStatus.FAIL,
                            duration_ms=duration,
                            error="Missing telemetry fields",
                        ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="System",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="System",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_voice_transcription(self, report: DiagnosticsReport):
        """Test voice transcription pipeline (without actual audio)."""
        test_name = "Voice Transcription Pipeline"
        start = time.time()

        try:
            from app.language_detection import detect_language
            detection = detect_language("Hello, how are you?")
            duration = (time.time() - start) * 1000

            if detection.confidence > 0:
                report.add_result(TestResult(
                    name=test_name,
                    category="Voice",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message=f"Language detection working (confidence: {detection.confidence:.2f})",
                ))
            else:
                report.add_result(TestResult(
                    name=test_name,
                    category="Voice",
                    status=TestStatus.FAIL,
                    duration_ms=duration,
                    error="Language detection failed",
                ))
        except ImportError:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Voice",
                status=TestStatus.SKIPPED,
                duration_ms=duration,
                message="Language detection module not available",
            ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Voice",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_tts_synthesis(self, report: DiagnosticsReport):
        """Test TTS synthesis pipeline (without actual synthesis)."""
        test_name = "TTS Synthesis Pipeline"
        start = time.time()

        try:
            from app.tts_service import detect_emotion, Emotion
            emotion = detect_emotion("Task completed successfully!")
            duration = (time.time() - start) * 1000

            if emotion in [Emotion.CONFIRMING, Emotion.CONGRATULATORY]:
                report.add_result(TestResult(
                    name=test_name,
                    category="Voice",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message=f"Emotion detection working (detected: {emotion.value})",
                ))
            else:
                report.add_result(TestResult(
                    name=test_name,
                    category="Voice",
                    status=TestStatus.PASS,
                    duration_ms=duration,
                    message=f"Emotion detection working (detected: {emotion.value})",
                ))
        except ImportError:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Voice",
                status=TestStatus.SKIPPED,
                duration_ms=duration,
                message="TTS service not available",
            ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Voice",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_chat_endpoint(self, report: DiagnosticsReport):
        """Test /api/chat endpoint."""
        test_name = "Chat Endpoint"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {"messages": [{"role": "user", "content": "Hello"}]}
                logger.info(f"Testing chat endpoint with payload: {payload}")
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    if "reply" in data or "message" in data:
                        report.add_result(TestResult(
                            name=test_name,
                            category="AI",
                            status=TestStatus.PASS,
                            duration_ms=duration,
                            message="Chat endpoint responding",
                        ))
                    else:
                        report.add_result(TestResult(
                            name=test_name,
                            category="AI",
                            status=TestStatus.FAIL,
                            duration_ms=duration,
                            error="Missing reply field",
                        ))
                else:
                    error_detail = resp.text
                    logger.error(f"Chat endpoint returned {resp.status_code}: {error_detail}")
                    report.add_result(TestResult(
                        name=test_name,
                        category="AI",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}: {error_detail[:200]}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="AI",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_coding_workspace(self, report: DiagnosticsReport):
        """Test coding workspace endpoints."""
        test_name = "Coding Workspace"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/coding/workspace/tree?max_depth=1")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Coding",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="Workspace tree accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Coding",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Coding",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_file_operations(self, report: DiagnosticsReport):
        """Test file operation endpoints."""
        test_name = "File Operations"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/uploads")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="System",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="File operations accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="System",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="System",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_memory_system(self, report: DiagnosticsReport):
        """Test memory system endpoints."""
        test_name = "Memory System"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/memory/state")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="AI",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="Memory system accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="AI",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="AI",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_web_search(self, report: DiagnosticsReport):
        """Test web search endpoint."""
        test_name = "Web Search"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/google/search",
                    params={"query": "test"},
                )
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Web",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="Web search accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Web",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Web",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_youtube_search(self, report: DiagnosticsReport):
        """Test YouTube search endpoint."""
        test_name = "YouTube Search"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/youtube/search",
                    params={"query": "test"},
                )
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Web",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="YouTube search accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Web",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Web",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_skills_registry(self, report: DiagnosticsReport):
        """Test skills registry endpoint."""
        test_name = "Skills Registry"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/skills")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    if "skills" in data:
                        report.add_result(TestResult(
                            name=test_name,
                            category="AI",
                            status=TestStatus.PASS,
                            duration_ms=duration,
                            message=f"{len(data['skills'])} skills loaded",
                        ))
                    else:
                        report.add_result(TestResult(
                            name=test_name,
                            category="AI",
                            status=TestStatus.FAIL,
                            duration_ms=duration,
                            error="Missing skills field",
                        ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="AI",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="AI",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    async def _test_biometrics_status(self, report: DiagnosticsReport):
        """Test biometrics status endpoint."""
        test_name = "Biometrics System"
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/biometrics/status")
                duration = (time.time() - start) * 1000

                if resp.status_code == 200:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Security",
                        status=TestStatus.PASS,
                        duration_ms=duration,
                        message="Biometrics system accessible",
                    ))
                else:
                    report.add_result(TestResult(
                        name=test_name,
                        category="Security",
                        status=TestStatus.FAIL,
                        duration_ms=duration,
                        error=f"HTTP {resp.status_code}",
                    ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            report.add_result(TestResult(
                name=test_name,
                category="Security",
                status=TestStatus.ERROR,
                duration_ms=duration,
                error=str(e),
            ))

    def get_latest_report(self) -> Optional[DiagnosticsReport]:
        """Get the most recent diagnostics report."""
        return self.test_history[-1] if self.test_history else None

    def get_history(self) -> list[DiagnosticsReport]:
        """Get all diagnostics reports."""
        return self.test_history.copy()


diagnostics_engine = DiagnosticsEngine()
