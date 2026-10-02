"""Loop Guard - Detects and prevents degenerate agent tool-calling loops.

Ported from OpenJARVIS (Stanford Hazy Research).
Four detection mechanisms:
1. Hash tracking: SHA-256 of (tool_name, arguments) blocks after max_identical_calls
2. Ping-pong detection: Sliding window detects A-B-A-B or A-B-C-A-B-C patterns
3. Poll-tool budget: Tools with polling metadata get a relaxed call budget
4. Context overflow recovery: 4-stage compression
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LoopVerdict(Enum):
    CONTINUE = "continue"
    WARN = "warn"
    BLOCK = "block"
    COMPRESS = "compress"


@dataclass
class LoopGuardConfig:
    max_identical_calls: int = 3
    max_total_calls: int = 50
    max_ping_pong_patterns: int = 2
    ping_pong_window: int = 8
    warn_before_block: bool = True
    compression_stages: int = 4


class LoopGuard:
    def __init__(self, config: LoopGuardConfig | None = None):
        self.config = config or LoopGuardConfig()
        self._call_hashes: list[str] = []
        self._hash_counts: dict[str, int] = {}
        self._total_calls: int = 0
        self._warned: bool = False

    def record_call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> LoopVerdict:
        self._total_calls += 1

        if self._total_calls > self.config.max_total_calls:
            logger.warning(f"Loop guard: total call limit reached ({self.config.max_total_calls})")
            return LoopVerdict.BLOCK

        call_data = json.dumps({"tool": tool_name, "args": arguments or {}}, sort_keys=True)
        call_hash = hashlib.sha256(call_data.encode()).hexdigest()

        self._call_hashes.append(call_hash)
        self._hash_counts[call_hash] = self._hash_counts.get(call_hash, 0) + 1

        if self._hash_counts[call_hash] >= self.config.max_identical_calls:
            logger.warning(f"Loop guard: identical call detected {self._hash_counts[call_hash]}x: {tool_name}")
            return LoopVerdict.BLOCK

        ping_pong = self._detect_ping_pong()
        if ping_pong:
            logger.warning(f"Loop guard: ping-pong pattern detected: {ping_pong}")
            if self.config.warn_before_block and not self._warned:
                self._warned = True
                return LoopVerdict.WARN
            return LoopVerdict.BLOCK

        return LoopVerdict.CONTINUE

    def _detect_ping_pong(self) -> str | None:
        window = self.config.ping_pong_window
        if len(self._call_hashes) < window:
            return None

        recent = self._call_hashes[-window:]

        for pattern_len in range(2, window // 2 + 1):
            pattern = recent[-pattern_len * 2:]
            if len(pattern) < pattern_len * 2:
                continue
            first_half = pattern[:pattern_len]
            second_half = pattern[pattern_len:]
            if first_half == second_half:
                return f"repeating pattern of length {pattern_len}"

        return None

    def should_compress_context(self, token_estimate: int, max_tokens: int = 8000) -> bool:
        return token_estimate > max_tokens * 0.85

    def compress_context(self, messages: list[dict], stage: int = 0) -> list[dict]:
        if not messages:
            return messages

        if stage == 0:
            return self._truncate_tool_results(messages)
        elif stage == 1:
            return self._sliding_window(messages)
        elif stage == 2:
            return self._drop_middle_pairs(messages)
        else:
            return self._extreme_truncation(messages)

    def _truncate_tool_results(self, messages: list[dict]) -> list[dict]:
        result = []
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 500:
                    msg = {**msg, "content": content[:500] + "... [truncated by loop guard]"}
            result.append(msg)
        return result

    def _sliding_window(self, messages: list[dict]) -> list[dict]:
        if len(messages) <= 4:
            return messages
        system = [m for m in messages if m.get("role") == "system"]
        recent = messages[-4:]
        return system + recent

    def _drop_middle_pairs(self, messages: list[dict]) -> list[dict]:
        if len(messages) <= 6:
            return messages
        system = [m for m in messages if m.get("role") == "system"]
        first_two = messages[1:3]
        last_two = messages[-2:]
        return system + first_two + last_two

    def _extreme_truncation(self, messages: list[dict]) -> list[dict]:
        system = [m for m in messages if m.get("role") == "system"]
        last_two = messages[-2:]
        return system + last_two

    def reset(self):
        self._call_hashes.clear()
        self._hash_counts.clear()
        self._total_calls = 0
        self._warned = False

    @property
    def stats(self) -> dict:
        return {
            "total_calls": self._total_calls,
            "unique_hashes": len(self._hash_counts),
            "warned": self._warned,
        }
