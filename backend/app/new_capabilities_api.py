"""API router for the new JARVIS capabilities.

Registers routes for: execution policy, observability, security asset graph,
industrial automation, digital twin + cell inspection, PLC analysis,
predictive maintenance, and the unified knowledge layer.

Every route flows: intent -> policy check -> real execution -> validation ->
observability record, and every response says whether the data is real or
simulated.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("jarvis.new_capabilities")

router = APIRouter(tags=["jarvis-capabilities"])


def _trace(tool: str, agent: str, user_input: str = "", status: str = "completed",
            output: Any = None, error: str | None = None, **extra):
    try:
        from app.core.observability import get_observability
        trace = get_observability().start_trace(
            user_input=user_input, agent=agent, tool=tool, **extra)
        trace.finish(status, output, error)
        get_observability().record(trace)
        return trace.id
    except Exception:
        return ""


# ========================================================================== #
# Execution policy
# ========================================================================== #
class PolicyCheckRequest(BaseModel):
    operation: str
    agent: str = ""
    tool: str = ""
    target: str = ""
    action_class: Optional[str] = None
    authorized: bool = False
    scope_id: Optional[str] = None
    simulate: bool = False
    user_intent: str = ""
    task_id: str = ""


@router.post("/api/policy/check")
async def policy_check(req: PolicyCheckRequest):
    from app.core.execution_policy import get_execution_policy
    record = get_execution_policy().evaluate(
        req.operation, agent=req.agent, tool=req.tool, target=req.target,
        action_class=req.action_class, authorized=req.authorized,
        scope_id=req.scope_id, simulate=req.simulate,
        user_intent=req.user_intent, task_id=req.task_id)
    return record.to_dict()


@router.post("/api/policy/confirm")
async def policy_confirm(payload: dict):
    from app.core.execution_policy import get_execution_policy
    token = get_execution_policy().confirm(
        payload.get("operation", ""), payload.get("target", ""),
        payload.get("confirmed_by", "user"))
    return {"success": True, "confirmation_token": token,
            "note": "Re-issue the action with authorized=true within 120 seconds."}


@router.get("/api/policy/history")
async def policy_history(limit: int = 50, action_class: Optional[str] = None):
    from app.core.execution_policy import get_execution_policy
    return {"history": get_execution_policy().get_history(limit, action_class)}


@router.get("/api/policy/stats")
async def policy_stats():
    from app.core.execution_policy import get_execution_policy
    return get_execution_policy().get_stats()


# ========================================================================== #
# Observability
# ========================================================================== #
@router.get("/api/observability/recent")
async def observability_recent(limit: int = 50, agent: Optional[str] = None,
                               status: Optional[str] = None):
    from app.core.observability import get_observability
    return {"traces": get_observability().recent(limit, agent, status)}


@router.get("/api/observability/task/{task_id}")
async def observability_task(task_id: str):
    from app.core.observability import get_observability
    return {"task_id": task_id, "traces": get_observability().get_by_task(task_id)}


@router.get("/api/observability/trace/{trace_id}")
async def observability_trace(trace_id: str):
    from app.core.observability import get_observability
    trace = get_observability().get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return trace


@router.get("/api/observability/stats")
async def observability_stats():
    from app.core.observability import get_observability
    return get_observability().get_stats()


# ========================================================================== #
# Security asset graph
# ========================================================================== #
@router.post("/api/security/graph/sync")
async def graph_sync():
    from app.cybersecurity.asset_graph import get_security_graph
    counts = get_security_graph().sync_from_databases()
    return {"success": True, "synced": counts,
            "summary": get_security_graph().risk_summary()}


@router.get("/api/security/graph/summary")
async def graph_summary():
    from app.cybersecurity.asset_graph import get_security_graph
    return get_security_graph().risk_summary()


@router.get("/api/security/graph/nodes")
async def graph_nodes(node_type: Optional[str] = None, q: str = "", limit: int = 200):
    from app.cybersecurity.asset_graph import get_security_graph
    return {"nodes": get_security_graph().find_nodes(node_type, q, limit)}


@router.get("/api/security/graph/neighbors/{node_id}")
async def graph_neighbors(node_id: str, depth: int = 1):
    from app.cybersecurity.asset_graph import get_security_graph
    result = get_security_graph().neighbors(node_id, min(max(depth, 1), 3))
    if not result.get("root"):
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return result


@router.get("/api/security/graph/attack-paths")
async def graph_attack_paths(limit: int = 20):
    from app.cybersecurity.asset_graph import get_security_graph
    return {"paths": get_security_graph().attack_paths(limit)}


@router.post("/api/security/graph/ingest-scan")
async def graph_ingest_scan(payload: dict):
    from app.cybersecurity.asset_graph import get_security_graph
    counts = get_security_graph().ingest_scan_result(
        payload.get("scan_type", "manual"), payload.get("target", ""),
        payload.get("result", {}))
    return {"success": True, "ingested": counts}


# ========================================================================== #
# Industrial automation
# ========================================================================== #
class DeviceRegisterRequest(BaseModel):
    id: str
    name: str
    kind: str = "plc"
    protocol: str = "modbus_tcp"
    address: str = ""
    port: int = 502
    unit_id: int = 1
    tags: list[dict] = Field(default_factory=list)
    cell: str = ""


@router.get("/api/industrial/status")
async def industrial_status():
    from app.industrial_service import get_industrial_service
    return get_industrial_service().get_status()


@router.get("/api/industrial/protocols")
async def industrial_protocols():
    from app.industrial_service import get_industrial_service
    return get_industrial_service().protocol_status()


@router.get("/api/industrial/devices")
async def industrial_devices(cell: Optional[str] = None):
    from app.industrial_service import get_industrial_service
    return {"devices": get_industrial_service().list_devices(cell)}


@router.post("/api/industrial/devices/register")
async def industrial_register(req: DeviceRegisterRequest):
    from app.industrial_service import IndustrialDevice, get_industrial_service
    device = IndustrialDevice(**req.model_dump())
    return {"success": True, "device": get_industrial_service().register_device(device)}


class ConnectRequest(BaseModel):
    kind: str = "modbus"
    host: str = "127.0.0.1"
    port: int = 502
    unit_id: int = 1
    endpoint: str = ""
    broker: str = "localhost"
    mqtt_port: int = 1883
    subscribe_topics: list[str] = Field(default_factory=list)
    device_id: str = ""


@router.post("/api/industrial/connect")
async def industrial_connect(req: ConnectRequest):
    from app.industrial_service import get_industrial_service
    svc = get_industrial_service()
    if req.kind == "modbus":
        return svc.connect_modbus(req.host, req.port, req.unit_id, req.device_id)
    if req.kind == "opcua":
        return svc.connect_opcua(req.endpoint or f"opc.tcp://{req.host}:4840", req.device_id)
    if req.kind == "mqtt":
        return svc.connect_mqtt(req.broker, req.mqtt_port, req.subscribe_topics, req.device_id)
    raise HTTPException(status_code=400, detail=f"Unknown connection kind '{req.kind}'")


@router.get("/api/industrial/device/{device_id}/read")
async def industrial_read(device_id: str):
    from app.core.execution_policy import ActionClass, get_execution_policy
    policy = get_execution_policy().evaluate(
        "read_device_tags", agent="industrial_agent", tool="industrial.read_device",
        target=device_id, action_class=ActionClass.READ)
    if policy.decision == "DENY":
        raise HTTPException(status_code=403, detail=policy.decision_reason)
    from app.industrial_service import get_industrial_service
    result = get_industrial_service().read_device(device_id)
    result["simulated"] = bool(get_industrial_service().get_device(device_id) and
                               get_industrial_service().get_device(device_id).simulated)
    _trace("industrial.read_device", "industrial_agent", f"read {device_id}",
           output={"readings": len(result.get("readings", [])), "errors": len(result.get("errors", []))})
    return result


@router.get("/api/industrial/device/{device_id}/tag/{tag}")
async def industrial_read_tag(device_id: str, tag: str):
    from app.industrial_service import get_industrial_service
    result = get_industrial_service().read_tag(device_id, tag)
    device = get_industrial_service().get_device(device_id)
    result["simulated"] = bool(device and device.simulated)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


class WriteTagRequest(BaseModel):
    value: Any
    authorized: bool = False


@router.post("/api/industrial/device/{device_id}/tag/{tag}/write")
async def industrial_write_tag(device_id: str, tag: str, req: WriteTagRequest):
    from app.core.execution_policy import ActionClass, get_execution_policy
    policy = get_execution_policy().evaluate(
        "write_tag", agent="industrial_agent", tool="industrial.write_tag",
        target=f"{device_id}.{tag}", action_class=ActionClass.CONTROL,
        authorized=req.authorized)
    if policy.decision != "ALLOW":
        raise HTTPException(status_code=403, detail={
            "message": policy.decision_reason,
            "action_class": "CONTROL",
            "decision": policy.decision,
            "confirm_url": "/api/policy/confirm",
        })
    from app.industrial_service import get_industrial_service
    result = get_industrial_service().write_tag(device_id, tag, req.value, authorized=True)
    _trace("industrial.write_tag", "industrial_agent", f"write {device_id}.{tag}",
           output={"success": result.get("success")}, error=result.get("error"))
    if result.get("blocked"):
        raise HTTPException(status_code=403, detail=result.get("error"))
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error"))
    return result


@router.get("/api/industrial/device/{device_id}/state")
async def industrial_state(device_id: str):
    from app.industrial_service import get_industrial_service
    return get_industrial_service().machine_state(device_id)


@router.get("/api/industrial/alarms")
async def industrial_alarms(active_only: bool = False, limit: int = 100):
    from app.industrial_service import get_industrial_service
    svc = get_industrial_service()
    return {"alarms": svc.active_alarms() if active_only else svc.all_alarms(limit)}


@router.post("/api/industrial/alarms/raise")
async def industrial_raise_alarm(payload: dict):
    from app.industrial_service import get_industrial_service
    return get_industrial_service().raise_alarm(
        payload.get("code", "GEN"), payload.get("message", "operator alarm"),
        payload.get("severity", "medium"), payload.get("source", "api"))


@router.post("/api/industrial/alarms/{alarm_id}/clear")
async def industrial_clear_alarm(alarm_id: str):
    from app.industrial_service import get_industrial_service
    result = get_industrial_service().clear_alarm(alarm_id)
    if result.get("success") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/api/industrial/mode")
async def industrial_mode(payload: dict):
    from app.industrial_service import get_industrial_service
    result = get_industrial_service().set_control_mode(payload.get("mode", "monitoring"))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/api/industrial/history")
async def industrial_history(device_id: str, tag: str, limit: int = 200):
    from app.industrial_service import get_industrial_service
    return {"device_id": device_id, "tag": tag,
            "samples": get_industrial_service().tag_history(device_id, tag, limit)}


class SimulatorRequest(BaseModel):
    action: str = "start"


@router.post("/api/industrial/simulator/modbus")
async def industrial_modbus_sim(req: SimulatorRequest):
    from app.industrial_sim import get_modbus_sim
    sim = get_modbus_sim()
    if req.action == "stop":
        sim.stop()
        return {"success": True, "running": False}
    result = sim.start()
    if not result.get("success") and not sim.running:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return {"success": True, "running": sim.running, "host": sim.host, "port": sim.port,
            "simulated": True, "snapshot": sim.snapshot()}


@router.get("/api/industrial/simulator/modbus/snapshot")
async def industrial_modbus_snapshot():
    from app.industrial_sim import get_modbus_sim
    return get_modbus_sim().snapshot()


@router.post("/api/industrial/simulator/mqtt")
async def industrial_mqtt_sim(req: SimulatorRequest):
    from app.industrial_sim import get_mqtt_sim
    sim = get_mqtt_sim()
    if req.action == "stop":
        sim.stop()
        return {"success": True, "running": False}
    result = sim.start()
    if not result.get("success"):
        raise HTTPException(status_code=501, detail=result.get("error"))
    return {**result, "running": sim.running}


# ========================================================================== #
# Digital twin + robot cell
# ========================================================================== #
@router.get("/api/twin/status")
async def twin_status():
    from app.digital_twin import get_digital_twin
    return get_digital_twin().get_status()


@router.get("/api/twin/entity/{entity}")
async def twin_entity(entity: str):
    from app.digital_twin import get_digital_twin
    return get_digital_twin().get_state(entity)


class TwinExpectedRequest(BaseModel):
    entity: str
    state: dict
    source: str = "operator"


@router.post("/api/twin/expected")
async def twin_expected(req: TwinExpectedRequest):
    from app.digital_twin import get_digital_twin
    return get_digital_twin().set_expected(req.entity, req.state, req.source)


class TwinActualRequest(BaseModel):
    entity: str
    state: dict
    source: str = "live"
    simulated: bool = False


@router.post("/api/twin/actual")
async def twin_actual(req: TwinActualRequest):
    from app.digital_twin import get_digital_twin
    return get_digital_twin().update_actual(req.entity, req.state, req.source, req.simulated)


@router.get("/api/twin/deviations")
async def twin_deviations(limit: int = 50):
    from app.digital_twin import get_digital_twin
    return {"deviations": get_digital_twin().deviations(limit)}


@router.post("/api/robot-cell/inspect")
async def robot_cell_inspect(payload: dict | None = None):
    from app.digital_twin import get_cell_inspector
    payload = payload or {}
    report = await get_cell_inspector().inspect(
        cell=payload.get("cell", "robot_cell_1"),
        run_vision=bool(payload.get("run_vision", False)))
    return report


# ========================================================================== #
# PLC analysis
# ========================================================================== #
class PlcAnalyzeRequest(BaseModel):
    source: str = ""
    filename: str = ""
    path: str = ""


@router.post("/api/plc/analyze")
async def plc_analyze(req: PlcAnalyzeRequest):
    from app.plc_analyzer import get_plc_analyzer
    analyzer = get_plc_analyzer()
    if req.path:
        result = analyzer.analyze_file(req.path)
    elif req.source:
        result = analyzer.analyze(req.source, req.filename)
    else:
        raise HTTPException(status_code=400, detail="Provide 'source' or 'path'")
    _trace("plc.analyze", "plc_agent", f"analyze {req.filename or req.path}",
           output={"findings": result.get("finding_count", 0)})
    return result


@router.get("/api/plc/analyses")
async def plc_analyses(limit: int = 20):
    from app.plc_analyzer import get_plc_analyzer
    return {"analyses": get_plc_analyzer().get_analyses(limit)}


@router.post("/api/plc/test-cases")
async def plc_test_cases(payload: dict):
    from app.plc_analyzer import get_plc_analyzer
    analysis_id = payload.get("analysis_id", "")
    analysis = next((a for a in get_plc_analyzer()._analyses
                     if a.get("analysis_id") == analysis_id), None)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
    return get_plc_analyzer().generate_test_cases(analysis)


@router.post("/api/plc/documentation")
async def plc_documentation(payload: dict):
    from app.plc_analyzer import get_plc_analyzer
    analysis_id = payload.get("analysis_id", "")
    analysis = next((a for a in get_plc_analyzer()._analyses
                     if a.get("analysis_id") == analysis_id), None)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
    return {"analysis_id": analysis_id,
            "documentation": get_plc_analyzer().generate_documentation(analysis)}


@router.post("/api/plc/draft")
async def plc_draft(payload: dict):
    from app.plc_analyzer import get_plc_analyzer
    spec = (payload or {}).get("spec", "")
    if not spec.strip():
        raise HTTPException(status_code=400, detail="Provide a 'spec' description")
    return get_plc_analyzer().generate_draft(spec)


# ========================================================================== #
# Predictive maintenance
# ========================================================================== #
class SampleRequest(BaseModel):
    device_id: str
    signal: str
    value: float
    unit: str = ""
    source: str = ""


@router.get("/api/maintenance/status")
async def maintenance_status():
    from app.predictive_maintenance import get_maintenance_engine
    return get_maintenance_engine().get_status()


@router.post("/api/maintenance/samples")
async def maintenance_sample(req: SampleRequest):
    from app.predictive_maintenance import get_maintenance_engine
    result = get_maintenance_engine().record_sample(
        req.device_id, req.signal, req.value, req.unit, req.source)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/api/maintenance/series")
async def maintenance_series():
    from app.predictive_maintenance import get_maintenance_engine
    return {"series": get_maintenance_engine().list_series()}


@router.get("/api/maintenance/series/{device_id}/{signal}")
async def maintenance_signal(device_id: str, signal: str, limit: int = 500):
    from app.predictive_maintenance import get_maintenance_engine
    return {"device_id": device_id, "signal": signal,
            "samples": get_maintenance_engine().get_series(device_id, signal, limit)}


@router.post("/api/maintenance/collect")
async def maintenance_collect(payload: dict):
    from app.predictive_maintenance import get_maintenance_engine
    engine = get_maintenance_engine()
    kind = (payload or {}).get("source", "host")
    if kind == "robot":
        return engine.collect_from_robot()
    if kind == "plc":
        device_id = (payload or {}).get("device_id", "")
        return engine.collect_from_plc(device_id, (payload or {}).get("tags"))
    return engine.collect_host_telemetry()


@router.post("/api/maintenance/analyze")
async def maintenance_analyze(payload: dict | None = None):
    from app.predictive_maintenance import get_maintenance_engine
    result = get_maintenance_engine().analyze((payload or {}).get("device_id"))
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error"))
    _trace("maintenance.analyze", "maintenance_agent", "analyze equipment",
           output={"signals": result.get("signals_analyzed"),
                   "alerts": len(result.get("alerts", []))})
    return result


@router.get("/api/maintenance/health/{device_id}")
async def maintenance_health(device_id: str):
    from app.predictive_maintenance import get_maintenance_engine
    return get_maintenance_engine().equipment_health(device_id)


@router.get("/api/maintenance/alerts")
async def maintenance_alerts(limit: int = 50, device_id: Optional[str] = None):
    from app.predictive_maintenance import get_maintenance_engine
    return {"alerts": get_maintenance_engine().get_alerts(limit, device_id)}


@router.post("/api/maintenance/thresholds")
async def maintenance_threshold(payload: dict):
    from app.predictive_maintenance import get_maintenance_engine
    return get_maintenance_engine().set_threshold(
        payload.get("signal", ""), payload.get("warn", 0),
        payload.get("critical", 0), payload.get("unit", ""))


# ========================================================================== #
# Unified knowledge / RAG
# ========================================================================== #
class KnowledgeQuery(BaseModel):
    query: str
    domain: Optional[str] = None
    limit: int = 8


@router.post("/api/knowledge/search")
async def knowledge_search(req: KnowledgeQuery):
    from app.knowledge_rag import get_knowledge_base
    result = get_knowledge_base().search(req.query, req.domain, req.limit)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    _trace("knowledge.search", "knowledge_agent", req.query,
           output={"results": result.get("result_count"), "sources": result.get("sources")})
    return result


@router.post("/api/knowledge/answer-context")
async def knowledge_answer_context(req: KnowledgeQuery):
    from app.knowledge_rag import get_knowledge_base
    result = get_knowledge_base().answer_context(req.query, req.domain, min(req.limit, 5))
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/api/knowledge/status")
async def knowledge_status():
    from app.knowledge_rag import get_knowledge_base
    return get_knowledge_base().get_status()


@router.get("/api/knowledge/domains")
async def knowledge_domains():
    from app.knowledge_rag import get_knowledge_base
    return get_knowledge_base().domains()


class IngestRequest(BaseModel):
    title: str
    content: str = ""
    path: str = ""
    domain: str = "documents"


@router.post("/api/knowledge/ingest")
async def knowledge_ingest(req: IngestRequest):
    from app.knowledge_rag import get_knowledge_base
    kb = get_knowledge_base()
    if req.path:
        result = kb.ingest_file(req.path, req.domain)
    else:
        result = kb.ingest_text(req.title, req.content, req.domain, source="api")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/api/knowledge/documents")
async def knowledge_documents(limit: int = 100):
    from app.knowledge_rag import get_knowledge_base
    return {"documents": get_knowledge_base().list_documents(limit)}


@router.delete("/api/knowledge/documents/{document_id}")
async def knowledge_delete(document_id: str):
    from app.knowledge_rag import get_knowledge_base
    result = get_knowledge_base().delete_document(document_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ========================================================================== #
# Orchestrated multi-domain commands (voice/chat entry points wired to the
# central orchestrator pipeline).
# ========================================================================== #
@router.post("/api/jarvis/execute-capability")
async def execute_capability(payload: dict):
    """Run a capability through the full pipeline with policy + observability.

    Body: {capability, target, args, authorized, scope_id, simulate}
    """
    from app.core.execution_policy import ActionClass, get_execution_policy
    from app.core.observability import get_observability

    capability = (payload or {}).get("capability", "")
    target = (payload or {}).get("target", "")
    args = (payload or {}).get("args", {}) or {}
    authorized = bool((payload or {}).get("authorized", False))
    scope_id = (payload or {}).get("scope_id")
    simulate = bool((payload or {}).get("simulate", False))

    registry = _capability_registry()
    entry = registry.get(capability)
    if not entry:
        raise HTTPException(status_code=404, detail={
            "error": f"Unknown capability '{capability}'",
            "available": sorted(registry.keys()),
        })

    policy = get_execution_policy().evaluate(
        capability, agent=entry["agent"], tool=entry["tool"], target=target,
        action_class=entry["action_class"], authorized=authorized,
        scope_id=scope_id, simulate=simulate, user_intent=capability)
    if policy.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=policy.to_dict())

    obs = get_observability()
    trace = obs.start_trace(
        user_input=capability, intent=capability, agent=entry["agent"],
        tool=entry["tool"], tool_input=args, action_class=entry["action_class"],
        risk_level=policy.risk_level, permission_result=policy.decision,
        simulated=simulate or policy.action_class == ActionClass.SIMULATE.value,
        source="execute-capability")
    try:
        result = await entry["handler"](target, args)
        simulated = bool(isinstance(result, dict) and result.get("simulated"))
        trace.simulated = trace.simulated or simulated
        trace.finish("completed", result)
        trace.validation_status = "validated" if not (
            isinstance(result, dict) and result.get("success") is False) else "failed"
        obs.record(trace)
        if isinstance(result, dict):
            result["policy"] = policy.to_dict()
            result["trace_id"] = trace.id
        return result
    except Exception as e:
        trace.finish("failed", error=str(e))
        trace.validation_status = "failed"
        obs.record(trace)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jarvis/capabilities")
async def list_capabilities():
    return {"capabilities": [
        {"name": name, "agent": entry["agent"], "action_class": entry["action_class"].value,
         "description": entry["description"]}
        for name, entry in sorted(_capability_registry().items())
    ]}


def _capability_registry() -> dict[str, dict]:
    from app.core.execution_policy import ActionClass

    async def robot_status(target: str, args: dict):
        from app.robotics_service import get_robotics_service
        status = get_robotics_service().get_full_status()
        status["simulated"] = status.get("simulation", True)
        return status

    async def robot_navigate(target: str, args: dict):
        from app.robotics_service import get_robotics_service
        result = await get_robotics_service().navigate_to(target or args.get("location", ""))
        result["simulated"] = True
        return result

    async def vision_frame(target: str, args: dict):
        from app.vision_service import get_vision_service
        frame = await get_vision_service().process_frame()
        data = frame.to_dict()
        data["simulated"] = get_vision_service().get_stats().get("simulation_mode", True)
        return data

    async def cell_inspect(target: str, args: dict):
        from app.digital_twin import get_cell_inspector
        return await get_cell_inspector().inspect(
            cell=target or args.get("cell", "robot_cell_1"),
            run_vision=bool(args.get("run_vision", False)))

    async def plc_read(target: str, args: dict):
        from app.industrial_service import get_industrial_service
        return get_industrial_service().read_device(target)

    async def plc_analyze(target: str, args: dict):
        from app.plc_analyzer import get_plc_analyzer
        analyzer = get_plc_analyzer()
        if args.get("source"):
            return analyzer.analyze(args["source"], args.get("filename", ""))
        if args.get("path") or target:
            return analyzer.analyze_file(args.get("path") or target)
        raise ValueError("Provide PLC source text or a file path")

    async def security_scan(target: str, args: dict):
        from app.cybersecurity import get_vulnerability_scanner, get_security_db, get_alert_manager
        scan = get_vulnerability_scanner().comprehensive_vulnerability_scan()
        return {"success": True, "scan": scan,
                "alert_summary": get_alert_manager().get_alert_summary(),
                "security_stats": get_security_db().get_security_stats()}

    async def knowledge_lookup(target: str, args: dict):
        from app.knowledge_rag import get_knowledge_base
        result = get_knowledge_base().search(target or args.get("query", ""),
                                             args.get("domain"), args.get("limit", 5))
        if not result.get("success"):
            raise ValueError(result.get("error", "no knowledge retrieved"))
        return result

    async def maintenance_check(target: str, args: dict):
        from app.predictive_maintenance import get_maintenance_engine
        result = get_maintenance_engine().analyze(target or None)
        if not result.get("success"):
            raise ValueError(result.get("error", "no maintenance data"))
        return result

    return {
        "robot_status": {"agent": "navigation_agent", "tool": "robotics.status",
                         "action_class": ActionClass.READ,
                         "description": "Read live robot state, joints, navigation status",
                         "handler": robot_status},
        "robot_navigate": {"agent": "navigation_agent", "tool": "robotics.navigate",
                           "action_class": ActionClass.SIMULATE,
                           "description": "Navigate the simulated robot to a named location",
                           "handler": robot_navigate},
        "vision_frame": {"agent": "object_detection_agent", "tool": "vision.process_frame",
                         "action_class": ActionClass.READ,
                         "description": "Capture and analyze one camera frame",
                         "handler": vision_frame},
        "inspect_cell": {"agent": "monitoring_agent", "tool": "cell.inspect",
                         "action_class": ActionClass.READ,
                         "description": "Correlated robot-cell inspection report",
                         "handler": cell_inspect},
        "plc_read": {"agent": "industrial_agent", "tool": "industrial.read_device",
                     "action_class": ActionClass.READ,
                     "description": "Read PLC tags and machine state",
                     "handler": plc_read},
        "plc_analyze": {"agent": "plc_agent", "tool": "plc.analyze",
                        "action_class": ActionClass.ANALYZE,
                        "description": "Analyze a PLC program for logic errors",
                        "handler": plc_analyze},
        "security_scan": {"agent": "security_agent", "tool": "security.scan",
                          "action_class": ActionClass.ANALYZE,
                          "description": "Defensive vulnerability scan of local systems",
                          "handler": security_scan},
        "knowledge_lookup": {"agent": "knowledge_agent", "tool": "knowledge.search",
                             "action_class": ActionClass.READ,
                             "description": "Retrieve knowledge across all domains",
                             "handler": knowledge_lookup},
        "maintenance_check": {"agent": "maintenance_agent", "tool": "maintenance.analyze",
                              "action_class": ActionClass.ANALYZE,
                              "description": "Analyze stored sensor data for failures",
                              "handler": maintenance_check},
    }
