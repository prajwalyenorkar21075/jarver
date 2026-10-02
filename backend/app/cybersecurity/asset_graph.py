"""Security Asset Graph for JARVIS.

Models the relationships the security modules already produce so the AI can
reason over them instead of looking at flat lists:

    Device → IP → Port → Service → Software → Vulnerability
          → Account → Permission → Security Event → Incident

Storage: dedicated tables in ``security.db`` (same file the cybersecurity
module already uses). ``migrate()`` is additive only — it never drops or
rewrites an existing table, so existing scan data is preserved.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.security_graph")

SECURITY_DB_PATH = Path(__file__).resolve().parent.parent.parent / "security.db"

NODE_TYPES = (
    "device", "ip", "port", "service", "software", "vulnerability",
    "account", "permission", "event", "incident",
)

RELATION_TYPES = (
    "has_ip", "exposes_port", "runs_service", "has_software",
    "affected_by", "has_account", "grants_permission",
    "generated_event", "part_of_incident", "connects_to", "depends_on",
)


class SecurityAssetGraph:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or SECURITY_DB_PATH
        self.migrate()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def _read_conn(self):
        """Separate, read-only connection for reading source tables.

        The graph writes on another connection while these rows are still being
        iterated; a plain read connection would hold a SHARED lock and block the
        write, so source reads are opened with ``mode=ro``.
        """
        uri = f"file:{str(self.db_path).replace(chr(92), '/')}?mode=ro"
        conn = sqlite3.connect(uri, timeout=10.0, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def migrate(self):
        """Additive migration — safe to run on every start, never destructive."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asset_graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    risk_score REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asset_graph_edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    properties TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_node_unique ON asset_graph_nodes(node_type, name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_edge_source ON asset_graph_edges(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_edge_target ON asset_graph_edges(target_id)")
            conn.commit()
        logger.info("[SECURITY_GRAPH] asset graph tables ready")

    # ------------------------------------------------------------------ #
    # Nodes / edges
    # ------------------------------------------------------------------ #
    def upsert_node(self, node_type: str, name: str, properties: dict | None = None,
                    risk_score: float = 0.0) -> str:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Unknown node type '{node_type}'. Valid: {NODE_TYPES}")
        now = time.time()
        props = json.dumps(properties or {})
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM asset_graph_nodes WHERE node_type=? AND name=?",
                (node_type, name),
            ).fetchone()
            if row:
                node_id = row["id"]
                conn.execute(
                    "UPDATE asset_graph_nodes SET properties=?, last_seen=?, risk_score=? WHERE id=?",
                    (props, now, risk_score, node_id),
                )
            else:
                node_id = str(uuid.uuid4())[:12]
                conn.execute(
                    """INSERT INTO asset_graph_nodes
                       (id, node_type, name, properties, first_seen, last_seen, risk_score)
                       VALUES (?,?,?,?,?,?,?)""",
                    (node_id, node_type, name, props, now, now, risk_score),
                )
        return node_id

    def add_edge(self, source_id: str, relation: str, target_id: str,
                 properties: dict | None = None) -> str:
        if relation not in RELATION_TYPES:
            raise ValueError(f"Unknown relation '{relation}'. Valid: {RELATION_TYPES}")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM asset_graph_edges WHERE source_id=? AND relation=? AND target_id=?",
                (source_id, relation, target_id),
            ).fetchone()
            if row:
                return row["id"]
            edge_id = str(uuid.uuid4())[:12]
            conn.execute(
                """INSERT INTO asset_graph_edges (id, source_id, relation, target_id, properties, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (edge_id, source_id, relation, target_id, json.dumps(properties or {}), time.time()),
            )
        return edge_id

    def link(self, source: tuple[str, str], relation: str, target: tuple[str, str],
             properties: dict | None = None) -> tuple[str, str, str]:
        """Link two (type, name) pairs, creating nodes as needed."""
        src_id = self.upsert_node(source[0], source[1])
        dst_id = self.upsert_node(target[0], target[1])
        self.add_edge(src_id, relation, dst_id, properties)
        return src_id, relation, dst_id

    # ------------------------------------------------------------------ #
    # Ingestion from existing security modules
    # ------------------------------------------------------------------ #
    def ingest_scan_result(self, scan_type: str, target: str, result: dict) -> dict[str, int]:
        """Turn a completed scan into graph nodes/edges.

        Handles the shapes the existing cybersecurity module produces:
        port scans (open_ports), vulnerability scans, code scans (findings).
        """
        counts = {"nodes": 0, "edges": 0, "vulnerabilities": 0, "open_ports": 0}

        if not target:
            return counts

        device_id = self.upsert_node("device", target, {"scan_type": scan_type})
        counts["nodes"] += 1

        ip_like = target.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
        ip_id = self.upsert_node("ip", ip_like, {"source_target": target})
        self.add_edge(device_id, "has_ip", ip_id)
        counts["nodes"] += 1
        counts["edges"] += 1

        open_ports = result.get("open_ports") or result.get("ports") or []
        for port_info in open_ports:
            if isinstance(port_info, dict):
                port = port_info.get("port")
                service = port_info.get("service") or "unknown"
                state = port_info.get("state", "open")
            else:
                port, service, state = port_info, "unknown", "open"
            if port is None:
                continue
            port_id = self.upsert_node("port", f"{ip_like}:{port}", {"state": state, "protocol": "tcp"})
            self.add_edge(ip_id, "exposes_port", port_id)
            service_id = self.upsert_node("service", f"{service}@{port}", {"port": port, "name": service})
            self.add_edge(port_id, "runs_service", service_id)
            counts["nodes"] += 2
            counts["edges"] += 2
            counts["open_ports"] += 1

        findings = result.get("findings") or []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            title = finding.get("title") or finding.get("category") or "finding"
            severity = str(finding.get("severity", "info")).lower()
            risk = {"critical": 9.5, "high": 7.5, "medium": 5.0, "low": 2.5, "info": 0.5}.get(severity, 1.0)
            vuln_id = self.upsert_node(
                "vulnerability",
                f"{title} [{finding.get('file_path', ip_like)}:{finding.get('line_number', 0)}]"
                if finding.get("file_path") else title,
                {
                    "severity": severity,
                    "category": finding.get("category", ""),
                    "remediation": finding.get("remediation", ""),
                    "cwe_id": finding.get("cwe_id"),
                    "cve_id": finding.get("cve_id"),
                    "source": scan_type,
                },
                risk_score=risk,
            )
            self.add_edge(device_id, "affected_by", vuln_id)
            counts["nodes"] += 1
            counts["edges"] += 1
            counts["vulnerabilities"] += 1

            software = finding.get("affected_component") or finding.get("file_path")
            if software:
                sw_id = self.upsert_node("software", str(software))
                self.add_edge(sw_id, "affected_by", vuln_id)
                self.add_edge(device_id, "has_software", sw_id)
                counts["nodes"] += 1
                counts["edges"] += 2

        return counts

    def ingest_security_event(self, event: dict) -> str:
        event_id = event.get("id") or str(uuid.uuid4())[:12]
        node_id = self.upsert_node(
            "event",
            f"{event.get('event_type', 'event')}:{event_id}",
            {
                "severity": event.get("severity", "info"),
                "source": event.get("source", ""),
                "description": event.get("description", ""),
                "timestamp": event.get("timestamp", time.time()),
            },
            risk_score={"critical": 9.0, "high": 7.0, "medium": 4.0, "low": 2.0}.get(
                str(event.get("severity", "info")).lower(), 0.5),
        )
        source = event.get("source")
        if source:
            device_id = self.upsert_node("device", str(source))
            self.add_edge(device_id, "generated_event", node_id)
        return node_id

    def ingest_incident(self, incident: dict) -> str:
        inc_id = incident.get("id") or incident.get("incident_id") or str(uuid.uuid4())[:12]
        node_id = self.upsert_node(
            "incident",
            f"{incident.get('title', 'incident')}:{inc_id}",
            {
                "severity": incident.get("severity", "medium"),
                "status": incident.get("status", "detected"),
                "created_at": incident.get("created_at", time.time()),
            },
            risk_score=8.0 if str(incident.get("severity", "")).lower() in ("critical", "high") else 4.0,
        )
        for system in incident.get("affected_systems") or []:
            device_id = self.upsert_node("device", str(system))
            self.add_edge(device_id, "part_of_incident", node_id)
        return node_id

    def ingest_account(self, username: str, role: str = "user",
                       device: str | None = None, permissions: list[str] | None = None) -> str:
        account_id = self.upsert_node("account", username, {"role": role})
        if device:
            device_id = self.upsert_node("device", device)
            self.add_edge(device_id, "has_account", account_id)
        for perm in permissions or []:
            perm_id = self.upsert_node("permission", perm, {"scope": role})
            self.add_edge(account_id, "grants_permission", perm_id)
        return account_id

    def sync_from_databases(self) -> dict[str, int]:
        """Pull the existing security tables into the graph (idempotent)."""
        counts = {"events": 0, "incidents": 0, "vulnerabilities": 0, "scans": 0}
        # Source rows are fetched in full before any graph write: SQLite will not
        # let a second connection commit while a read cursor is still open.
        with self._read_conn() as conn:
            try:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT 500")]
                for row in rows:
                    self.ingest_security_event(row)
                    counts["events"] += 1
            except sqlite3.Error as e:
                logger.debug(f"[SECURITY_GRAPH] security_events skipped: {e}")

            try:
                incident_rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 200")]
                for data in incident_rows:
                    if data.get("affected_systems"):
                        try:
                            data["affected_systems"] = json.loads(data["affected_systems"])
                        except (json.JSONDecodeError, TypeError):
                            data["affected_systems"] = []
                    self.ingest_incident(data)
                    counts["incidents"] += 1
            except sqlite3.Error as e:
                logger.debug(f"[SECURITY_GRAPH] incidents skipped: {e}")

            try:
                vuln_rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM vulnerabilities ORDER BY discovered_at DESC LIMIT 500")]
                for data in vuln_rows:
                    vuln_id = self.upsert_node(
                        "vulnerability",
                        data.get("title") or data.get("cve_id") or "vulnerability",
                        {
                            "severity": data.get("severity"),
                            "cve_id": data.get("cve_id"),
                            "cvss_score": data.get("cvss_score"),
                            "remediation": data.get("remediation"),
                        },
                        risk_score=float(data.get("cvss_score") or 5.0),
                    )
                    system = data.get("affected_system")
                    if system:
                        device_id = self.upsert_node("device", str(system))
                        self.add_edge(device_id, "affected_by", vuln_id)
                    counts["vulnerabilities"] += 1
            except sqlite3.Error as e:
                logger.debug(f"[SECURITY_GRAPH] vulnerabilities skipped: {e}")

            try:
                scan_rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM scan_results ORDER BY timestamp DESC LIMIT 100")]
                for data in scan_rows:
                    raw = data.get("raw_results")
                    findings = []
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            findings = parsed if isinstance(parsed, list) else []
                        except (json.JSONDecodeError, TypeError):
                            findings = []
                    self.ingest_scan_result(
                        data.get("scan_type", "scan"),
                        data.get("target") or "local",
                        {"findings": findings},
                    )
                    counts["scans"] += 1
            except sqlite3.Error as e:
                logger.debug(f"[SECURITY_GRAPH] scan_results skipped: {e}")

        return counts

    # ------------------------------------------------------------------ #
    # Reasoning over the graph
    # ------------------------------------------------------------------ #
    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM asset_graph_nodes WHERE id=?", (node_id,)).fetchone()
            return dict(row) if row else None

    def find_nodes(self, node_type: str | None = None, name_contains: str = "",
                   limit: int = 200) -> list[dict[str, Any]]:
        query = "SELECT * FROM asset_graph_nodes WHERE 1=1"
        params: list[Any] = []
        if node_type:
            query += " AND node_type=?"
            params.append(node_type)
        if name_contains:
            query += " AND name LIKE ?"
            params.append(f"%{name_contains}%")
        query += " ORDER BY risk_score DESC, last_seen DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params)]

    def neighbors(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        """Breadth-first neighbourhood around a node."""
        seen = {node_id}
        frontier = [node_id]
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        for _ in range(max(1, depth)):
            next_frontier: list[str] = []
            with self._conn() as conn:
                for nid in frontier:
                    rows = conn.execute(
                        """SELECT * FROM asset_graph_edges
                           WHERE source_id=? OR target_id=?""",
                        (nid, nid),
                    ).fetchall()
                    for row in rows:
                        edge = dict(row)
                        edges.append(edge)
                        for candidate in (edge["source_id"], edge["target_id"]):
                            if candidate not in seen:
                                seen.add(candidate)
                                next_frontier.append(candidate)
                                node = conn.execute(
                                    "SELECT * FROM asset_graph_nodes WHERE id=?", (candidate,)
                                ).fetchone()
                                if node:
                                    nodes.append(dict(node))
            frontier = next_frontier
            if not frontier:
                break
        root = self.get_node(node_id)
        return {
            "root": root,
            "nodes": nodes,
            "edges": _dedupe_edges(edges),
            "node_count": len(nodes) + (1 if root else 0),
            "edge_count": len(_dedupe_edges(edges)),
        }

    def attack_paths(self, limit: int = 20) -> list[dict[str, Any]]:
        """Device → port → service → vulnerability chains that reach a finding."""
        paths: list[dict[str, Any]] = []
        with self._conn() as conn:
            devices = conn.execute(
                "SELECT * FROM asset_graph_nodes WHERE node_type='device' LIMIT 100"
            ).fetchall()
            for device in devices:
                ips = conn.execute(
                    "SELECT target_id FROM asset_graph_edges WHERE source_id=? AND relation='has_ip'",
                    (device["id"],),
                ).fetchall()
                for ip in ips:
                    ports = conn.execute(
                        "SELECT target_id FROM asset_graph_edges WHERE source_id=? AND relation='exposes_port'",
                        (ip["target_id"],),
                    ).fetchall()
                    for port in ports:
                        services = conn.execute(
                            "SELECT target_id FROM asset_graph_edges WHERE source_id=? AND relation='runs_service'",
                            (port["target_id"],),
                        ).fetchall()
                        for service in services:
                            service_node = conn.execute(
                                "SELECT * FROM asset_graph_nodes WHERE id=?", (service["target_id"],)
                            ).fetchone()
                            vulns = conn.execute(
                                """SELECT n.* FROM asset_graph_edges e
                                   JOIN asset_graph_nodes n ON n.id = e.target_id
                                   WHERE e.source_id=? AND e.relation='affected_by'""",
                                (service["target_id"],),
                            ).fetchall()
                            for vuln in vulns:
                                paths.append({
                                    "device": device["name"],
                                    "service": service_node["name"] if service_node else "unknown",
                                    "vulnerability": vuln["name"],
                                    "severity": json.loads(vuln["properties"] or "{}").get("severity", "unknown"),
                                    "risk_score": vuln["risk_score"],
                                })
                    # device-level findings
                    device_vulns = conn.execute(
                        """SELECT n.* FROM asset_graph_edges e
                           JOIN asset_graph_nodes n ON n.id = e.target_id
                           WHERE e.source_id=? AND e.relation='affected_by'""",
                        (device["id"],),
                    ).fetchall()
                    for vuln in device_vulns:
                        paths.append({
                            "device": device["name"],
                            "service": "device-level",
                            "vulnerability": vuln["name"],
                            "severity": json.loads(vuln["properties"] or "{}").get("severity", "unknown"),
                            "risk_score": vuln["risk_score"],
                        })
        paths.sort(key=lambda p: p.get("risk_score") or 0, reverse=True)
        return paths[:limit]

    def risk_summary(self) -> dict[str, Any]:
        with self._conn() as conn:
            by_type = {
                row["node_type"]: row["c"]
                for row in conn.execute(
                    "SELECT node_type, COUNT(*) AS c FROM asset_graph_nodes GROUP BY node_type"
                )
            }
            by_relation = {
                row["relation"]: row["c"]
                for row in conn.execute(
                    "SELECT relation, COUNT(*) AS c FROM asset_graph_edges GROUP BY relation"
                )
            }
            top_risk = [
                dict(r) for r in conn.execute(
                    "SELECT node_type, name, risk_score FROM asset_graph_nodes ORDER BY risk_score DESC LIMIT 10"
                )
            ]
            high_risk = conn.execute(
                "SELECT COUNT(*) FROM asset_graph_nodes WHERE risk_score >= 7.0"
            ).fetchone()[0]
        return {
            "nodes_by_type": by_type,
            "edges_by_relation": by_relation,
            "total_nodes": sum(by_type.values()),
            "total_edges": sum(by_relation.values()),
            "high_risk_nodes": high_risk,
            "top_risk": top_risk,
        }

    def reset(self) -> dict[str, int]:
        """Clear graph data only — never touches the security scan tables."""
        with self._conn() as conn:
            edges = conn.execute("SELECT COUNT(*) FROM asset_graph_edges").fetchone()[0]
            nodes = conn.execute("SELECT COUNT(*) FROM asset_graph_nodes").fetchone()[0]
            conn.execute("DELETE FROM asset_graph_edges")
            conn.execute("DELETE FROM asset_graph_nodes")
            conn.commit()
        return {"removed_nodes": nodes, "removed_edges": edges}


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for e in edges:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        out.append(e)
    return out


_graph: SecurityAssetGraph | None = None


def get_security_graph() -> SecurityAssetGraph:
    global _graph
    if _graph is None:
        _graph = SecurityAssetGraph()
    return _graph
