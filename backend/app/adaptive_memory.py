"""Adaptive Memory System for JARVIS.

Enhances existing persistent memory with:
- Importance scoring, relevance, confidence
- Source tracking, privacy/security classification
- Learning from failures and success patterns
- Short-term conversation memory, long-term preferences
- Task history, agent performance history
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("jarvis.adaptive_memory")


class PrivacyLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PRIVATE = "PRIVATE"
    SECRET = "SECRET"


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    PREFERENCE = "preference"
    TASK_HISTORY = "task_history"
    FAILURE_PATTERN = "failure_pattern"
    SUCCESS_PATTERN = "success_pattern"
    TOOL_USAGE = "tool_usage"
    AGENT_PERFORMANCE = "agent_performance"
    ROBOTICS_KNOWLEDGE = "robotics_knowledge"
    USER_CORRECTION = "user_correction"


@dataclass
class MemoryEntry:
    id: str = ""
    memory_type: MemoryType = MemoryType.CONVERSATION
    content: str = ""
    source: str = ""
    importance: float = 0.5
    relevance: float = 0.5
    confidence: float = 0.8
    privacy: PrivacyLevel = PrivacyLevel.INTERNAL
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.01

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "source": self.source,
            "importance": round(self.importance, 3),
            "relevance": round(self.relevance, 3),
            "confidence": round(self.confidence, 3),
            "privacy": self.privacy.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "effective_score": round(self.effective_score(), 3),
        }

    def effective_score(self) -> float:
        age_hours = (time.time() - self.created_at) / 3600
        decay = math.exp(-self.decay_rate * age_hours)
        return self.importance * self.confidence * decay


@dataclass
class FailurePattern:
    operation: str
    error_type: str
    error_message: str
    recovery_strategy: str
    occurrence_count: int = 1
    last_occurred: float = field(default_factory=time.time)
    success_after_recovery: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "recovery_strategy": self.recovery_strategy,
            "occurrence_count": self.occurrence_count,
            "last_occurred": self.last_occurred,
            "success_after_recovery": self.success_after_recovery,
        }


@dataclass
class SuccessPattern:
    operation: str
    strategy: str
    execution_time_ms: float = 0.0
    success_count: int = 1
    avg_confidence: float = 0.9
    last_used: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "strategy": self.strategy,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "success_count": self.success_count,
            "avg_confidence": round(self.avg_confidence, 3),
            "last_used": self.last_used,
        }


class AdaptiveMemory:
    def __init__(self):
        self._short_term: list[MemoryEntry] = []
        self._long_term: dict[str, MemoryEntry] = {}
        self._failure_patterns: dict[str, FailurePattern] = {}
        self._success_patterns: dict[str, SuccessPattern] = {}
        self._agent_performance: dict[str, dict[str, Any]] = {}
        self._tool_usage: dict[str, dict[str, Any]] = {}
        self._max_short_term = 50
        self._max_long_term = 500
        logger.info("[MEMORY] AdaptiveMemory initialized")

    def store_short_term(self, content: str, source: str = "", tags: list[str] | None = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.CONVERSATION,
            content=content,
            source=source,
            importance=0.6,
            relevance=0.7,
            tags=tags or [],
        )
        self._short_term.append(entry)
        if len(self._short_term) > self._max_short_term:
            oldest = self._short_term.pop(0)
            if oldest.importance > 0.7:
                self._promote_to_long_term(oldest)
        return entry

    def store_long_term(self, entry: MemoryEntry):
        key = f"{entry.memory_type.value}:{entry.content[:50]}"
        self._long_term[key] = entry
        if len(self._long_term) > self._max_long_term:
            self._prune_long_term()

    def _promote_to_long_term(self, entry: MemoryEntry):
        key = f"{entry.memory_type.value}:{entry.content[:50]}"
        if key not in self._long_term:
            self._long_term[key] = entry

    def _prune_long_term(self):
        sorted_entries = sorted(self._long_term.items(), key=lambda x: x[1].effective_score())
        to_remove = len(sorted_entries) - self._max_long_term
        for i in range(max(0, to_remove)):
            del self._long_term[sorted_entries[i][0]]

    def retrieve(self, query: str, memory_type: MemoryType | None = None, limit: int = 10) -> list[MemoryEntry]:
        query_lower = query.lower()
        candidates = []

        for entry in self._short_term:
            score = self._relevance_score(entry, query_lower)
            if score > 0.1:
                entry.access_count += 1
                entry.last_accessed = time.time()
                candidates.append((score, entry))

        for entry in self._long_term.values():
            if memory_type and entry.memory_type != memory_type:
                continue
            score = self._relevance_score(entry, query_lower)
            if score > 0.1:
                entry.access_count += 1
                entry.last_accessed = time.time()
                candidates.append((score, entry))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in candidates[:limit]]

    def _relevance_score(self, entry: MemoryEntry, query: str) -> float:
        content_lower = entry.content.lower()
        tag_matches = sum(1 for tag in entry.tags if tag.lower() in query)
        content_words = set(content_lower.split())
        query_words = set(query.split())
        overlap = len(content_words & query_words)
        text_score = overlap / max(len(query_words), 1)
        tag_score = tag_matches * 0.2
        return (entry.importance * 0.3 + entry.confidence * 0.2 + text_score * 0.3 + tag_score * 0.2)

    def record_failure(self, operation: str, error_type: str, error_message: str, recovery_strategy: str = ""):
        key = f"{operation}:{error_type}"
        if key in self._failure_patterns:
            pattern = self._failure_patterns[key]
            pattern.occurrence_count += 1
            pattern.last_occurred = time.time()
        else:
            self._failure_patterns[key] = FailurePattern(
                operation=operation,
                error_type=error_type,
                error_message=error_message,
                recovery_strategy=recovery_strategy,
            )
        logger.info(f"[MEMORY] Failure recorded: {operation} — {error_type}")

    def record_success(self, operation: str, strategy: str, execution_time_ms: float = 0.0, confidence: float = 0.9):
        key = f"{operation}:{strategy}"
        if key in self._success_patterns:
            pattern = self._success_patterns[key]
            pattern.success_count += 1
            pattern.avg_confidence = (pattern.avg_confidence * (pattern.success_count - 1) + confidence) / pattern.success_count
            pattern.last_used = time.time()
            if execution_time_ms > 0:
                pattern.execution_time_ms = execution_time_ms
        else:
            self._success_patterns[key] = SuccessPattern(
                operation=operation,
                strategy=strategy,
                execution_time_ms=execution_time_ms,
                avg_confidence=confidence,
            )

    def get_recovery_suggestion(self, operation: str, error_type: str) -> str | None:
        key = f"{operation}:{error_type}"
        pattern = self._failure_patterns.get(key)
        if pattern and pattern.recovery_strategy:
            return pattern.recovery_strategy
        for k, p in self._failure_patterns.items():
            if operation in k and p.recovery_strategy:
                return p.recovery_strategy
        return None

    def get_best_strategy(self, operation: str) -> str | None:
        candidates = [(k, p) for k, p in self._success_patterns.items() if operation in k]
        if not candidates:
            return None
        best = max(candidates, key=lambda x: x[1].avg_confidence * x[1].success_count)
        return best[1].strategy

    def record_agent_performance(self, agent_id: str, success: bool, execution_time_ms: float = 0.0):
        if agent_id not in self._agent_performance:
            self._agent_performance[agent_id] = {
                "total_executions": 0,
                "successes": 0,
                "failures": 0,
                "total_time_ms": 0.0,
            }
        perf = self._agent_performance[agent_id]
        perf["total_executions"] += 1
        if success:
            perf["successes"] += 1
        else:
            perf["failures"] += 1
        perf["total_time_ms"] += execution_time_ms

    def record_tool_usage(self, tool_name: str, success: bool, execution_time_ms: float = 0.0):
        if tool_name not in self._tool_usage:
            self._tool_usage[tool_name] = {
                "total_calls": 0,
                "successes": 0,
                "failures": 0,
                "total_time_ms": 0.0,
            }
        usage = self._tool_usage[tool_name]
        usage["total_calls"] += 1
        if success:
            usage["successes"] += 1
        else:
            usage["failures"] += 1
        usage["total_time_ms"] += execution_time_ms

    def get_stats(self) -> dict[str, Any]:
        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "failure_patterns": len(self._failure_patterns),
            "success_patterns": len(self._success_patterns),
            "agent_performance_entries": len(self._agent_performance),
            "tool_usage_entries": len(self._tool_usage),
            "top_failure_patterns": [p.to_dict() for p in list(self._failure_patterns.values())[:5]],
            "top_success_patterns": [p.to_dict() for p in list(self._success_patterns.values())[:5]],
        }


_adaptive_memory: AdaptiveMemory | None = None


def get_adaptive_memory() -> AdaptiveMemory:
    global _adaptive_memory
    if _adaptive_memory is None:
        _adaptive_memory = AdaptiveMemory()
    return _adaptive_memory
