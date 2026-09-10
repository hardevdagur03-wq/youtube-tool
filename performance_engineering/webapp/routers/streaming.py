"""Streaming API endpoints — Server-Sent Events."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from performance_engineering.streaming import SSEManager

router = APIRouter(prefix="/api/stream", tags=["streaming"])

_sse_manager: SSEManager | None = None


def init_sse(manager: SSEManager) -> None:
    """Initialize the SSE manager reference.

    Args:
        manager: SSEManager instance.
    """
    global _sse_manager
    _sse_manager = manager


@router.get("/pipeline/{pipeline_id}")
async def stream_pipeline(pipeline_id: str):
    """SSE endpoint for streaming pipeline progress."""
    if _sse_manager is None:
        return {"error": "SSE not initialized"}

    async def event_generator():
        async for event in _sse_manager.subscribe(pipeline_id):
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
