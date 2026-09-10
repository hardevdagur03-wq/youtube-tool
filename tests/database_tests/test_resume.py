from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.config import DatabaseConfig
from database.resume_engine import ResumeEngine
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork


pytestmark = pytest.mark.db


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def setup(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    session = mgr.session_factory()
    uow_obj = UnitOfWork(session=session)
    await uow_obj.__aenter__()
    yield uow_obj, mgr
    await uow_obj.__aexit__(None, None, None)
    await session.close()
    await mgr.close()


class TestResume:
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, setup):
        uow_obj, mgr = setup
        engine = ResumeEngine(uow_obj)
        p = await uow_obj.projects.create(
            name="Resume Test", short_id="RS001", status="running"
        )
        await uow_obj.commit()
        pipeline_state = await uow_obj.pipeline_states.create(
            project_uuid=p.uuid,
            stage="transcript",
            status="completed",
            checkpoint_data={"transcript": "done"},
        )
        resume_point = await engine.find_resume_point(p.uuid)
        assert resume_point is not None

    @pytest.mark.asyncio
    async def test_resume_with_modified_data(self, setup):
        uow_obj, mgr = setup
        engine = ResumeEngine(uow_obj)
        p = await uow_obj.projects.create(
            name="Modified Resume", short_id="MR001", status="running"
        )
        await uow_obj.commit()
        await uow_obj.pipeline_states.create(
            project_uuid=p.uuid,
            stage="analysis",
            status="completed",
        )
        await uow_obj.projects.update(p.uuid, name="Modified Name")
        resume_point = await engine.find_resume_point(p.uuid)
        assert resume_point is not None

    @pytest.mark.asyncio
    async def test_resume_non_existent(self, setup):
        uow_obj, mgr = setup
        engine = ResumeEngine(uow_obj)
        resume_point = await engine.find_resume_point("non_existent_uuid")
        assert resume_point is None
