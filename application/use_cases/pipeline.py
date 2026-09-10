"""Use cases for pipeline orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from domain.entities import (
    Analysis,
    Blog,
    Export,
    KnowledgeGraph,
    Outline,
    Project,
    SEO,
    Transcript,
    Video,
)
from domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    BlogFailed,
    BlogGenerated,
    ExportCompleted,
    ExportFailed,
    KnowledgeGraphBuilt,
    OutlineGenerated,
    PipelineCompleted,
    PipelineFailed,
    PipelineStageCompleted,
    PipelineStageFailed,
    PipelineStarted,
    ProjectCreated,
    SEOAnalysisCompleted,
    TranscriptFailed,
    TranscriptGenerated,
)
from domain.repositories import UnitOfWork
from domain.services import (
    AnalysisProvider,
    BlogProvider,
    ExportProvider,
    KnowledgeGraphProvider,
    OutlineProvider,
    SEOProvider,
    TranscriptProvider,
)
from domain.value_objects import (
    ExportFormat,
    PipelineStage,
    PipelineStatus,
    VideoId,
)

from .base import Command, Result, UseCase


@dataclass
class RunPipelineCommand(Command):
    video_id: str = ""
    url: str = ""
    project_id: str = ""
    stages: list[str] | None = None


class RunPipelineUseCase(UseCase[RunPipelineCommand, Result]):
    """Orchestrates the full pipeline execution for a video.

    Each stage is isolated: failure in one stage does not destroy others.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        transcript_provider: TranscriptProvider,
        analysis_provider: AnalysisProvider,
        blog_provider: BlogProvider,
        seo_provider: SEOProvider,
        export_provider: ExportProvider,
        knowledge_graph_provider: KnowledgeGraphProvider | None = None,
        outline_provider: OutlineProvider | None = None,
    ):
        self._uow = uow
        self._transcript_provider = transcript_provider
        self._analysis_provider = analysis_provider
        self._blog_provider = blog_provider
        self._seo_provider = seo_provider
        self._export_provider = export_provider
        self._kg_provider = knowledge_graph_provider
        self._outline_provider = outline_provider
        self._start_time: float = 0.0

    async def execute(self, command: RunPipelineCommand) -> Result:
        self._start_time = time.monotonic()

        try:
            video_id = VideoId(command.video_id)
        except ValueError as e:
            return Result(success=False, error=str(e), error_code="INVALID_VIDEO_ID")

        project = await self._resolve_project(command, video_id)
        if not project:
            return Result(
                success=False,
                error="Failed to create project",
                error_code="PROJECT_CREATION_FAILED",
            )

        project.record_event(PipelineStarted(
            project_id=project.id,
            video_id=video_id.value,
        ))
        project.status = PipelineStatus.RUNNING
        await self._uow.projects.save(project)
        await self._uow.commit()

        stages_to_run = command.stages or [s.value for s in PipelineStage]

        for stage_name in stages_to_run:
            stage = PipelineStage(stage_name)
            result = await self._run_stage(stage, project, video_id, command)
            if not result.success:
                project.record_event(PipelineStageFailed(
                    project_id=project.id,
                    stage=stage.value,
                    error=result.error,
                    video_id=video_id.value,
                ))
                project.fail_stage(stage, result.error)
                await self._uow.projects.save(project)
                await self._uow.commit()
                project.record_event(PipelineFailed(
                    project_id=project.id,
                    video_id=video_id.value,
                    error=result.error,
                    failed_stage=stage.value,
                ))
                return result

            project.record_event(PipelineStageCompleted(
                project_id=project.id,
                stage=stage.value,
                video_id=video_id.value,
            ))
            project.complete_stage(stage)
            await self._uow.projects.save(project)
            await self._uow.commit()

        duration = time.monotonic() - self._start_time
        project.status = PipelineStatus.COMPLETED
        project.record_event(PipelineCompleted(
            project_id=project.id,
            video_id=video_id.value,
            total_stages=len(stages_to_run),
            duration_seconds=round(duration, 2),
        ))
        await self._uow.projects.save(project)
        await self._uow.commit()

        return Result(data={
            "project_id": project.id,
            "video_id": video_id.value,
            "stages_completed": len(stages_to_run),
            "duration_seconds": round(duration, 2),
        })

    async def _resolve_project(
        self, command: RunPipelineCommand, video_id: VideoId
    ) -> Project | None:
        if command.project_id:
            project = await self._uow.projects.get_by_id(command.project_id)
            if project:
                return project

        existing = await self._uow.projects.get_by_video_id(video_id)
        if existing:
            if existing.status in (PipelineStatus.FAILED, PipelineStatus.CANCELLED):
                existing.status = PipelineStatus.RUNNING
                existing.run_count += 1
                await self._uow.projects.save(existing)
                await self._uow.commit()
            return existing

        project = Project(
            video_id=video_id,
            url=command.url,
            title=command.url,
        )
        project.record_event(ProjectCreated(
            project_id=project.id,
            video_id=video_id.value,
            url=command.url,
        ))
        saved = await self._uow.projects.save(project)
        await self._uow.commit()
        return saved

    async def _run_stage(
        self,
        stage: PipelineStage,
        project: Project,
        video_id: VideoId,
        command: RunPipelineCommand,
    ) -> Result:
        try:
            if stage == PipelineStage.TRANSCRIPT:
                return await self._run_transcript_stage(video_id)
            elif stage == PipelineStage.ANALYSIS:
                return await self._run_analysis_stage(video_id)
            elif stage == PipelineStage.KNOWLEDGE_GRAPH:
                return await self._run_kg_stage(video_id)
            elif stage == PipelineStage.SEO:
                return await self._run_seo_stage(video_id)
            elif stage == PipelineStage.OUTLINE:
                return await self._run_outline_stage(video_id)
            elif stage == PipelineStage.DRAFT:
                return await self._run_blog_stage(video_id)
            elif stage == PipelineStage.EXPORT:
                return await self._run_export_stage(video_id)
            elif stage == PipelineStage.METADATA:
                return Result(data={"stage": "metadata", "status": "skipped"})
            return Result(data={"stage": stage.value, "status": "skipped"})
        except Exception as e:
            return Result(success=False, error=str(e), error_code="STAGE_ERROR")

    async def _run_transcript_stage(self, video_id: VideoId) -> Result:
        transcript = await self._transcript_provider.get_transcript(video_id)
        if not transcript.plain_text:
            return Result(
                success=False,
                error="No transcript text produced",
                error_code="TRANSCRIPT_EMPTY",
            )
        transcript.record_event(TranscriptGenerated(
            video_id=video_id.value,
            source=transcript.source.value,
            language=transcript.language,
            word_count=transcript.word_count,
        ))
        await self._uow.transcripts.save(transcript)
        await self._uow.commit()
        return Result(data={"transcript_id": transcript.id, "word_count": transcript.word_count})

    async def _run_analysis_stage(self, video_id: VideoId) -> Result:
        transcript = await self._uow.transcripts.get_by_video_id(video_id)
        if not transcript:
            return Result(success=False, error="No transcript found", error_code="TRANSCRIPT_NOT_FOUND")

        video = await self._uow.videos.get_by_video_id(video_id)
        analysis = await self._analysis_provider.analyze(transcript, video)
        if not analysis.primary_topic:
            return Result(success=False, error="Analysis produced no content", error_code="ANALYSIS_EMPTY")

        analysis.record_event(AnalysisCompleted(
            video_id=video_id.value,
            primary_topic=analysis.primary_topic,
            llm_provider=analysis.llm_provider,
            total_tokens=analysis.total_tokens,
        ))
        await self._uow.analyses.save(analysis)
        await self._uow.commit()
        return Result(data={"analysis_id": analysis.id, "topic": analysis.primary_topic})

    async def _run_seo_stage(self, video_id: VideoId) -> Result:
        blog = await self._uow.blogs.get_by_video_id(video_id)
        if not blog:
            analysis = await self._uow.analyses.get_by_video_id(video_id)
            if not analysis:
                blog = Blog(video_id=video_id)
            else:
                blog = await self._blog_provider.generate(analysis)

        seo = await self._seo_provider.optimize(blog)
        seo.record_event(SEOAnalysisCompleted(
            video_id=video_id.value,
            score=seo.scores.total,
            keyword_count=len(seo.focus_keywords),
        ))
        await self._uow.seos.save(seo)
        await self._uow.commit()
        return Result(data={"seo_id": seo.id, "score": seo.scores.total})

    async def _run_kg_stage(self, video_id: VideoId) -> Result:
        if not self._kg_provider:
            return Result(data={"stage": "knowledge_graph", "status": "skipped"})

        analysis = await self._uow.analyses.get_by_video_id(video_id)
        if not analysis:
            return Result(success=False, error="No analysis found", error_code="ANALYSIS_NOT_FOUND")

        transcript = await self._uow.transcripts.get_by_video_id(video_id)
        kg = await self._kg_provider.build(analysis, transcript)
        kg.record_event(KnowledgeGraphBuilt(
            video_id=video_id.value,
            entity_count=kg.entity_count(),
            relationship_count=kg.relationship_count(),
        ))
        await self._uow.knowledge_graphs.save(kg)
        await self._uow.commit()
        return Result(data={"kg_id": kg.id, "entities": kg.entity_count()})

    async def _run_outline_stage(self, video_id: VideoId) -> Result:
        if not self._outline_provider:
            return Result(data={"stage": "outline", "status": "skipped"})

        analysis = await self._uow.analyses.get_by_video_id(video_id)
        if not analysis:
            return Result(success=False, error="No analysis found", error_code="ANALYSIS_NOT_FOUND")

        seo = await self._uow.seos.get_by_video_id(video_id)
        outline = await self._outline_provider.generate(analysis, seo)
        outline.record_event(OutlineGenerated(
            video_id=video_id.value,
            section_count=len(outline.sections),
        ))
        await self._uow.outlines.save(outline)
        await self._uow.commit()
        return Result(data={"outline_id": outline.id, "sections": len(outline.sections)})

    async def _run_blog_stage(self, video_id: VideoId) -> Result:
        analysis = await self._uow.analyses.get_by_video_id(video_id)
        if not analysis:
            return Result(success=False, error="No analysis found", error_code="ANALYSIS_NOT_FOUND")

        seo = await self._uow.seos.get_by_video_id(video_id)
        blog = await self._blog_provider.generate(analysis, seo)
        if not blog.markdown:
            return Result(success=False, error="Blog generation produced no content", error_code="BLOG_EMPTY")

        blog.record_event(BlogGenerated(
            video_id=video_id.value,
            word_count=blog.statistics.word_count,
            llm_provider=blog.llm_provider,
            total_tokens=blog.total_tokens,
        ))
        await self._uow.blogs.save(blog)
        await self._uow.commit()
        return Result(data={"blog_id": blog.id, "word_count": blog.statistics.word_count})

    async def _run_export_stage(self, video_id: VideoId) -> Result:
        blog = await self._uow.blogs.get_by_video_id(video_id)
        if not blog:
            return Result(success=False, error="No blog found", error_code="BLOG_NOT_FOUND")

        export = await self._export_provider.export(
            blog, [ExportFormat.MARKDOWN.value, ExportFormat.HTML.value]
        )
        export.record_event(ExportCompleted(
            video_id=video_id.value,
            export_id=export.id,
            formats=[f.value for f in export.formats],
            total_size_bytes=export.total_size_bytes,
        ))
        await self._uow.exports.save(export)
        await self._uow.commit()
        return Result(data={"export_id": export.id, "files": len(export.files)})
