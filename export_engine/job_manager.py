from __future__ import annotations

import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from export_engine.models import (
    ExportRequest,
    JobResult,
    JobState,
    JobStatus,
    ProgressStage,
    ProgressUpdate,
    StageProgress,
    STAGE_LABELS,
)

CURRENT_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = CURRENT_DIR / "webapp" / "runs"

_RUN_ID_PATTERN = __import__("re").compile(r"^[0-9a-f]{12}$")
_STALE_AGE_SECONDS = 3600


class JobNotFoundError(Exception):
    pass


class JobAlreadyExistsError(Exception):
    pass


class JobManager:
    """Manages the lifecycle of export jobs.

    Thread-safe in-memory store with disk persistence for progress/result.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = Lock()
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

    def create_job(self, request: ExportRequest) -> JobState:
        job_id = uuid.uuid4().hex[:12]
        run_dir = RUNS_DIR / job_id
        run_dir.mkdir(parents=True, exist_ok=True)

        job = JobState(
            job_id=job_id,
            status=JobStatus.PENDING,
            request=request,
            progress=ProgressUpdate(job_id=job_id),
            progress_file=str(run_dir / "progress.json"),
            result_file=str(run_dir / "result.json"),
            csv_path=str(run_dir / "videos.csv"),
            created_at=datetime.now(timezone.utc),
        )
        self._init_stages(job)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def _init_stages(self, job: JobState) -> None:
        stages_order = [
            ProgressStage.VALIDATE_URL,
            ProgressStage.CHECK_CACHE,
            ProgressStage.RESOLVE_CHANNEL,
            ProgressStage.FETCH_PLAYLIST,
            ProgressStage.FETCH_VIDEO_IDS,
            ProgressStage.FETCH_METADATA,
            ProgressStage.GENERATE_CSV,
            ProgressStage.COMPLETE,
        ]
        for stage in stages_order:
            key = stage.value
            job.progress.stages[key] = StageProgress(
                stage=stage,
                status=JobStatus.PENDING,
                label=STAGE_LABELS.get(stage, stage.value),
                detail="",
            )

    def get_job(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_or_load_job(self, job_id: str) -> JobState | None:
        job = self.get_job(job_id)
        if job is not None:
            return job
        run_dir = RUNS_DIR / job_id
        if not run_dir.exists():
            return None
        job = self._load_from_disk(job_id, run_dir)
        if job is not None:
            with self._lock:
                self._jobs[job_id] = job
        return job

    def _load_from_disk(self, job_id: str, run_dir: Path) -> JobState | None:
        try:
            job = JobState(job_id=job_id)
            progress_path = run_dir / "progress.json"
            if progress_path.exists():
                data = json.loads(progress_path.read_text(encoding="utf-8"))
                if "status" in data:
                    job.status = JobStatus(data["status"])
                if "stages" in data:
                    for key, sdata in data["stages"].items():
                        job.progress.stages[key] = StageProgress(**sdata)
                job.progress.error = data.get("error", "")
                job.progress.overall_progress_pct = data.get("overall_progress_pct", 0.0)
            result_path = run_dir / "result.json"
            if result_path.exists():
                rdata = json.loads(result_path.read_text(encoding="utf-8"))
                job.result = JobResult(**rdata)
                if rdata.get("success"):
                    job.status = JobStatus.COMPLETED
                elif rdata.get("error"):
                    job.status = JobStatus.FAILED
            csv_path = run_dir / "videos.csv"
            if csv_path.exists():
                job.csv_path = str(csv_path)
            job.progress_file = str(progress_path)
            job.result_file = str(result_path)
            return job
        except Exception:
            return None

    def start_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self._persist_progress(job)

    def update_stage(
        self,
        job_id: str,
        stage: ProgressStage,
        status: JobStatus = JobStatus.RUNNING,
        detail: str = "",
        progress_pct: float = 0.0,
        current_page: int = 0,
        total_pages: int = 0,
        processed: int = 0,
        total: int = 0,
        api_calls: int = 0,
        rows_written: int = 0,
        eta_seconds: float = 0.0,
        error: str = "",
    ) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        key = stage.value
        if key not in job.progress.stages:
            job.progress.stages[key] = StageProgress(stage=stage)
        sp = job.progress.stages[key]
        sp.status = status
        sp.detail = detail
        sp.progress_pct = progress_pct
        sp.current_page = current_page
        sp.total_pages = total_pages
        sp.processed = processed
        sp.total = total
        sp.remaining = total - processed
        sp.api_calls = api_calls
        sp.rows_written = rows_written
        sp.eta_seconds = eta_seconds
        sp.elapsed = time.time() - (job.started_at.timestamp() if job.started_at else time.time())
        if error:
            sp.error = error
        job.progress.current_stage = stage.value
        job.progress.error = error
        if error:
            job.progress.status = JobStatus.FAILED
        self._compute_overall_progress(job)
        self._persist_progress(job)

    def _compute_overall_progress(self, job: JobState) -> None:
        stages_order = [
            ProgressStage.VALIDATE_URL,
            ProgressStage.CHECK_CACHE,
            ProgressStage.RESOLVE_CHANNEL,
            ProgressStage.FETCH_PLAYLIST,
            ProgressStage.FETCH_VIDEO_IDS,
            ProgressStage.FETCH_METADATA,
            ProgressStage.GENERATE_CSV,
            ProgressStage.COMPLETE,
        ]
        total_weight = len(stages_order)
        completed_weight = 0
        for stage in stages_order:
            key = stage.value
            sp = job.progress.stages.get(key)
            if sp is None:
                continue
            if sp.status == JobStatus.COMPLETED:
                completed_weight += 1
            elif sp.status == JobStatus.RUNNING and stage == ProgressStage.FETCH_METADATA:
                if sp.total > 0:
                    partial = sp.progress_pct / 100.0
                    completed_weight += partial
        job.progress.overall_progress_pct = (completed_weight / total_weight) * 100.0
        if job.started_at:
            elapsed = time.time() - job.started_at.timestamp()
            job.progress.elapsed_seconds = elapsed
            if job.progress.overall_progress_pct > 0:
                eta = (elapsed / (job.progress.overall_progress_pct / 100.0)) - elapsed
                job.progress.eta_seconds = max(0.0, eta)

    def complete_job(self, job_id: str, result: JobResult) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = datetime.now(timezone.utc)
        job.progress.status = JobStatus.COMPLETED
        self.update_stage(job_id, ProgressStage.COMPLETE, JobStatus.COMPLETED, "Export completed successfully")
        self._persist_result(job)
        self._persist_progress(job)

    def fail_job(self, job_id: str, error: str, error_type: str = "", error_action: str = "") -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = JobStatus.FAILED
        job.error = error
        job.completed_at = datetime.now(timezone.utc)
        job.progress.status = JobStatus.FAILED
        job.progress.error = error
        job.progress.error_type = error_type
        job.progress.error_action = error_action
        elapsed = time.time() - (job.started_at.timestamp() if job.started_at else time.time())
        job.result = JobResult(
            success=False,
            job_id=job_id,
            error=error,
            error_type=error_type,
            elapsed_seconds=round(elapsed, 1),
        )
        self._persist_result(job)
        self._persist_progress(job)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job is None:
            return False
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return False
        job.cancel_requested = True
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        job.progress.status = JobStatus.CANCELLED
        self._cleanup_job_files(job)
        self._persist_progress(job)
        return True

    def is_cancelled(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job is None:
            return True
        return job.cancel_requested or job.status == JobStatus.CANCELLED

    def _persist_progress(self, job: JobState) -> None:
        try:
            data = {
                "status": job.status.value,
                "stages": {k: v.model_dump() for k, v in job.progress.stages.items()},
                "current_stage": job.progress.current_stage,
                "overall_progress_pct": round(job.progress.overall_progress_pct, 1),
                "elapsed_seconds": round(job.progress.elapsed_seconds, 1),
                "eta_seconds": round(job.progress.eta_seconds, 1),
                "error": job.progress.error,
                "error_type": job.progress.error_type,
                "error_action": job.progress.error_action,
            }
            path = Path(job.progress_file)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            tmp.replace(path)
        except Exception:
            pass

    def _persist_result(self, job: JobState) -> None:
        if job.result is None:
            return
        try:
            path = Path(job.result_file)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(job.result.model_dump(), f)
            tmp.replace(path)
        except Exception:
            pass

    def _cleanup_job_files(self, job: JobState) -> None:
        try:
            run_dir = Path(job.progress_file).parent
            if run_dir.exists():
                shutil.rmtree(str(run_dir), ignore_errors=True)
        except Exception:
            pass

    def clean_stale_runs(self) -> None:
        if not RUNS_DIR.exists():
            return
        now = time.time()
        for entry in RUNS_DIR.iterdir():
            if not entry.is_dir():
                continue
            if not _RUN_ID_PATTERN.match(entry.name):
                continue
            result_file = entry / "result.json"
            if result_file.exists():
                continue
            age = now - entry.stat().st_mtime
            if age > _STALE_AGE_SECONDS:
                try:
                    shutil.rmtree(str(entry), ignore_errors=True)
                except Exception:
                    pass

    def get_active_jobs(self) -> list[JobState]:
        with self._lock:
            return [
                j for j in self._jobs.values()
                if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
            ]

    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = status
        self._persist_progress(job)

    def get_stage_progress(self, job_id: str, stage: ProgressStage) -> StageProgress | None:
        job = self.get_job(job_id)
        if job is None:
            return None
        return job.progress.stages.get(stage.value)
