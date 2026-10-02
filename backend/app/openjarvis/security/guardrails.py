"""Security guardrails engine — wraps inference with scanning."""

import logging
from typing import Optional
from .scanner import SecretScanner, PIIScanner, ScanResult

logger = logging.getLogger(__name__)


class SecurityBlockError(Exception):
    def __init__(self, scan_result: ScanResult, direction: str):
        self.scan_result = scan_result
        self.direction = direction
        alerts = [a["pattern"] for a in scan_result.alerts]
        super().__init__(f"Security block ({direction}): {', '.join(alerts)}")


class GuardrailsEngine:
    """Scans input/output for secrets and PII with WARN/REDACT/BLOCK modes."""

    def __init__(self, mode: str = "WARN"):
        self.mode = mode.upper()
        self.secret_scanner = SecretScanner()
        self.pii_scanner = PIIScanner()
        self._alert_log: list[dict] = []

    def scan_input(self, text: str) -> ScanResult:
        result = ScanResult()
        for match in self.secret_scanner.scan(text).matches:
            result.add(match)
        for match in self.pii_scanner.scan(text).matches:
            result.add(match)

        self._handle_result(result, "input")
        return result

    def scan_output(self, text: str) -> ScanResult:
        result = ScanResult()
        for match in self.secret_scanner.scan(text).matches:
            result.add(match)

        self._handle_result(result, "output")
        return result

    def redact(self, text: str) -> str:
        text = self.secret_scanner.redact(text)
        text = self.pii_scanner.redact(text)
        return text

    def _handle_result(self, result: ScanResult, direction: str):
        if result.clean:
            return

        for alert in result.alerts:
            entry = {"direction": direction, **alert}
            self._alert_log.append(entry)
            logger.warning(f"[GUARDRAILS] {direction}: {alert['pattern']} ({alert['severity']})")

        if self.mode == "BLOCK":
            raise SecurityBlockError(result, direction)

    @property
    def alert_log(self) -> list[dict]:
        return list(self._alert_log)

    def clear_alerts(self):
        self._alert_log.clear()


guardrails = GuardrailsEngine(mode="WARN")
