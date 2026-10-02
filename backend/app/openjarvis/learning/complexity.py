"""Complexity Analyzer - Scores query complexity and suggests model tier.

Ported from OpenJARVIS (Stanford Hazy Research).
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComplexityResult:
    score: float
    tier: str
    suggested_max_tokens: int
    signals: dict[str, Any] = field(default_factory=dict)


class ComplexityAnalyzer:
    CODE_PATTERNS = [
        r"def\s+\w+", r"class\s+\w+", r"import\s+\w+", r"from\s+\w+\s+import",
        r"function\s+\w+", r"const\s+\w+", r"let\s+\w+", r"var\s+\w+",
        r"if\s*\(", r"for\s*\(", r"while\s*\(", r"=>", r"lambda\s+",
        r"\w+\.\w+\(", r"print\s*\(", r"return\s+",
    ]

    MATH_PATTERNS = [
        r"\d+\s*[+\-*/]\s*\d+", r"equation", r"solve", r"integral",
        r"derivative", r"theorem", r"proof", r"matrix", r"vector",
        r"sum_", r"product_", r"lim_", r"\\frac", r"\\sqrt",
    ]

    REASONING_PATTERNS = [
        r"why\s+", r"how\s+does", r"explain", r"analyze", r"compare",
        r"evaluate", r"assess", r"reason", r"because", r"therefore",
        r"consequently", r"step.by.step", r"break.down",
    ]

    MULTI_STEP_PATTERNS = [
        r"first.*then", r"step\s+\d", r"1\..*2\..*3\.",
        r"multiple", r"several", r"each", r"all of",
    ]

    CREATIVE_PATTERNS = [
        r"write\s+(a|an|the)", r"create", r"generate", r"compose",
        r"design", r"imagine", r"story", r"poem", r"essay",
    ]

    def analyze(self, query: str) -> ComplexityResult:
        signals = {}
        score = 0.0

        signals["length"] = len(query)
        if len(query) > 500:
            score += 0.15
        elif len(query) > 200:
            score += 0.08
        elif len(query) > 50:
            score += 0.03

        code_hits = sum(1 for p in self.CODE_PATTERNS if re.search(p, query, re.IGNORECASE))
        signals["code_patterns"] = code_hits
        if code_hits >= 3:
            score += 0.25
        elif code_hits >= 1:
            score += 0.12

        math_hits = sum(1 for p in self.MATH_PATTERNS if re.search(p, query, re.IGNORECASE))
        signals["math_patterns"] = math_hits
        if math_hits >= 2:
            score += 0.25
        elif math_hits >= 1:
            score += 0.12

        reasoning_hits = sum(1 for p in self.REASONING_PATTERNS if re.search(p, query, re.IGNORECASE))
        signals["reasoning_patterns"] = reasoning_hits
        if reasoning_hits >= 3:
            score += 0.2
        elif reasoning_hits >= 1:
            score += 0.1

        multi_hits = sum(1 for p in self.MULTI_STEP_PATTERNS if re.search(p, query, re.IGNORECASE))
        signals["multi_step_patterns"] = multi_hits
        if multi_hits >= 2:
            score += 0.15

        creative_hits = sum(1 for p in self.CREATIVE_PATTERNS if re.search(p, query, re.IGNORECASE))
        signals["creative_patterns"] = creative_hits
        if creative_hits >= 1:
            score += 0.05

        score = min(score, 1.0)
        signals["total_score"] = score

        if score <= 0.15:
            tier = "trivial"
            tokens = 1024
        elif score <= 0.30:
            tier = "simple"
            tokens = 2048
        elif score <= 0.50:
            tier = "moderate"
            tokens = 4096
        elif score <= 0.75:
            tier = "complex"
            tokens = 8192
        else:
            tier = "very_complex"
            tokens = 16384

        return ComplexityResult(score=score, tier=tier, suggested_max_tokens=tokens, signals=signals)
