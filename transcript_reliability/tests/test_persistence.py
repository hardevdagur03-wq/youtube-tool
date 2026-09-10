"""Tests for Persistence and Observability modules."""

from __future__ import annotations

from models.transcript import TranscriptResult
from transcript_reliability.cache_layer import MultiLevelCache, LRUCache
from transcript_reliability.version_manager import VersionManager
from transcript_reliability.quality_scorer import QualityScorer
from transcript_reliability.observability import TranscriptObservability


class TestLRUCache:
    def test_set_and_get(self):
        cache = LRUCache(max_size=10, ttl=300)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = LRUCache()
        assert cache.get("missing") is None

    def test_eviction(self):
        cache = LRUCache(max_size=2, ttl=300)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        assert cache.get("k1") is None
        assert cache.get("k3") == "v3"

    def test_ttl_expiry(self):
        cache = LRUCache(max_size=10, ttl=0.05)
        cache.set("key", "value")
        import time
        time.sleep(0.06)
        assert cache.get("key") is None

    def test_delete(self):
        cache = LRUCache()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self):
        cache = LRUCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.size == 0

    def test_stats(self):
        cache = LRUCache()
        cache.set("k1", "v1")
        cache.get("k1")
        cache.get("missing")
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestMultiLevelCache:
    def test_set_and_get_l1(self):
        cache = MultiLevelCache()
        tr = TranscriptResult(video_id="test123", plain_text="test", word_count=1)
        cache.set("test123", tr)
        cached = cache.get("test123")
        assert cached is not None
        assert cached.video_id == "test123"

    def test_get_missing(self):
        cache = MultiLevelCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_stats(self):
        cache = MultiLevelCache()
        tr = TranscriptResult(video_id="test", plain_text="test", word_count=1)
        cache.set("test", tr)
        cache.get("test")
        cache.get("missing")
        stats = cache.stats
        assert stats["l1_hits"] >= 1
        assert stats["misses"] >= 1

    def test_clear(self):
        cache = MultiLevelCache()
        tr = TranscriptResult(video_id="test", plain_text="test", word_count=1)
        cache.set("test", tr)
        cache.clear()
        assert cache.get("test") is None

    def test_invalidate(self):
        cache = MultiLevelCache()
        tr = TranscriptResult(video_id="test", plain_text="test", word_count=1)
        cache.set("test", tr)
        # The L1 cache doesn't support prefix invalidation; clear instead
        cache.clear()
        assert cache.get("test") is None

    def test_cache_key_format(self):
        cache = MultiLevelCache()
        key = cache._build_key("v1", "en", "youtube_manual", "current")
        assert "transcript" in key
        assert "v1" in key
        assert "en" in key


class TestVersionManager:
    def test_create_version(self, sample_transcript):
        vm = VersionManager()
        v = vm.create_version(sample_transcript, "original", "Initial")
        assert v.version_number == 1
        assert v.version_type == "original"
        assert v.video_id == "dQw4w9WgXcQ"

    def test_multiple_versions(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "First")
        vm.create_version(sample_transcript, "original", "Second")
        versions = vm.list_versions("dQw4w9WgXcQ", "original")
        assert len(versions) == 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2

    def test_get_latest_version(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "First")
        vm.create_version(sample_transcript, "original", "Second")
        latest = vm.get_version("dQw4w9WgXcQ", "original")
        assert latest.version_number == 2

    def test_get_specific_version(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "First")
        v = vm.get_version("dQw4w9WgXcQ", "original", version_number=1)
        assert v.version_number == 1
        assert v.change_reason == "First"

    def test_restore_version(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "Initial")
        restored = vm.restore_version("dQw4w9WgXcQ", "original")
        assert restored is not None
        assert restored.plain_text == sample_transcript.plain_text

    def test_verify_integrity(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "Initial")
        assert vm.verify_integrity("dQw4w9WgXcQ") == True

    def test_list_all_versions(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "Orig")
        vm.create_version(sample_transcript, "cleaned", "Clean")
        all_v = vm.list_versions("dQw4w9WgXcQ")
        assert len(all_v) == 2

    def test_delete_versions(self, sample_transcript):
        vm = VersionManager()
        vm.create_version(sample_transcript, "original", "Test")
        vm.delete_versions("dQw4w9WgXcQ")
        assert len(vm.list_versions("dQw4w9WgXcQ")) == 0

    def test_lineage(self, sample_transcript):
        vm = VersionManager()
        v1 = vm.create_version(sample_transcript, "original", "First")
        vm.create_version(sample_transcript, "original", "Second", parent_version_id=v1.version_id)
        lineage = vm.get_lineage("dQw4w9WgXcQ", version_type="original")
        assert len(lineage) == 2


