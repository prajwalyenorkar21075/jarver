"""PLC program analysis for JARVIS.

Reads real PLC source exports (ladder listings, Structured Text) and answers
engineering questions about them: what the logic does, what is unreachable,
what looks wrong, what to test, and a documentation draft.

Supported inputs
    Structured Text (.st / .scl / .txt with ST syntax)
    Ladder listings (.lad / .csv / .txt exported as ``rung``/``TON``/``XIC`` text)

Unsupported formats are reported as unsupported — this module never guesses at
a binary project file.

Generating code is always a draft: nothing here deploys to hardware.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("jarvis.plc")


@dataclass
class PlcTag:
    name: str
    data_type: str = ""
    address: str = ""
    comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "data_type": self.data_type,
                "address": self.address, "comment": self.comment}


@dataclass
class PlcFinding:
    severity: str
    category: str
    title: str
    detail: str
    line: int = 0
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "category": self.category, "title": self.title,
                "detail": self.detail, "line": self.line, "remediation": self.remediation}


# --------------------------------------------------------------------------- #
# Structured Text analysis
# --------------------------------------------------------------------------- #
_ST_ASSIGN = re.compile(r"^\s*([A-Za-z_][\w\.\[\]]*)\s*:=\s*(.+?);", re.MULTILINE)
_ST_IF = re.compile(r"\bIF\b(.+?)\bTHEN\b", re.IGNORECASE | re.DOTALL)
_ST_ELSIF = re.compile(r"\bELSIF\b(.+?)\bTHEN\b", re.IGNORECASE | re.DOTALL)
_ST_ELSE = re.compile(r"\bELSE\b", re.IGNORECASE)
_ST_ENDIF = re.compile(r"\bEND_IF\b", re.IGNORECASE)
_ST_CASE = re.compile(r"\bCASE\b(.+?)\bOF\b", re.IGNORECASE | re.DOTALL)
_ST_ENDCASE = re.compile(r"\bEND_CASE\b", re.IGNORECASE)
_ST_TIMER = re.compile(r"\b(TON|TOF|TP|TONR)\b", re.IGNORECASE)
_ST_COUNTER = re.compile(r"\b(CTU|CTD|CTUD)\b", re.IGNORECASE)
_ST_FOR = re.compile(r"\bFOR\b(.+?)\bTO\b(.+?)\bDO\b", re.IGNORECASE | re.DOTALL)
_ST_WHILE = re.compile(r"\bWHILE\b(.+?)\bDO\b", re.IGNORECASE | re.DOTALL)
_ST_DANGEROUS = re.compile(
    r"\b(JMP|GOTO|RET|EXIT|CONTINUE)\b|\b(SET|RESET)\s*\(", re.IGNORECASE
)

# Ladder mnemonic analysis
_LADDER_INSTR = re.compile(
    r"\b(XIC|XIO|OTE|OTL|OTU|ONS|OSR|OSF|TON|TOF|RTO|CTU|CTD|RES|MOV|COP|ADD|SUB|MUL|DIV|EQU|NEQ|GRT|LES|GEQ|LEQ|JSR|JMP|LBL|MCR|AFI)\b",
    re.IGNORECASE,
)
_LADDER_RUNG = re.compile(r"^\s*(?:rung\s*\d+|\[?\d+\]?[:.)])\s*(.+)$", re.IGNORECASE)


class PlcAnalyzer:
    def __init__(self):
        self._analyses: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Format detection
    # ------------------------------------------------------------------ #
    def detect_format(self, source: str, filename: str = "") -> str:
        name = filename.lower()
        if name.endswith((".st", ".scl", ".stl")):
            return "structured_text"
        if name.endswith((".lad", ".rss", ".l5x", ".csv")):
            return "ladder_listing"
        if name.endswith((".acd", ".ap16", ".zap16", ".project")):
            return "unsupported_binary"

        st_markers = len(re.findall(r"\b(END_IF|END_CASE|ELSIF|VAR|END_VAR|:=)\b", source, re.IGNORECASE))
        ladder_markers = len(_LADDER_INSTR.findall(source))
        if st_markers >= ladder_markers and st_markers > 0:
            return "structured_text"
        if ladder_markers > 0:
            return "ladder_listing"
        return "unknown"

    # ------------------------------------------------------------------ #
    # Tag extraction
    # ------------------------------------------------------------------ #
    def extract_tags(self, source: str) -> list[PlcTag]:
        tags: dict[str, PlcTag] = {}

        # VAR blocks: name : TYPE := init;
        for block in re.findall(r"\bVAR(?:_INPUT|_OUTPUT|_IN_OUT|_GLOBAL|_TEMP)?\b(.*?)\bEND_VAR\b",
                                source, re.IGNORECASE | re.DOTALL):
            for match in re.finditer(
                r"^\s*([A-Za-z_]\w*)\s*:\s*([A-Za-z_][\w\.\[\]\(\)]*)\s*(?::=\s*([^;]+))?\s*;",
                block, re.MULTILINE,
            ):
                name, dtype = match.group(1), match.group(2)
                tags[name] = PlcTag(name=name, data_type=dtype)

        # Assignment targets that were not declared
        for match in _ST_ASSIGN.finditer(source):
            name = match.group(1)
            if name not in tags:
                tags[name] = PlcTag(name=name, data_type="implicit")

        # Ladder-style addresses, e.g. B3:0/0, N7:12, I:1/0, O:2/3, T4:0.ACC
        for match in re.finditer(r"\b([BIOTNFC]\d+:\d+(?:[/.]\w+)?)\b", source):
            address = match.group(1)
            tags.setdefault(address, PlcTag(name=address, data_type="ladder_address"))

        return list(tags.values())

    # ------------------------------------------------------------------ #
    # Structured Text analysis
    # ------------------------------------------------------------------ #
    def _analyze_structured_text(self, source: str) -> dict[str, Any]:
        findings: list[PlcFinding] = []
        lines = source.splitlines()

        if_count = len(_ST_IF.findall(source))
        endif_count = len(_ST_ENDIF.findall(source))
        if if_count != endif_count:
            findings.append(PlcFinding(
                severity="high", category="structure", title="Unbalanced IF/END_IF",
                detail=f"{if_count} IF blocks but {endif_count} END_IF statements",
                remediation="Every IF must have a matching END_IF; unmatched blocks will not compile.",
            ))

        case_count = len(_ST_CASE.findall(source))
        endcase_count = len(_ST_ENDCASE.findall(source))
        if case_count != endcase_count:
            findings.append(PlcFinding(
                severity="high", category="structure", title="Unbalanced CASE/END_CASE",
                detail=f"{case_count} CASE blocks but {endcase_count} END_CASE statements",
                remediation="Close every CASE with END_CASE.",
            ))

        # ELSE-less IF chains that only ever set outputs (common logic error)
        for match in re.finditer(r"\bIF\b(.*?)\bEND_IF\b", source, re.IGNORECASE | re.DOTALL):
            body = match.group(1)
            if "ELSE" not in body.upper() and _ST_ASSIGN.search(body):
                line = source[:match.start()].count("\n") + 1
                findings.append(PlcFinding(
                    severity="low", category="logic", title="IF without ELSE assigns outputs",
                    detail="An IF branch assigns values but there is no ELSE path.",
                    line=line,
                    remediation="Confirm the output holds its previous value when the condition is false, "
                                "or add an explicit ELSE to make the behaviour unambiguous.",
                ))

        # Outputs assigned in more than one place (last-write-wins hazard)
        assignments: dict[str, list[int]] = {}
        for match in _ST_ASSIGN.finditer(source):
            target = match.group(1)
            line = source[:match.start()].count("\n") + 1
            assignments.setdefault(target, []).append(line)
        for target, where in assignments.items():
            if len(where) > 2 and not target.startswith(("temp", "TMP", "_")):
                findings.append(PlcFinding(
                    severity="medium", category="logic", title=f"Repeated assignment to {target}",
                    detail=f"{target} is written at lines {where}",
                    line=where[0],
                    remediation="Multiple writes to the same output make the final value order-dependent. "
                                "Consolidate into a single decision block.",
                ))

        # Unreachable code after unconditional control transfer
        for i, line in enumerate(lines):
            if re.search(r"\b(RETURN|JMP|GOTO|EXIT)\b", line, re.IGNORECASE):
                following = [l for l in lines[i + 1:i + 4] if l.strip() and not l.strip().startswith("//")]
                if following:
                    findings.append(PlcFinding(
                        severity="medium", category="unreachable",
                        title="Code after unconditional transfer",
                        detail=f"Line {i + 1} transfers control; the following statements may never execute: "
                               f"{following[0].strip()[:60]}",
                        line=i + 1,
                        remediation="Remove the dead statements or confirm the transfer is conditional.",
                    ))
                    break

        # Timers/counters used without their done bit being read
        timers = set(_ST_TIMER.findall(source))
        counters = set(_ST_COUNTER.findall(source))
        if timers and not re.search(r"\.(Q|DN|DONE)\b", source, re.IGNORECASE):
            findings.append(PlcFinding(
                severity="medium", category="logic", title="Timer done bit never evaluated",
                detail=f"Timer(s) {sorted(timers)} are instantiated but no .Q/.DN bit is read.",
                remediation="Read the timer done bit (or remove the unused timer) so the timing actually gates logic.",
            ))
        if counters and not re.search(r"\.(Q|DN|DONE|CV)\b", source, re.IGNORECASE):
            findings.append(PlcFinding(
                severity="low", category="logic", title="Counter result never used",
                detail=f"Counter(s) {sorted(counters)} are instantiated but no done/current value is read.",
                remediation="Use the counter's done bit or current value, or delete the unused counter.",
            ))

        # Safety-relevant signals written directly
        safety_terms = ("estop", "e_stop", "emergency", "guard", "interlock", "safety")
        for match in _ST_ASSIGN.finditer(source):
            target = match.group(1).lower()
            if any(term in target for term in safety_terms):
                line = source[:match.start()].count("\n") + 1
                findings.append(PlcFinding(
                    severity="critical", category="safety",
                    title=f"Program writes a safety-related signal: {match.group(1)}",
                    detail="Safety functions must be handled by the safety system, not ordinary program logic.",
                    line=line,
                    remediation="Route safety interlocks through the certified safety PLC/relay. "
                                "Standard logic must never override them.",
                ))

        structures = []
        for match in _ST_IF.finditer(source):
            structures.append({"type": "if", "condition": match.group(1).strip()[:120],
                               "line": source[:match.start()].count("\n") + 1})
        for match in _ST_CASE.finditer(source):
            structures.append({"type": "case", "selector": match.group(1).strip()[:120],
                               "line": source[:match.start()].count("\n") + 1})
        for match in _ST_FOR.finditer(source):
            structures.append({"type": "for", "detail": f"{match.group(1).strip()} TO {match.group(2).strip()}",
                               "line": source[:match.start()].count("\n") + 1})
        for match in _ST_WHILE.finditer(source):
            structures.append({"type": "while", "detail": match.group(1).strip()[:120],
                               "line": source[:match.start()].count("\n") + 1})

        return {
            "language": "structured_text",
            "structures": structures,
            "findings": [f.to_dict() for f in findings],
            "metrics": {
                "lines": len(lines),
                "assignments": len(_ST_ASSIGN.findall(source)),
                "if_blocks": if_count,
                "case_blocks": case_count,
                "timers": sorted(timers),
                "counters": sorted(counters),
                "control_transfers": len(_ST_DANGEROUS.findall(source)),
            },
        }

    # ------------------------------------------------------------------ #
    # Ladder analysis
    # ------------------------------------------------------------------ #
    def _analyze_ladder(self, source: str) -> dict[str, Any]:
        findings: list[PlcFinding] = []
        rungs = [m.group(1) for m in _LADDER_RUNG.finditer(source)]
        if not rungs:
            rungs = [line for line in source.splitlines() if _LADDER_INSTR.search(line)]

        instructions: dict[str, int] = {}
        for rung in rungs:
            for instr in _LADDER_INSTR.findall(rung):
                key = instr.upper()
                instructions[key] = instructions.get(key, 0) + 1

        output_instructions = {"OTE", "OTL", "OTU"}
        conditional = {"XIC", "XIO", "EQU", "NEQ", "GRT", "LES", "GEQ", "LEQ"}

        for index, rung in enumerate(rungs, start=1):
            ops = {i.upper() for i in _LADDER_INSTR.findall(rung)}
            if ops & output_instructions and not ops & conditional:
                findings.append(PlcFinding(
                    severity="medium", category="logic",
                    title=f"Rung {index} drives an output with no conditional input",
                    detail=rung.strip()[:160],
                    line=index,
                    remediation="An unconditional output is either a deliberate always-on or a missing "
                                "condition. Add the intended input contact.",
                ))

        # Rungs after an unconditional JMP/LBL pairing
        jump_targets = set()
        labels = set()
        for rung in rungs:
            for match in re.finditer(r"\bJMP\b\s*\(?([A-Za-z0-9_]+)\)?", rung, re.IGNORECASE):
                jump_targets.add(match.group(1))
            for match in re.finditer(r"\bLBL\b\s*\(?([A-Za-z0-9_]+)\)?", rung, re.IGNORECASE):
                labels.add(match.group(1))
        for target in jump_targets - labels:
            findings.append(PlcFinding(
                severity="high", category="structure", title=f"JMP to undefined label '{target}'",
                detail="A jump targets a label that does not exist in the listing.",
                remediation="Define the label or remove the jump; an undefined label will not compile.",
            ))
        for label in labels - jump_targets:
            findings.append(PlcFinding(
                severity="low", category="unreachable", title=f"Label '{label}' is never jumped to",
                detail="The label exists but no JMP references it.",
                remediation="Remove the orphan label or restore the jump.",
            ))

        if "AFI" in instructions:
            findings.append(PlcFinding(
                severity="info", category="unreachable", title="AFI (Always False Instruction) present",
                detail=f"{instructions['AFI']} rung(s) are deliberately disabled with AFI.",
                remediation="Confirm these rungs are intentionally disabled; remove them once verified.",
            ))
        if "MCR" in instructions:
            findings.append(PlcFinding(
                severity="medium", category="safety", title="Master Control Relay (MCR) zone used",
                detail="MCR zones disable outputs across a region and are easy to misread.",
                remediation="Verify the MCR zone boundaries and that no safety output is inside one.",
            ))

        structures = [{"type": "rung", "index": i + 1, "detail": r.strip()[:160]} for i, r in enumerate(rungs)]

        return {
            "language": "ladder_listing",
            "structures": structures,
            "findings": [f.to_dict() for f in findings],
            "metrics": {
                "rungs": len(rungs),
                "instructions": instructions,
                "jump_targets": sorted(jump_targets),
                "labels": sorted(labels),
            },
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(self, source: str, filename: str = "") -> dict[str, Any]:
        fmt = self.detect_format(source, filename)
        analysis_id = str(uuid.uuid4())[:10]

        if fmt == "unsupported_binary":
            result = {
                "analysis_id": analysis_id,
                "filename": filename,
                "format": fmt,
                "supported": False,
                "error": "Binary PLC project files are not supported. Export the routine as "
                         "Structured Text or a ladder listing and analyze that instead.",
                "findings": [],
            }
            self._analyses.append(result)
            return result

        if fmt == "structured_text":
            core = self._analyze_structured_text(source)
        elif fmt == "ladder_listing":
            core = self._analyze_ladder(source)
        else:
            core = {
                "language": "unknown",
                "structures": [],
                "findings": [PlcFinding(
                    severity="info", category="format", title="Unrecognised PLC source format",
                    detail="The content did not match Structured Text or ladder listing syntax.",
                    remediation="Export the routine as .st (Structured Text) or a rung listing.",
                ).to_dict()],
                "metrics": {"lines": len(source.splitlines())},
            }

        tags = self.extract_tags(source)
        result = {
            "analysis_id": analysis_id,
            "filename": filename,
            "format": fmt,
            "supported": True,
            "analyzed_at": time.time(),
            "tags": [t.to_dict() for t in tags],
            "tag_count": len(tags),
            **core,
            "finding_count": len(core["findings"]),
            "severity_counts": _count_severities(core["findings"]),
        }
        self._analyses.append(result)
        if len(self._analyses) > 100:
            self._analyses = self._analyses[-100:]
        logger.info(f"[PLC] Analyzed {filename or 'inline source'} ({fmt}): "
                    f"{result['finding_count']} findings")
        return result

    def analyze_file(self, path: str) -> dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                source = handle.read()
        except Exception as e:
            return {"supported": False, "error": f"Could not read '{path}': {e}", "findings": []}
        import os
        return self.analyze(source, os.path.basename(path))

    def explain(self, analysis: dict[str, Any]) -> str:
        """Plain-language explanation of an analyzed program."""
        if not analysis.get("supported", True):
            return analysis.get("error", "This program could not be analyzed.")

        lines = [
            f"Program: {analysis.get('filename') or 'inline source'} "
            f"({analysis.get('format')})",
            f"Tags declared: {analysis.get('tag_count', 0)}",
        ]
        metrics = analysis.get("metrics", {})
        if analysis.get("format") == "structured_text":
            lines.append(
                f"Structure: {metrics.get('if_blocks', 0)} IF blocks, "
                f"{metrics.get('case_blocks', 0)} CASE blocks, "
                f"{metrics.get('assignments', 0)} assignments"
            )
            if metrics.get("timers"):
                lines.append(f"Timers: {', '.join(metrics['timers'])}")
            if metrics.get("counters"):
                lines.append(f"Counters: {', '.join(metrics['counters'])}")
        else:
            lines.append(f"Rungs: {metrics.get('rungs', 0)}")
            instr = metrics.get("instructions") or {}
            if instr:
                lines.append("Instructions: " + ", ".join(f"{k}×{v}" for k, v in sorted(instr.items())))

        counts = analysis.get("severity_counts") or {}
        if counts:
            lines.append("Findings: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        else:
            lines.append("Findings: none — no structural or logic problems detected")
        return "\n".join(lines)

    def generate_test_cases(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Derive concrete test cases from the analyzed structure."""
        cases: list[dict[str, Any]] = []
        structures = analysis.get("structures", [])

        for structure in structures:
            if structure["type"] == "if":
                condition = structure.get("condition", "condition")
                cases.append({
                    "name": f"IF branch true at line {structure.get('line', 0)}",
                    "given": f"{condition} evaluates TRUE",
                    "expect": "The statements inside the IF block execute",
                    "type": "logic",
                })
                cases.append({
                    "name": f"IF branch false at line {structure.get('line', 0)}",
                    "given": f"{condition} evaluates FALSE",
                    "expect": "Outputs hold their previous value or take the ELSE path",
                    "type": "logic",
                })
            elif structure["type"] == "case":
                cases.append({
                    "name": f"CASE selector at line {structure.get('line', 0)}",
                    "given": f"selector value = {structure.get('selector', 'unknown')} with an unmatched value",
                    "expect": "The ELSE branch runs, or no branch runs if there is no ELSE",
                    "type": "logic",
                })
            elif structure["type"] == "for":
                cases.append({
                    "name": "FOR loop bounds",
                    "given": structure.get("detail", "loop bounds"),
                    "expect": "Loop terminates; no off-by-one on the final index",
                    "type": "boundary",
                })
            elif structure["type"] == "while":
                cases.append({
                    "name": "WHILE loop termination",
                    "given": structure.get("detail", "loop condition"),
                    "expect": "The condition can become false; scan time stays within budget",
                    "type": "boundary",
                })

        metrics = analysis.get("metrics", {})
        for timer in metrics.get("timers", []):
            cases.append({
                "name": f"Timer {timer} preset reached",
                "given": f"{timer} accumulates past its preset",
                "expect": "The done bit sets and the gated logic runs exactly once per cycle",
                "type": "timing",
            })
        for counter in metrics.get("counters", []):
            cases.append({
                "name": f"Counter {counter} preset reached",
                "given": f"{counter} counts to its preset",
                "expect": "The done bit sets and is reset by the intended reset condition",
                "type": "timing",
            })

        for finding in analysis.get("findings", []):
            if finding.get("category") == "safety":
                cases.append({
                    "name": f"Safety check: {finding['title']}",
                    "given": "The safety condition is triggered while the program is running",
                    "expect": "The safety system stops the machine independently of program logic",
                    "type": "safety",
                })
            elif finding.get("category") in ("logic", "unreachable"):
                cases.append({
                    "name": f"Regression check: {finding['title']}",
                    "given": finding.get("detail", ""),
                    "expect": "The behaviour is confirmed intentional, or the finding is fixed",
                    "type": "regression",
                })

        if not cases:
            cases.append({
                "name": "Baseline scan",
                "given": "Program loaded, inputs at nominal values",
                "expect": "Outputs match the documented behaviour and no alarms are raised",
                "type": "baseline",
            })

        return {
            "analysis_id": analysis.get("analysis_id"),
            "case_count": len(cases),
            "cases": cases,
            "note": "Test cases are derived from static analysis and must be run in a simulator or "
                    "an offline PLC before touching production hardware.",
        }

    def generate_documentation(self, analysis: dict[str, Any]) -> str:
        """Draft documentation for the analyzed program."""
        if not analysis.get("supported", True):
            return f"# PLC Program\n\nNot analyzed: {analysis.get('error')}"

        metrics = analysis.get("metrics", {})
        doc = [
            f"# PLC Program Documentation — {analysis.get('filename') or 'inline source'}",
            "",
            f"- Format: {analysis.get('format')}",
            f"- Analyzed: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(analysis.get('analyzed_at', time.time())))}",
            f"- Tags: {analysis.get('tag_count', 0)}",
        ]
        if analysis.get("format") == "structured_text":
            doc.append(f"- IF blocks: {metrics.get('if_blocks', 0)}")
            doc.append(f"- CASE blocks: {metrics.get('case_blocks', 0)}")
            doc.append(f"- Assignments: {metrics.get('assignments', 0)}")
        else:
            doc.append(f"- Rungs: {metrics.get('rungs', 0)}")

        doc.append("")
        doc.append("## Tag list")
        doc.append("")
        doc.append("| Tag | Type | Address |")
        doc.append("|-----|------|---------|")
        for tag in analysis.get("tags", [])[:200]:
            doc.append(f"| {tag['name']} | {tag['data_type']} | {tag['address'] or '—'} |")

        doc.append("")
        doc.append("## Structure")
        doc.append("")
        for structure in analysis.get("structures", [])[:100]:
            detail = structure.get("condition") or structure.get("selector") or structure.get("detail", "")
            doc.append(f"- `{structure['type']}` (line {structure.get('line', '?')}): {detail}")

        doc.append("")
        doc.append("## Findings")
        doc.append("")
        findings = analysis.get("findings", [])
        if not findings:
            doc.append("No structural or logic problems detected by static analysis.")
        for finding in findings:
            doc.append(f"- **[{finding['severity'].upper()}] {finding['title']}** "
                       f"(line {finding.get('line', '?')}): {finding['detail']}")
            if finding.get("remediation"):
                doc.append(f"  - Fix: {finding['remediation']}")

        doc.append("")
        doc.append("## Change control")
        doc.append("")
        doc.append("This document is generated from static analysis. Any change derived from it must be "
                   "reviewed, simulated, and validated offline before being deployed to production hardware.")
        return "\n".join(doc)

    def generate_draft(self, spec: str) -> dict[str, Any]:
        """Produce a Structured Text draft from a plain-language spec.

        This is a draft for a human to review — it is never deployed.
        """
        spec_lower = spec.lower()
        lines = [
            "(* ============================================================",
            "   DRAFT GENERATED BY J.A.R.V.I.S. — REQUIRES ENGINEERING REVIEW",
            f"   Spec: {spec.strip()[:120]}",
            "   This routine has NOT been deployed to any PLC.",
            "   ============================================================ *)",
            "",
            "FUNCTION_BLOCK FB_DraftRoutine",
            "VAR_INPUT",
            "    StartCmd    : BOOL;      (* operator start *)",
            "    StopCmd     : BOOL;      (* operator stop  *)",
            "    SafetyOK    : BOOL;      (* from safety system, read-only here *)",
            "END_VAR",
            "VAR_OUTPUT",
            "    RunEnable   : BOOL;",
            "    CycleCount  : UDINT;",
            "END_VAR",
            "VAR",
            "    RunLatch    : BOOL;",
            "    CycleTimer  : TON;",
            "    CycleTime   : TIME := T#500MS;",
            "END_VAR",
            "",
            "(* Safety: the interlock is read, never written. If the safety chain",
            "   drops, RunEnable falls immediately. *)",
            "IF NOT SafetyOK THEN",
            "    RunLatch := FALSE;",
            "    RunEnable := FALSE;",
            "    CycleTimer(IN := FALSE, PT := CycleTime);",
            "    RETURN;",
            "END_IF;",
            "",
            "(* Start / stop latch with an explicit stop that wins over start *)",
            "IF StopCmd THEN",
            "    RunLatch := FALSE;",
            "ELSIF StartCmd THEN",
            "    RunLatch := TRUE;",
            "END_IF;",
            "",
            "RunEnable := RunLatch;",
            "",
            "(* Cycle timing: only counts while running *)",
            "CycleTimer(IN := RunEnable, PT := CycleTime);",
            "IF CycleTimer.Q THEN",
            "    CycleCount := CycleCount + 1;",
            "    CycleTimer(IN := FALSE, PT := CycleTime);",
            "END_IF;",
            "",
            "END_FUNCTION_BLOCK",
        ]
        if "conveyor" in spec_lower:
            lines.insert(30, "(* NOTE: conveyor speed must be commanded through the drive, not a raw output. *)")
        if "alarm" in spec_lower or "fault" in spec_lower:
            lines.insert(30, "(* NOTE: raise faults as alarm records with a code, not as bare bits. *)")

        return {
            "language": "structured_text",
            "draft": "\n".join(lines),
            "review_required": True,
            "deployed": False,
            "warning": "Draft only. Simulate and validate before any deployment; JARVIS never writes "
                       "logic to production hardware automatically.",
        }

    def get_analyses(self, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "analysis_id": a.get("analysis_id"),
                "filename": a.get("filename"),
                "format": a.get("format"),
                "finding_count": a.get("finding_count", 0),
                "severity_counts": a.get("severity_counts", {}),
            }
            for a in self._analyses[-limit:]
        ]


def _count_severities(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        severity = finding.get("severity", "info")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


_analyzer: PlcAnalyzer | None = None


def get_plc_analyzer() -> PlcAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PlcAnalyzer()
    return _analyzer
