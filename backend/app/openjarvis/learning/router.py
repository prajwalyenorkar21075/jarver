"""Heuristic Router - Rule-based model selection based on query analysis.

Ported from OpenJARVIS (Stanford Hazy Research).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.openjarvis.learning.complexity import ComplexityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class RoutingContext:
    query: str
    complexity_score: float = 0.0
    complexity_tier: str = "simple"
    has_code: bool = False
    has_math: bool = False
    has_reasoning: bool = False
    urgency: float = 0.0
    suggested_tokens: int = 2048
    signals: dict[str, Any] = field(default_factory=dict)


class HeuristicRouter:
    def __init__(self, models: dict[str, str] | None = None):
        self._analyzer = ComplexityAnalyzer()
        self._models = models or {
            "small": "gpt-4o-mini",
            "default": "gpt-4o",
            "large": "gpt-4o",
            "code": "gpt-4o",
        }

    def set_models(self, models: dict[str, str]) -> None:
        self._models.update(models)

    def build_context(self, query: str) -> RoutingContext:
        complexity = self._analyzer.analyze(query)

        ctx = RoutingContext(
            query=query,
            complexity_score=complexity.score,
            complexity_tier=complexity.tier,
            has_code=complexity.signals.get("code_patterns", 0) > 0,
            has_math=complexity.signals.get("math_patterns", 0) > 0,
            has_reasoning=complexity.signals.get("reasoning_patterns", 0) > 0,
            suggested_tokens=complexity.suggested_max_tokens,
            signals=complexity.signals,
        )

        urgency_patterns = [r"urgent", r"asap", r"immediately", r"right now", r"emergency"]
        urgency_hits = sum(1 for p in urgency_patterns if re.search(p, query, re.IGNORECASE))
        ctx.urgency = min(urgency_hits * 0.3, 1.0)

        return ctx

    def route(self, query: str) -> dict[str, Any]:
        ctx = self.build_context(query)
        model = self._select_model(ctx)

        return {
            "model": model,
            "max_tokens": ctx.suggested_tokens,
            "complexity": ctx.complexity_tier,
            "complexity_score": ctx.complexity_score,
            "reason": self._explain_routing(ctx, model),
        }

    def _select_model(self, ctx: RoutingContext) -> str:
        if ctx.urgency > 0.8:
            return self._models.get("small", "gpt-4o-mini")

        if ctx.has_code:
            return self._models.get("code", self._models.get("default", "gpt-4o"))

        if ctx.complexity_score <= 0.20:
            return self._models.get("small", "gpt-4o-mini")

        if ctx.has_math:
            return self._models.get("large", "gpt-4o")

        if ctx.complexity_score >= 0.55 or ctx.has_reasoning:
            return self._models.get("large", "gpt-4o")

        return self._models.get("default", "gpt-4o")

    def _explain_routing(self, ctx: RoutingContext, model: str) -> str:
        reasons = []
        if ctx.urgency > 0.8:
            reasons.append("high urgency -> fast model")
        if ctx.has_code:
            reasons.append("code detected -> code model")
        if ctx.complexity_score <= 0.20:
            reasons.append(f"low complexity ({ctx.complexity_score:.2f}) -> small model")
        if ctx.has_math:
            reasons.append("math detected -> large model")
        if ctx.complexity_score >= 0.55:
            reasons.append(f"high complexity ({ctx.complexity_score:.2f}) -> large model")
        if ctx.has_reasoning:
            reasons.append("reasoning required -> large model")
        if not reasons:
            reasons.append("default routing")
        return "; ".join(reasons)
