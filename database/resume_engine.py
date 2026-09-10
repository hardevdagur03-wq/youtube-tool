from __future__ import annotations

import logging
from typing import Any

from database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

STAGE_ORDER = [
    "metadata",
    "transcript",
    "analysis",
    "knowledge_graph",
    "seo",
    "seo_intelligence",
    "outline",
    "outline_generator",
    "sections",
    "merge",
    "review",
    "optimization",
    "export",
]


class ResumeEngine:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_resume_state(self, project_uuid: str) -> dict[str, Any]:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return {"can_resume": False, "reason": "Project not found"}

        pipeline = await self.uow.history.get_by_field(
            "project_uuid", project_uuid
        )

        return {
            "project_uuid": project_uuid,
            "status": project.status,
            "current_stage": project.pipeline_state.get("current_stage", ""),
            "completed_stages": project.pipeline_state.get("completed_stages", []),
            "pending_stages": project.pipeline_state.get("pending_stages", []),
            "failed_stages": project.pipeline_state.get("failed_stages", []),
            "progress": project.progress,
            "version": project.version,
            "can_resume": project.status in ("FAILED", "PAUSED", "CANCELLED"),
        }

    async def compute_resume_plan(
        self, project_uuid: str
    ) -> dict[str, Any]:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return {"can_resume": False, "reason": "Project not found"}

        state = project.pipeline_state or {}
        completed = set(state.get("completed_stages", []))
        failed = set(s.get("stage") for s in state.get("failed_stages", []))
        current = state.get("current_stage", "")

        pending = []
        for stage in STAGE_ORDER:
            if stage not in completed and stage != current:
                pending.append(stage)

        resume_from = current if current in failed else self._find_resume_point(completed)

        stage_data: dict[str, bool] = {}
        for stage in STAGE_ORDER:
            stage_data[stage] = stage in completed

        return {
            "project_uuid": project_uuid,
            "can_resume": True,
            "resume_from": resume_from,
            "completed_stages": list(completed),
            "pending_stages": pending,
            "failed_stages": list(failed),
            "current_stage": current,
            "stage_data": stage_data,
            "progress": project.progress,
        }

    async def mark_stage_completed(
        self,
        project_uuid: str,
        stage: str,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            raise ValueError(f"Project {project_uuid[:8]} not found")

        state = dict(project.pipeline_state or {})
        completed = list(state.get("completed_stages", []))
        if stage not in completed:
            completed.append(stage)
        state["completed_stages"] = completed
        state["current_stage"] = self._next_stage(stage)
        state["last_completed"] = stage

        await self.uow.projects.update_pipeline_state(project_uuid, state)

        if output_data:
            await self.uow.projects.update_stage_data(
                project_uuid, stage, output_data
            )

        progress = len(completed) / len(STAGE_ORDER) * 100
        await self.uow.projects.update(project_uuid, progress=progress)

        await self.uow.history.log_event(
            action=f"pipeline.stage_completed",
            entity_type="pipeline",
            entity_uuid=project_uuid,
            project_uuid=project_uuid,
            actor_id="system",
            changes={"stage": stage, "progress": progress},
        )

    async def mark_stage_failed(
        self,
        project_uuid: str,
        stage: str,
        error: str,
    ) -> None:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            raise ValueError(f"Project {project_uuid[:8]} not found")

        state = dict(project.pipeline_state or {})
        failed = list(state.get("failed_stages", []))
        failed.append({"stage": stage, "error": error, "timestamp": str(__import__("datetime").datetime.now())})
        state["failed_stages"] = failed
        state["last_error"] = error

        await self.uow.projects.update_pipeline_state(project_uuid, state)
        await self.uow.projects.update(project_uuid, status="FAILED", error=error)

        await self.uow.history.log_event(
            action=f"pipeline.stage_failed",
            entity_type="pipeline",
            entity_uuid=project_uuid,
            project_uuid=project_uuid,
            actor_id="system",
            changes={"stage": stage, "error": error},
        )

    async def get_pipeline_checkpoint(
        self, project_uuid: str
    ) -> dict[str, Any] | None:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return None
        state = project.pipeline_state or {}
        return state.get("checkpoint")

    async def save_pipeline_checkpoint(
        self,
        project_uuid: str,
        stage: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            raise ValueError(f"Project {project_uuid[:8]} not found")

        state = dict(project.pipeline_state or {})
        state["checkpoint"] = {
            "stage": stage,
            "data": checkpoint_data,
            "timestamp": str(__import__("datetime").datetime.now()),
        }
        await self.uow.projects.update_pipeline_state(project_uuid, state)

    async def get_stage_data(
        self, project_uuid: str, stage: str
    ) -> dict[str, Any] | None:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return None
        stage_data = project.stage_data or {}
        return stage_data.get(stage)

    async def get_all_stage_data(
        self, project_uuid: str
    ) -> dict[str, Any]:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return {}
        return project.stage_data or {}

    async def is_stage_completed(
        self, project_uuid: str, stage: str
    ) -> bool:
        project = await self.uow.projects.get_by_uuid(project_uuid)
        if project is None:
            return False
        state = project.pipeline_state or {}
        return stage in state.get("completed_stages", [])

    def _find_resume_point(self, completed: set[str]) -> str:
        for stage in STAGE_ORDER:
            if stage not in completed:
                return stage
        return STAGE_ORDER[-1]

    def _next_stage(self, current: str) -> str:
        try:
            idx = STAGE_ORDER.index(current)
            if idx + 1 < len(STAGE_ORDER):
                return STAGE_ORDER[idx + 1]
        except ValueError:
            pass
        return "completed"
