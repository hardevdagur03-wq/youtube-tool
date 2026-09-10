from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from publishing.models import (
    ExportFileInfo, ExportFormat, ManifestInfo,
)

logger = logging.getLogger(__name__)


class ManifestGenerator:
    def generate(self, project_id: str, export_id: str, version: int,
                 title: str, files: list[ExportFileInfo],
                 output_dir: Path, statistics: dict[str, Any] | None = None,
                 metadata: dict[str, Any] | None = None) -> ManifestInfo:
        manifest = ManifestInfo(
            project_id=project_id,
            export_id=export_id,
            version=version,
            title=title,
            formats=list(set(f.format.value for f in files)),
            statistics=statistics or {},
            metadata=metadata or {},
        )

        for f in files:
            file_info: dict[str, Any] = {
                "filename": f.filename,
                "format": f.format.value,
                "size_bytes": f.size_bytes,
                "size_display": f.size_display,
                "mime_type": f.mime_type,
                "checksum": f.checksum,
                "valid": f.valid,
            }
            manifest.files.append(file_info)
            if f.filename:
                manifest.checksums[f.filename] = f.checksum

        content = manifest.model_dump_json(indent=2)
        fpath = output_dir / "manifest.json"
        fpath.write_text(content, encoding="utf-8")

        manifest.files.append({
            "filename": "manifest.json",
            "format": "json",
            "size_bytes": fpath.stat().st_size,
            "checksum": hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
        })

        return manifest

    def generate_project_manifest(self, project_id: str, output_dir: Path,
                                  project_data: dict[str, Any] | None = None) -> Path:
        manifest: dict[str, Any] = {
            "project_id": project_id,
            "generated_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "version": "2.0",
        }

        if project_data:
            manifest["project"] = {
                "title": project_data.get("name", ""),
                "video_id": project_data.get("video_id", ""),
                "status": project_data.get("status", ""),
                "language": project_data.get("language", "en"),
                "created_at": project_data.get("created_at", ""),
                "completed_at": project_data.get("completed_at", ""),
            }

        fpath = output_dir / "project.json"
        content = json.dumps(manifest, indent=2, ensure_ascii=False)
        fpath.write_text(content, encoding="utf-8")
        return fpath

    def generate_export_metadata(self, project_id: str, export_id: str,
                                 version: int, output_dir: Path,
                                 formats: list[str], total_size: int,
                                 file_count: int, execution_time_ms: float) -> Path:
        meta: dict[str, Any] = {
            "export_id": export_id,
            "project_id": project_id,
            "version": version,
            "created_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "formats": formats,
            "total_size_bytes": total_size,
            "file_count": file_count,
            "execution_time_ms": execution_time_ms,
        }
        fpath = output_dir / "export_metadata.json"
        content = json.dumps(meta, indent=2, ensure_ascii=False)
        fpath.write_text(content, encoding="utf-8")
        return fpath
