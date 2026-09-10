from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_llm():
    with patch("services.content_analysis_service.ContentAnalysisService.analyze") as mock:
        mock.return_value = {
            "primary_topic": "Python Programming",
            "search_intent": "educational",
            "summary": {"short": "A guide to Python", "key_insights": ["Python is versatile"]},
        }
        yield mock


@pytest.fixture
def mock_youtube():
    with patch("services.youtube_metadata_service.YouTubeMetadataService") as mock:
        instance = mock.return_value
        instance.get_video_metadata.return_value = {
            "id": "test123",
            "snippet": {"title": "Test Video", "channelTitle": "Test Channel"},
            "statistics": {"viewCount": "1000", "likeCount": "100"},
        }
        yield instance


@pytest.fixture
def mock_redis():
    with patch("redis.Redis") as mock:
        instance = mock.return_value
        instance.get.return_value = None
        instance.set.return_value = True
        instance.publish.return_value = 1
        instance.ping.return_value = True
        yield instance


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


@pytest.fixture
def mock_file_system(tmp_path):
    base = tmp_path / "projects"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def sample_project():
    return {
        "project_id": "proj_test_001",
        "video_id": "vid_test_001",
        "status": "created",
        "name": "Test Project",
        "url": "https://youtube.com/watch?v=vid_test_001",
    }


@pytest.fixture
def sample_video():
    return {
        "id": "vid_test_001",
        "title": "Test Video Title",
        "channel": "Test Channel",
        "duration_seconds": 600,
        "view_count": 10000,
        "like_count": 500,
    }


@pytest.fixture
def sample_transcript():
    return {
        "video_id": "vid_test_001",
        "language": "en",
        "plain_text": "This is a sample transcript for testing. Python is a versatile language. "
                       "It was created by Guido van Rossum. According to recent data, Python usage has grown by 50 percent. "
                       "The most important thing is to practice regularly. Data cleaning is challenging. "
                       "As the speaker noted, Python simplicity is its greatest strength. "
                       "The language has been adopted by millions of developers worldwide.",
        "segments": [
            {"text": "This is a sample transcript for testing.", "start": 0.0, "duration": 5.0},
            {"text": "Python is a versatile language.", "start": 5.0, "duration": 4.0},
            {"text": "It was created by Guido van Rossum.", "start": 9.0, "duration": 3.0},
        ],
    }


@pytest.fixture
def sample_analysis():
    return {
        "primary_topic": "Python Programming for Data Science",
        "secondary_topics": ["Machine Learning", "Data Visualization", "Statistics"],
        "search_intent": "educational",
        "content_category": "programming",
        "summary": {
            "short": "A comprehensive guide to Python for data science",
            "key_insights": [
                "Python is the most popular language for data science",
                "Pandas and NumPy are essential libraries",
            ],
        },
        "key_takeaways": ["Start with Python basics", "Practice with real datasets"],
        "pain_points": ["Steep learning curve", "Data cleaning is time-consuming"],
        "solutions": ["Use Jupyter notebooks for interactive development"],
        "entities": {
            "people": ["Guido van Rossum"],
            "technologies": ["Python", "Pandas", "NumPy", "Scikit-learn", "TensorFlow"],
            "frameworks": ["Django", "Flask"],
            "tools": ["Jupyter", "VS Code"],
        },
        "keywords": {
            "primary": ["Python programming", "data science"],
            "secondary": ["machine learning", "data analysis"],
            "long_tail": ["Python for beginners", "data science tutorial"],
            "semantic": ["programming", "analytics"],
        },
    }


@pytest.fixture
def sample_knowledge_graph():
    return {
        "entities": [
            {"name": "Python", "type": "technology", "importance_score": 1.0},
            {"name": "Pandas", "type": "library", "importance_score": 0.9},
        ],
        "keywords": [
            {"keyword": "python", "type": "primary", "relevance_score": 1.0},
            {"keyword": "data science", "type": "primary", "relevance_score": 0.9},
        ],
        "facts": [
            {"statement": "Python is a high-level programming language.", "category": "definition"},
            {"statement": "Python usage has grown by 50%.", "category": "statistic"},
        ],
        "definitions": [{"term": "API", "definition": "Application Programming Interface"}],
        "pain_points": [{"problem": "Steep learning curve", "severity": "high"}],
    }


@pytest.fixture
def sample_seo_plan():
    return {
        "keyword_strategy": {
            "primary_keyword": "Python Programming for Data Science",
            "secondary_keywords": [
                {"keyword": "data analysis", "type": "secondary"},
                {"keyword": "machine learning", "type": "secondary"},
            ],
        },
        "search_intent": {"primary_intent": "educational"},
        "target_audience": {"primary_audience": "Data Scientists"},
        "content_strategy": {"recommended_word_count": 2500},
    }


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.emit = AsyncMock()
    bus.publish = MagicMock()
    bus.subscribe = MagicMock()
    return bus


@pytest.fixture
def mock_storage_manager(tmp_path):
    from projects.storage_manager import StorageManager
    return StorageManager(root=tmp_path)


@pytest.fixture
def mock_engine_config():
    return {
        "max_retries": 3,
        "temperature": 0.7,
        "enable_cache": True,
        "enable_validation": True,
    }


@pytest.fixture
def sample_draft():
    return {
        "title": "Complete Guide to Python",
        "content": "# Complete Guide to Python\n\n## Introduction\n\nPython is versatile.\n\n## Body\n\nPython is used widely.\n\n## Conclusion\n\nPython is the future.\n",
        "word_count": 20,
        "section_count": 3,
    }


@pytest.fixture
def sample_metadata():
    return {
        "title": "Test Video",
        "description": "A test video for unit testing",
        "channel_title": "Test Channel",
        "channel_id": "UCtest123",
        "published_at": "2024-01-01T00:00:00Z",
        "view_count": 10000,
        "like_count": 500,
        "comment_count": 100,
        "duration_seconds": 600,
        "tags": ["python", "tutorial", "testing"],
        "category_id": "27",
        "default_language": "en",
    }
