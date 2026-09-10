from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from editor.editor_models import (
    AutosaveConfig, AutosaveState, CursorPosition, RecoveryPoint,
    ScrollPosition, SelectionRange, utc_now,
)

logger = logging.getLogger(__name__)


class AutosaveManager:
    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir
        self._config = AutosaveConfig()
        self._timer: threading.Timer | None = None
        self._last_saved_content: str = ""
        self._last_saved_checksum: str = ""
        self._change_listeners: list[Callable] = []
        self._recovery_points: dict[str, list[RecoveryPoint]] = {}
        self._dirty = False

    @property
    def config(self) -> AutosaveConfig:
        return self._config

    def set_config(self, config: AutosaveConfig) -> None:
        self._config = config

    def mark_dirty(self) -> None:
        self._dirty = True

    def mark_clean(self) -> None:
        self._dirty = False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def save(
        self,
        project_id: str,
        content: str,
        cursor: CursorPosition | None = None,
        scroll: ScrollPosition | None = None,
        selection: SelectionRange | None = None,
        view_mode: str = "split",
    ) -> AutosaveState:
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

        if checksum == self._last_saved_checksum:
            return AutosaveState(
                project_id=project_id,
                content=content,
                checksum=checksum,
                saved_at=utc_now(),
            )

        state = AutosaveState(
            project_id=project_id,
            content=content,
            cursor=cursor or CursorPosition(),
            scroll=scroll or ScrollPosition(),
            selection=selection or SelectionRange(),
            view_mode=view_mode,
            saved_at=utc_now(),
            checksum=checksum,
        )

        self._last_saved_content = content
        self._last_saved_checksum = checksum
        self._dirty = False

        if self._storage_dir:
            self._persist(project_id, state)

        self._emit("autosave", {
            "project_id": project_id,
            "checksum": checksum,
            "saved_at": state.saved_at,
        })

        return state

    def load_latest(self, project_id: str) -> AutosaveState | None:
        if not self._storage_dir:
            return None
        return self._load_persisted(project_id)

    def create_recovery_point(
        self,
        project_id: str,
        content: str,
        cursor: CursorPosition | None = None,
        scroll: ScrollPosition | None = None,
        reason: str = "manual",
    ) -> RecoveryPoint:
        point = RecoveryPoint(
            point_id=uuid.uuid4().hex[:12],
            content=content,
            cursor=cursor or CursorPosition(),
            scroll=scroll or ScrollPosition(),
            reason=reason,
            checksum=hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
        )

        if project_id not in self._recovery_points:
            self._recovery_points[project_id] = []
        self._recovery_points[project_id].append(point)

        max_points = self._config.max_recovery_points
        if len(self._recovery_points[project_id]) > max_points:
            self._recovery_points[project_id].pop(0)

        if self._storage_dir:
            self._persist_recovery_point(project_id, point)

        self._emit("recovery_point_created", {
            "project_id": project_id,
            "point_id": point.point_id,
            "reason": reason,
        })

        return point

    def get_recovery_points(self, project_id: str) -> list[RecoveryPoint]:
        points = self._recovery_points.get(project_id, [])
        if not points and self._storage_dir:
            points = self._load_recovery_points(project_id)
            self._recovery_points[project_id] = points
        return points

    def recover_from_point(self, project_id: str, point_id: str) -> RecoveryPoint | None:
        points = self.get_recovery_points(project_id)
        for point in points:
            if point.point_id == point_id:
                self._emit("autosave_recovered", {
                    "project_id": project_id,
                    "point_id": point_id,
                })
                return point
        return None

    def has_recovery_data(self, project_id: str) -> bool:
        points = self.get_recovery_points(project_id)
        if points:
            return True
        if self._storage_dir:
            state = self._load_persisted(project_id)
            return state is not None
        return False

    def clear_recovery(self, project_id: str) -> None:
        self._recovery_points.pop(project_id, None)
        if self._storage_dir:
            self._clear_persisted(project_id)

    def start_autosave_timer(self, callback: Callable[[], None]) -> None:
        self.stop_autosave_timer()
        if not self._config.enabled:
            return

        def _tick():
            if self._dirty:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Autosave timer callback error: {e}")
            self._timer = threading.Timer(self._config.interval_seconds, _tick)
            self._timer.daemon = True
            self._timer.start()

        self._timer = threading.Timer(self._config.interval_seconds, _tick)
        self._timer.daemon = True
        self._timer.start()

    def stop_autosave_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _persist(self, project_id: str, state: AutosaveState) -> None:
        if not self._storage_dir:
            return
        autosave_dir = self._storage_dir / project_id / "autosave"
        autosave_dir.mkdir(parents=True, exist_ok=True)
        try:
            (autosave_dir / "state.json").write_text(
                state.model_dump_json(indent=2), encoding="utf-8"
            )
            (autosave_dir / "content.md").write_text(
                state.content, encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to persist autosave: {e}")

    def _load_persisted(self, project_id: str) -> AutosaveState | None:
        if not self._storage_dir:
            return None
        state_file = self._storage_dir / project_id / "autosave" / "state.json"
        content_file = self._storage_dir / project_id / "autosave" / "content.md"
        if state_file.exists() and content_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                data["content"] = content_file.read_text(encoding="utf-8")
                return AutosaveState(**data)
            except Exception as e:
                logger.error(f"Failed to load autosave: {e}")
        return None

    def _persist_recovery_point(self, project_id: str, point: RecoveryPoint) -> None:
        if not self._storage_dir:
            return
        recovery_dir = self._storage_dir / project_id / "autosave" / "recovery"
        recovery_dir.mkdir(parents=True, exist_ok=True)
        try:
            (recovery_dir / f"{point.point_id}.json").write_text(
                point.model_dump_json(indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to persist recovery point: {e}")

    def _load_recovery_points(self, project_id: str) -> list[RecoveryPoint]:
        if not self._storage_dir:
            return []
        recovery_dir = self._storage_dir / project_id / "autosave" / "recovery"
        if not recovery_dir.exists():
            return []
        points: list[RecoveryPoint] = []
        try:
            for f in sorted(recovery_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix == ".json":
                    data = json.loads(f.read_text(encoding="utf-8"))
                    points.append(RecoveryPoint(**data))
        except Exception as e:
            logger.error(f"Failed to load recovery points: {e}")
        return points

    def _clear_persisted(self, project_id: str) -> None:
        if not self._storage_dir:
            return
        import shutil
        autosave_dir = self._storage_dir / project_id / "autosave"
        try:
            if autosave_dir.exists():
                shutil.rmtree(str(autosave_dir))
        except Exception as e:
            logger.error(f"Failed to clear autosave: {e}")

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Autosave listener error: {e}")
