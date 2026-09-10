from __future__ import annotations

import hashlib
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from publishing.models import (
    CodeBlockInfo, DocumentModel, ImageInfo, TableInfo,
)

logger = logging.getLogger(__name__)

IMAGE_URL_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"}


class AssetManager:
    def __init__(self):
        self._assets_dir: Path | None = None

    def export_images(self, document: DocumentModel, output_dir: Path,
                      source_dir: Path | None = None) -> list[ImageInfo]:
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        self._assets_dir = images_dir

        exported: list[ImageInfo] = []
        for img in document.images:
            local_filename = self._resolve_image(img, images_dir, source_dir)
            if local_filename:
                exported.append(ImageInfo(
                    url=img.url,
                    alt=img.alt,
                    caption=img.caption,
                    filename=local_filename,
                    local_path=str(images_dir / local_filename),
                ))

        return exported

    def _resolve_image(self, img: ImageInfo, images_dir: Path,
                       source_dir: Path | None = None) -> str | None:
        url = img.url
        filename = img.filename or url.split("/")[-1].split("?")[0]

        if not filename or "." not in filename:
            ext = self._guess_extension(url)
            filename = f"image_{hash(url) & 0xFFFF:04x}{ext}"

        dest = images_dir / filename

        if url.startswith(("http://", "https://")):
            try:
                import urllib.request
                urllib.request.urlretrieve(url, str(dest))
                logger.info("Downloaded image: %s", filename)
                return filename
            except Exception as e:
                logger.warning("Could not download image %s: %s", url, e)
                return None

        if source_dir:
            candidate = source_dir / url.lstrip("/")
            if candidate.exists():
                shutil.copy2(str(candidate), str(dest))
                logger.info("Copied image: %s", filename)
                return filename

        local_path = Path(url)
        if local_path.exists():
            shutil.copy2(str(local_path), str(dest))
            return filename

        return None

    def extract_images_from_content(self, content: str, output_dir: Path,
                                    source_dir: Path | None = None) -> list[ImageInfo]:
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        self._assets_dir = images_dir

        exported: list[ImageInfo] = []
        seen = set()

        for match in IMAGE_URL_RE.finditer(content):
            alt = match.group(1).strip()
            url = match.group(2).strip()
            if url in seen:
                continue
            seen.add(url)

            img = ImageInfo(url=url, alt=alt)
            local_filename = self._resolve_image(img, images_dir, source_dir)
            if local_filename:
                exported.append(ImageInfo(
                    url=url, alt=alt, filename=local_filename,
                    local_path=str(images_dir / local_filename),
                ))

        return exported

    def export_tables(self, document: DocumentModel, output_dir: Path) -> list[TableInfo]:
        exported: list[TableInfo] = []
        for table in document.tables:
            exported.append(TableInfo(
                headers=table.headers,
                rows=table.rows,
                caption=table.caption,
                alignment=table.alignment,
            ))
        return exported

    def export_code_blocks(self, document: DocumentModel, output_dir: Path) -> list[CodeBlockInfo]:
        exported: list[CodeBlockInfo] = []
        for cb in document.code_blocks:
            exported.append(CodeBlockInfo(
                language=cb.language or "text",
                code=cb.code,
                caption=cb.caption,
            ))
        return exported

    def copy_additional_assets(self, output_dir: Path,
                               source_dirs: list[Path] | None = None) -> list[str]:
        copied: list[str] = []
        if not source_dirs:
            return copied

        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        for src_dir in source_dirs:
            if not src_dir.exists():
                continue
            for item in src_dir.iterdir():
                if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS | {".pdf", ".zip", ".json"}:
                    dest = assets_dir / item.name
                    if not dest.exists():
                        shutil.copy2(str(item), str(dest))
                        copied.append(item.name)

        return copied

    def get_asset_manifest(self, output_dir: Path) -> list[dict[str, Any]]:
        manifest: list[dict[str, Any]] = []
        images_dir = output_dir / "images"
        if images_dir.exists():
            for f in sorted(images_dir.iterdir()):
                if f.is_file():
                    manifest.append({
                        "filename": f.name,
                        "path": f"images/{f.name}",
                        "size_bytes": f.stat().st_size,
                        "checksum": hashlib.sha256(f.read_bytes()).hexdigest()[:32],
                    })
        assets_dir = output_dir / "assets"
        if assets_dir.exists():
            for f in sorted(assets_dir.iterdir()):
                if f.is_file():
                    manifest.append({
                        "filename": f.name,
                        "path": f"assets/{f.name}",
                        "size_bytes": f.stat().st_size,
                        "checksum": hashlib.sha256(f.read_bytes()).hexdigest()[:32],
                    })
        return manifest

    def cleanup(self, output_dir: Path) -> None:
        images_dir = output_dir / "images"
        if images_dir.exists():
            shutil.rmtree(str(images_dir))
        assets_dir = output_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(str(assets_dir))

    @staticmethod
    def _guess_extension(url: str) -> str:
        path = url.split("?")[0].lower()
        if ".jpg" in path or ".jpeg" in path:
            return ".jpg"
        if ".png" in path:
            return ".png"
        if ".gif" in path:
            return ".gif"
        if ".webp" in path:
            return ".webp"
        if ".svg" in path:
            return ".svg"
        return ".jpg"
