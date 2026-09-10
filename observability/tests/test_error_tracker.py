from __future__ import annotations

from observability.error_tracker import ErrorTracker, make_fingerprint


class TestErrorTracker:
    def test_capture_and_group(self):
        tracker = ErrorTracker()
        try:
            raise ValueError("test error")
        except ValueError as e:
            fp = tracker.capture(e, module="test_module")
        assert len(fp) > 0
        grouped = tracker.get_grouped_errors()
        assert len(grouped) == 1
        assert grouped[0]["error_type"] == "ValueError"
        assert grouped[0]["module"] == "test_module"
        assert grouped[0]["count"] == 1

    def test_deduplication(self):
        tracker = ErrorTracker()
        for _ in range(3):
            try:
                raise ValueError("dedup test")
            except ValueError as e:
                tracker.capture(e, module="dedup")
        grouped = tracker.get_grouped_errors()
        assert len(grouped) == 1
        assert grouped[0]["count"] == 3

    def test_mark_resolved(self):
        tracker = ErrorTracker()
        try:
            raise RuntimeError("resolve test")
        except RuntimeError as e:
            fp = tracker.capture(e, module="resolve")
        tracker.mark_resolved(fp)
        grouped = tracker.get_grouped_errors()
        assert grouped[0]["resolved"] is True

    def test_get_recent_errors(self):
        tracker = ErrorTracker()
        try:
            raise ValueError("recent")
        except ValueError as e:
            tracker.capture(e)
        recent = tracker.get_recent_errors()
        assert len(recent) >= 1

    def test_get_error_summary(self):
        tracker = ErrorTracker()
        try:
            raise ValueError("summary")
        except ValueError as e:
            tracker.capture(e, module="sum")
        summary = tracker.get_error_summary()
        assert summary["total_errors"] >= 1
        assert "ValueError" in summary["by_type"]

    def test_clear(self):
        tracker = ErrorTracker()
        try:
            raise ValueError("clear")
        except ValueError as e:
            tracker.capture(e)
        tracker.clear()
        assert len(tracker.get_grouped_errors()) == 0

    def test_make_fingerprint(self):
        try:
            raise ValueError("fp")
        except ValueError as e:
            fp = make_fingerprint(e, "module")
            assert "ValueError" in fp
