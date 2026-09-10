"""Download API endpoints — signed URLs and file delivery."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from export_delivery.download_service import DownloadService

router = APIRouter(prefix="/api/v3/downloads", tags=["downloads"])

_download_service: DownloadService | None = None


def initialize(download_service: DownloadService) -> None:
    """Initialize the download API with the download service."""
    global _download_service
    _download_service = download_service


@router.get("/{token}")
async def download_file(token: str):
    """Download a file via secure token."""
    if _download_service is None:
        raise HTTPException(status_code=503, detail="Download service not initialized")

    info = _download_service.validate_token(token)
    if info is None:
        raise HTTPException(status_code=404, detail="Download link invalid or expired")

    file_path = info["file_path"]
    filename = info["filename"]

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    mime_map = {
        ".md": "text/markdown",
        ".html": "text/html",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".json": "application/json",
        ".jsonld": "application/ld+json",
        ".yaml": "text/yaml",
        ".zip": "application/zip",
    }

    ext = os.path.splitext(file_path)[1].lower()
    mime = mime_map.get(ext, "application/octet-stream")

    return FileResponse(
        file_path,
        media_type=mime,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{token}/info")
async def get_download_info(token: str):
    """Get download file info without downloading."""
    if _download_service is None:
        raise HTTPException(status_code=503, detail="Download service not initialized")

    info = _download_service.validate_token(token)
    if info is None:
        raise HTTPException(status_code=404, detail="Download link invalid or expired")

    return {
        "success": True,
        "filename": info["filename"],
        "format": info["format"],
        "download_count": info["download_count"],
    }


@router.post("/{token}/revoke")
async def revoke_download_token(token: str):
    """Revoke a download token."""
    if _download_service is None:
        raise HTTPException(status_code=503, detail="Download service not initialized")

    success = _download_service.revoke_token(token)
    return {"success": success}
