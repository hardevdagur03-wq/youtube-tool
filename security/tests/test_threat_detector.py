from __future__ import annotations

import pytest

from security.security_models import ThreatDetectedError
from security.threat_detector import ThreatDetector


class TestThreatDetector:
    def setup_method(self):
        self.detector = ThreatDetector()

    def test_brute_force_not_detected_below_threshold(self):
        for _ in range(4):
            self.detector.record_failed_attempt("user@test.com")
        self.detector.check_brute_force("user@test.com")

    def test_brute_force_detected_at_threshold(self):
        for _ in range(5):
            self.detector.record_failed_attempt("user@test.com")
        with pytest.raises(ThreatDetectedError) as exc:
            self.detector.check_brute_force("user@test.com")
        assert "Brute force" in str(exc.value)

    def test_brute_force_uses_custom_max(self):
        for _ in range(3):
            self.detector.record_failed_attempt("user@test.com")
        with pytest.raises(ThreatDetectedError):
            self.detector.check_brute_force("user@test.com", max_attempts=3)

    def test_reset_attempts_clears_counter(self):
        for _ in range(5):
            self.detector.record_failed_attempt("user@test.com")
        self.detector.reset_attempts("user@test.com")
        self.detector.check_brute_force("user@test.com")

    def test_brute_force_isolated_per_user(self):
        for _ in range(5):
            self.detector.record_failed_attempt("attacker@test.com")
        self.detector.record_failed_attempt("legit@test.com")
        self.detector.check_brute_force("legit@test.com")
        with pytest.raises(ThreatDetectedError):
            self.detector.check_brute_force("attacker@test.com")

    def test_check_suspicious_ip_known_safe(self):
        known = {"192.168.1.1", "10.0.0.1"}
        assert self.detector.check_suspicious_ip("192.168.1.1", known) is False

    def test_check_suspicious_ip_unknown(self):
        known = {"192.168.1.1"}
        assert self.detector.check_suspicious_ip("10.0.0.5", known) is True

    def test_check_suspicious_ip_no_known_set(self):
        assert self.detector.check_suspicious_ip("10.0.0.5") is False

    def test_get_threat_summary_empty(self):
        summary = self.detector.get_threat_summary()
        assert summary["failed_logins_total"] == 0
        assert summary["unique_identifiers_under_attack"] == 0

    def test_get_threat_summary_with_data(self):
        self.detector.record_failed_attempt("user1")
        self.detector.record_failed_attempt("user1")
        self.detector.record_failed_attempt("user2")
        summary = self.detector.get_threat_summary()
        assert summary["failed_logins_total"] == 3
        assert summary["unique_identifiers_under_attack"] == 2

    def test_attempts_expire_after_window(self):
        import time
        detector = ThreatDetector()
        detector._failed_attempts_window = 0
        time.sleep(0.01)
        detector.record_failed_attempt("user@test.com")
        detector.check_brute_force("user@test.com", max_attempts=1)