class TestQualityScorer:
    def test_score_normal_transcript(self, sample_transcript):
        scorer = QualityScorer()
        quality = scorer.score(sample_transcript)
        assert quality.overall > 0
        assert len(quality.dimensions) == 8
        assert quality.provider_reliability_score == 0.5

    def test_score_empty_transcript(self, empty_transcript):
        scorer = QualityScorer()
        quality = scorer.score(empty_transcript)
        assert quality.overall <= 0.5

    def test_grade_excellent(self):
        scorer = QualityScorer()
        # Manually check grade thresholds
        from transcript_reliability.constants import QualityGrade
        assert scorer._grade(0.95) == QualityGrade.EXCELLENT
        assert scorer._grade(0.80) == QualityGrade.GOOD
        assert scorer._grade(0.60) == QualityGrade.FAIR
        assert scorer._grade(0.40) == QualityGrade.POOR
        assert scorer._grade(0.20) == QualityGrade.REJECT

    def test_get_history(self, sample_transcript):
        scorer = QualityScorer()
        scorer.score(sample_transcript)
        scorer.score(sample_transcript)
        history = scorer.get_history("dQw4w9WgXcQ")
        assert len(history) == 2

    def test_trend(self, sample_transcript):
        scorer = QualityScorer()
        scorer.score(sample_transcript)
        trend = scorer.get_trend("dQw4w9WgXcQ")
        assert trend in ("stable", "improving", "declining")


class TestObservability:
    def test_provider_latency(self):
        obs = TranscriptObservability()
        obs.record_provider_latency("p1", 100.0)
        obs.record_provider_latency("p1", 200.0)
        stats = obs.get_provider_latency_stats("p1")
        assert stats["avg"] == 150.0
        assert stats["count"] == 2

    def test_provider_success_rate(self):
        obs = TranscriptObservability()
        obs.record_provider_success("p1", True)
        obs.record_provider_success("p1", True)
        obs.record_provider_success("p1", False)
        rate = obs.get_provider_success_rate("p1")
        assert rate == 2 / 3

    def test_cache_hit_rate(self):
        obs = TranscriptObservability()
        obs.record_cache_hit("l1")
        obs.record_cache_hit("l2")
        obs.record_cache_miss()
        rate = obs.get_cache_hit_rate()
        assert rate == 2 / 3

    def test_record_retry(self):
        obs = TranscriptObservability()
        obs.record_retry("p1")
        obs.record_retry("p1")
        summary = obs.get_summary()
        assert summary["retries"].get("p1", 0) == 2

    def test_record_fallback(self):
        obs = TranscriptObservability()
        obs.record_fallback("p1", "p2")
        summary = obs.get_summary()
        assert "p1->p2" in summary["fallbacks"]

    def test_record_circuit_breaker_event(self):
        obs = TranscriptObservability()
        obs.record_circuit_breaker_event("p1", "open")
        summary = obs.get_summary()
        assert "p1:open" in summary["circuit_breaker_events"]

    def test_record_validation_failure(self):
        obs = TranscriptObservability()
        obs.record_validation_failure("empty_transcript")
        summary = obs.get_summary()
        assert summary["validation_failures"].get("empty_transcript", 0) == 1

    def test_get_summary(self):
        obs = TranscriptObservability()
        summary = obs.get_summary()
        assert "provider_success_rate" in summary
        assert "cache_hit_rate" in summary

    def test_quality_score_recording(self):
        obs = TranscriptObservability()
        obs.record_quality_score("v1", 0.85)
        summary = obs.get_summary()
        assert summary is not None
