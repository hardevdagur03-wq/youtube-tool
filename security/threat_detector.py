from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from security.security_models import (
    AlertSeverity, SecurityEvent, ThreatDetectedError, ThreatType,
)


class ThreatDetector:
    def __init__(self):
        self._failed_logins: dict[str, list[float]] = defaultdict(list)
        self._failed_attempts_threshold = 5
        self._failed_attempts_window = 300

    def check_brute_force(self, identifier: str, max_attempts: int | None = None) -> None:
        now = time.time()
        window = self._failed_attempts_window
        max_a = max_attempts or self._failed_attempts_threshold
        attempts = self._failed_logins[identifier]
        cutoff = now - window
        attempts[:] = [t for t in attempts if t > cutoff]
        if len(attempts) >= max_a:
            raise ThreatDetectedError(
                f"Brute force detected for {identifier}",
                threat_type=ThreatType.BRUTE_FORCE,
                severity=AlertSeverity.HIGH,
            )

    def record_failed_attempt(self, identifier: str) -> None:
        self._failed_logins[identifier].append(time.time())

    def reset_attempts(self, identifier: str) -> None:
        self._failed_logins[identifier].clear()

    def check_suspicious_ip(self, ip_address: str, known_ips: set[str] | None = None) -> bool:
        if known_ips and ip_address not in known_ips:
            return True
        return False

    def get_threat_summary(self) -> dict[str, Any]:
        total_failed = sum(len(v) for v in self._failed_logins.values())
        return {
            "failed_logins_total": total_failed,
            "unique_identifiers_under_attack": len(self._failed_logins),
            "active_threats": [],
        }
