#!/usr/bin/env python3
"""CLI entry point for Phase 4 — Transcript Engine.

Usage:
    python run_transcript.py <video_id> [--language en] [--no-whisper] [--json]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.transcript_service import TranscriptService
from models.transcript import TranscriptResult
from utils.logging_config import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YouTube Transcript Engine — retrieve the best available transcript.",
    )
    parser.add_argument("video_id", type=str, help="11-character YouTube video ID")
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=None,
        help="Preferred language code (e.g. 'en', 'es')",
    )
    parser.add_argument(
        "--no-whisper",
        action="store_true",
        help="Skip Whisper STT fallback",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass cache",
    )
    return parser.parse_args()


def display_transcript(result: TranscriptResult) -> None:
    """Display transcript result in a human-readable format."""
    status = "✅" if result.success else "❌"
    source_icons = {"manual": "📝", "auto": "🤖", "whisper": "🎙️"}
    icon = source_icons.get(result.source.value, "📄")

    print(f"\n{status} Transcript Result")
    print(f"  Video ID:    {result.video_id}")
    print(f"  Source:      {icon} {result.source.value} ({result.provider.value})")
    print(f"  Language:    {result.language}")
    if result.language_confidence:
        print(f"  Confidence:  {result.language_confidence:.2%}")
    print(f"  Words:       {result.word_count:,}")
    print(f"  Characters:  {result.character_count:,}")
    print(f"  Read time:   {result.estimated_read_time}")
    print(f"  Duration:    {result.duration_seconds:.1f}s" if result.duration_seconds else "")
    print(f"  Segments:    {len(result.segments)}")

    if result.whisper_info:
        wi = result.whisper_info
        print(f"\n  Whisper Info:")
        print(f"    Model:          {wi.model_name}")
        if wi.processing_time_seconds:
            print(f"    Processing:     {wi.processing_time_seconds:.1f}s")
        if wi.audio_duration_seconds:
            print(f"    Audio duration: {wi.audio_duration_seconds:.1f}s")
        if wi.language_detected:
            print(f"    Detected lang:  {wi.language_detected}")

    if result.error:
        print(f"\n  Error: {result.error}")

    print(f"\n  Pipeline:")
    for step in result.pipeline_steps:
        icon_map = {"ok": "✅", "running": "▶️", "pending": "⏳", "error": "❌", "skipped": "⏭️"}
        print(f"    {icon_map.get(step.status, '❓')} {step.name}: {step.detail}")

    if result.success:
        print(f"\n  Plain Text (first 300 chars):")
        print(f"    {result.plain_text[:300]}...")
        print()

        print(f"  Paragraph Text (first 300 chars):")
        print(f"    {result.paragraph_text[:300]}...")
        print()


def main() -> None:
    setup_logging()
    args = parse_args()

    service = TranscriptService()

    print(f"🔍 Fetching transcript for video {args.video_id}...")
    if args.language:
        print(f"   Language: {args.language}")

    start = time.time()
    result = service.get_transcript(
        video_id=args.video_id,
        language=args.language,
        force_refresh=args.force_refresh,
        allow_whisper=not args.no_whisper,
    )
    elapsed = time.time() - start

    if args.json:
        data = result.model_dump()
        data["elapsed_seconds"] = round(elapsed, 2)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        display_transcript(result)
        print(f"  ⏱️  Total: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
