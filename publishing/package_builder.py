from __future__ import annotations

import hashlib
import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Any

from publishing.models import (
    ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
    ManifestInfo, PackageInfo,
)

logger = logging.getLogger(__name__)


class PackageBuilder:
    def build_zip(self, output_dir: Path, export_id: str,
                  files: list[ExportFileInfo], manifest: ManifestInfo | None = None,
                  include_manifest: bool = True) -> Path:
        zip_filename = f"blog_v{manifest.version if manifest else 1}.zip"
        zip_path = output_dir.parent / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                file_path = output_dir / f.filename
                if file_path.exists():
                    zf.write(file_path, f.filename)

            images_dir = output_dir / "images"
            if images_dir.exists():
                for img in images_dir.iterdir():
                    if img.is_file():
                        zf.write(img, f"images/{img.name}")

            assets_dir = output_dir / "assets"
            if assets_dir.exists():
                for asset in assets_dir.iterdir():
                    if asset.is_file():
                        zf.write(asset, f"assets/{asset.name}")

        return zip_path

    def build_package(self, output_dir: Path, export_id: str, version: int,
                      files: list[ExportFileInfo], manifest: ManifestInfo) -> PackageInfo:
        package_dir = output_dir.parent / "packages"
        package_dir.mkdir(parents=True, exist_ok=True)

        package_filename = f"blog_v{version}_package.zip"
        package_path = package_dir / package_filename

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                file_path = output_dir / f.filename
                if file_path.exists():
                    zf.write(file_path, f.filename)

            manifest_content = manifest.model_dump_json(indent=2)
            zf.writestr("manifest.json", manifest_content)

            for key, extra_file in [
                ("export_metadata", output_dir / "export_metadata.json"),
                ("project", output_dir / "project.json"),
            ]:
                if extra_file.exists():
                    zf.write(extra_file, extra_file.name)

            images_dir = output_dir / "images"
            if images_dir.exists():
                for img in images_dir.iterdir():
                    if img.is_file():
                        zf.write(img, f"images/{img.name}")

            assets_dir = output_dir / "assets"
            if assets_dir.exists():
                for asset in assets_dir.iterdir():
                    if asset.is_file():
                        zf.write(asset, f"assets/{asset.name}")

        size = package_path.stat().st_size
        checksum = hashlib.sha256(package_path.read_bytes()).hexdigest()[:32]

        return PackageInfo(
            package_id=f"pkg_{export_id}",
            export_id=export_id,
            filename=package_filename,
            size_bytes=size,
            size_display=self._size_display(size),
            checksum=checksum,
            file_count=len(files) + 1,
            manifest=manifest,
        )

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
