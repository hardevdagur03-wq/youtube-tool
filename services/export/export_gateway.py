"""Export Gateway — orchestrates multi-format exports with queuing and tracking."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from services.export.export_provider import (
    ExportFormat,
    ExportProvider,
    ExportRequest,
    ExportResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ExportJob:
    job_id: str = ""
    status: str = "pending"
    results: list[ExportResult] = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0


class ExportGateway:
    """Central gateway for multi-format document export."""

    def __init__(self):
        self._providers: dict[str, ExportProvider] = {}
        self._jobs: dict[str, ExportJob] = {}

    def register_provider(self, name: str, provider: ExportProvider) -> None:
        self._providers[name] = provider
        logger.info("Export provider registered: %s", name)

    def export(self, request: ExportRequest) -> ExportResult:
        provider = self._providers.get(request.format.value)
        if not provider:
            return ExportResult(
                success=False,
                format=request.format.value,
                error=f"No provider registered for format: {request.format.value}",
            )
        return provider.export(request)

    def export_multi(self, request: ExportRequest, formats: list[ExportFormat]) -> ExportJob:
        start = time.time()
        job_id = f"exp_{int(start)}_{len(self._jobs)}"
        job = ExportJob(job_id=job_id)
        results = []

        for fmt in formats:
            fmt_request = ExportRequest(
                title=request.title,
                content=request.content,
                author=request.author,
                format=fmt,
                include_toc=request.include_toc,
                include_meta=request.include_meta,
                template=request.template,
                options=request.options,
            )
            result = self.export(fmt_request)
            results.append(result)

        job.results = results
        job.duration_ms = (time.time() - start) * 1000
        job.status = "completed" if all(r.success for r in results) else "partial"
        self._jobs[job_id] = job
        return job

    def export_all(self, request: ExportRequest) -> ExportJob:
        formats = list(ExportFormat)
        return self.export_multi(request, formats)

    def validate(self, content: str) -> dict[str, bool]:
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = provider.validate(content)
            except Exception:
                results[name] = False
        return results

    def get_job(self, job_id: str) -> ExportJob | None:
        return self._jobs.get(job_id)

    def list_formats(self) -> list[str]:
        return list(self._providers.keys())
