"""Tests for the new Domain Layer architecture."""

from __future__ import annotations

from domain.common.base import AggregateRoot, DomainService, Entity, Guard, Specification, ValueObject
from domain.entities import Analysis, Blog, Project, SEO, Transcript, Video
from domain.events import (
    BlogGenerated,
    PipelineCompleted,
    PipelineStarted,
    ProjectCreated,
    TranscriptGenerated,
)
from domain.value_objects import (
    ContentCategory,
    ContentType,
    DifficultyLevel,
    PipelineStage,
    PipelineStatus,
    SearchIntent,
    TranscriptSegment,
    TranscriptSource,
    VideoId,
)


class TestVideoId:
    def test_valid_video_id(self):
        vid = VideoId("dQw4w9WgXcQ")
        assert str(vid) == "dQw4w9WgXcQ"

    def test_invalid_video_id(self):
        with pytest.raises(ValueError):
            VideoId("short")

    def test_invalid_characters(self):
        with pytest.raises(ValueError):
            VideoId("dQw4w9WgXcQ!!!")


class TestValueObject:
    def test_equality_by_attributes(self):
        from dataclasses import dataclass
        @dataclass(unsafe_hash=True)
        class Point(ValueObject):
            x: int = 0
            y: int = 0

        p1 = Point(x=1, y=2)
        p2 = Point(x=1, y=2)
        p3 = Point(x=3, y=4)

        assert p1 == p2
        assert p1 != p3
        assert hash(p1) == hash(p2)

    def test_immutability(self):
        seg = TranscriptSegment(start=0.0, end=10.0, text="hello")
        assert seg.start == 0.0
        assert seg.end == 10.0
        assert seg.text == "hello"

    def test_invalid_segment_raises(self):
        with pytest.raises(ValueError, match="Start time cannot be negative"):
            TranscriptSegment(start=-1.0, end=10.0, text="bad")

        with pytest.raises(ValueError, match="End time must be after"):
            TranscriptSegment(start=5.0, end=3.0, text="bad")


class TestEntity:
    def test_unique_ids(self):
        class TestEntity(Entity):
            pass

        e1 = TestEntity()
        e2 = TestEntity()
        assert e1.id != e2.id

    def test_equality_by_id(self):
        e1 = Entity(id="same-id")
        e2 = Entity(id="same-id")
        assert e1 == e2

    def test_custom_id(self):
        e = Entity(id="custom-id")
        assert e.id == "custom-id"


class TestAggregateRoot:
    def test_domain_events(self):
        class TestAggregate(AggregateRoot):
            pass

        agg = TestAggregate()
        assert agg._domain_events == []

        from domain.events import PipelineStarted
        event = PipelineStarted(video_id="test")
        agg.record_event(event)
        assert len(agg._domain_events) == 1

        events = agg.clear_events()
        assert len(events) == 1
        assert agg._domain_events == []

    def test_no_events_initially(self):
        class TestAggregate2(AggregateRoot):
            pass
        agg = TestAggregate2()
        assert agg.clear_events() == []


class TestVideoEntity:
    def test_create_video(self):
        video_id = VideoId("dQw4w9WgXcQ")
        video = Video(video_id=video_id, title="Test Video")
        assert video.video_id == video_id
        assert video.title == "Test Video"
        assert video.id is not None

    def test_video_with_metadata(self):
        video_id = VideoId("dQw4w9WgXcQ")
        video = Video(
            video_id=video_id,
            title="Test",
            channel_name="Test Channel",
            view_count=1000,
            duration_seconds=120,
        )
        assert video.channel_name == "Test Channel"
        assert video.view_count == 1000
        assert video.duration_seconds == 120


class TestTranscriptEntity:
    def test_create_transcript(self):
        video_id = VideoId("dQw4w9WgXcQ")
        seg = TranscriptSegment(start=0.0, end=5.0, text="hello")
        transcript = Transcript(
            video_id=video_id,
            source=TranscriptSource.MANUAL,
            language="en",
            segments=[seg],
            word_count=1,
        )
        assert transcript.video_id == video_id
        assert transcript.word_count == 1
        assert transcript.segments[0].text == "hello"


class TestAnalysisEntity:
    def test_create_analysis(self):
        video_id = VideoId("dQw4w9WgXcQ")
        analysis = Analysis(
            video_id=video_id,
            primary_topic="Machine Learning",
            category=ContentCategory.TECHNOLOGY,
            content_type=ContentType.TUTORIAL,
            search_intent=SearchIntent.INFORMATIONAL,
            llm_provider="gemini",
            total_tokens=500,
        )
        assert analysis.primary_topic == "Machine Learning"
        assert analysis.category == ContentCategory.TECHNOLOGY


class TestBlogEntity:
    def test_create_blog(self):
        video_id = VideoId("dQw4w9WgXcQ")
        blog = Blog(
            video_id=video_id,
            seo_title="Test Blog Post",
            markdown="# Hello World",
        )
        assert blog.seo_title == "Test Blog Post"
        assert blog.markdown == "# Hello World"


class TestProjectEntity:
    def test_create_project(self):
        video_id = VideoId("dQw4w9WgXcQ")
        project = Project(video_id=video_id, title="Test Project")
        assert project.status == PipelineStatus.PENDING
        assert project.current_stage == PipelineStage.METADATA

    def test_complete_stage(self):
        video_id = VideoId("dQw4w9WgXcQ")
        project = Project(video_id=video_id)
        project.complete_stage(PipelineStage.METADATA)
        assert PipelineStage.METADATA in project.completed_stages

    def test_fail_stage(self):
        video_id = VideoId("dQw4w9WgXcQ")
        project = Project(video_id=video_id)
        project.fail_stage(PipelineStage.TRANSCRIPT, "Failed to fetch")
        assert PipelineStage.TRANSCRIPT in project.failed_stages
        assert project.status == PipelineStatus.FAILED
        assert project.error_message == "Failed to fetch"


class TestDomainEvents:
    def test_project_created_event(self):
        event = ProjectCreated(
            project_id="proj-1",
            video_id="dQw4w9WgXcQ",
            url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        )
        assert event.project_id == "proj-1"
        assert event.video_id == "dQw4w9WgXcQ"
        assert event.event_type == "ProjectCreated"

    def test_transcript_generated_event(self):
        event = TranscriptGenerated(
            video_id="dQw4w9WgXcQ",
            source="manual",
            language="en",
            word_count=1500,
        )
        assert event.word_count == 1500

    def test_blog_generated_event(self):
        event = BlogGenerated(
            video_id="dQw4w9WgXcQ",
            word_count=2000,
            llm_provider="gemini",
            total_tokens=5000,
        )
        assert event.total_tokens == 5000

    def test_pipeline_started_event(self):
        event = PipelineStarted(
            project_id="proj-1",
            video_id="dQw4w9WgXcQ",
        )
        assert event.event_type == "PipelineStarted"

    def test_pipeline_completed_event(self):
        event = PipelineCompleted(
            project_id="proj-1",
            video_id="dQw4w9WgXcQ",
            total_stages=5,
            duration_seconds=120.0,
        )
        assert event.total_stages == 5
        assert event.duration_seconds == 120.0


class TestGuard:
    def test_against_empty_passes(self):
        Guard.against_empty("hello", "value")

    def test_against_empty_raises(self):
        with pytest.raises(Exception, match="cannot be empty"):
            Guard.against_empty("", "value")

    def test_against_null_passes(self):
        Guard.against_null("not None", "value")

    def test_against_null_raises(self):
        with pytest.raises(Exception, match="cannot be null"):
            Guard.against_null(None, "value")


import pytest
