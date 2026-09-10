from __future__ import annotations

import os
import sys
import tempfile
import tracemalloc
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.config import DatabaseConfig
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork


pytestmark = pytest.mark.performance


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
async def uow(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    session = mgr.session_factory()
    uow_obj = UnitOfWork(session=session)
    await uow_obj.__aenter__()
    try:
        yield uow_obj
    except Exception:
        await uow_obj.__aexit__(*sys.exc_info())
        raise
    else:
        await uow_obj.__aexit__(None, None, None)
    finally:
        await session.close()
    await mgr.close()


class TestMemoryUsage:
    @pytest.mark.asyncio
    async def test_pipeline_memory_footprint(self, uow):
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        for i in range(50):
            await uow.projects.create(
                name=f"Mem Project {i}",
                short_id=f"MP{i:04d}",
                video_id=f"mvid{i}",
            )
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_diff = sum(stat.size_diff for stat in stats)
        assert total_diff < 5_000_000, (
            f"Memory increase {total_diff} bytes exceeds 5MB limit"
        )

    def test_export_memory_usage(self):
        from models.blog_export import ExportRequest, ExportFormat
        from export.markdown_exporter import MarkdownExporter

        blog = ExportRequest(
            blog_title="Memory Test",
            markdown_content="# Test\n\n" + "x" * 100_000,
            formats=[ExportFormat.MARKDOWN],
            sections=[],
        )
        exporter = MarkdownExporter()
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(blog, Path(tmpdir))
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_diff = sum(stat.size_diff for stat in stats)
        assert total_diff < 10_000_000, (
            f"Export memory increase {total_diff} bytes exceeds 10MB limit"
        )
        assert result.filename is not None

    @pytest.mark.asyncio
    async def test_large_transcript_memory(self, uow):
        large_transcript = "word " * 50_000
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        p = await uow.projects.create(
            name="Large Transcript",
            short_id="LT001",
            video_id="ltvid1",
        )
        await uow.transcripts.create(
            project_uuid=p.uuid,
            content=large_transcript,
            language="en",
        )
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_diff = sum(stat.size_diff for stat in stats)
        assert total_diff < 10_000_000, (
            f"Large transcript memory increase {total_diff} bytes exceeds 10MB limit"
        )
