"""Phase 4 entry point – Fetch metadata for a list of YouTube video IDs."""

import logging
import sys

from config.settings import ConfigurationError
from services.video_metadata import VideoMetadataService, VideoMetadataError
from utils.logging_config import setup_logging

logger = logging.getLogger("run_video_metadata")


def main() -> None:
    setup_logging()

    if len(sys.argv) > 1:
        video_ids = [v.strip() for v in sys.argv[1:] if v.strip()]
    else:
        raw = input("Enter video IDs (comma or space separated): ").strip()
        if not raw:
            logger.error("No video IDs provided.")
            print("\n[-] Error: at least one video ID is required.", file=sys.stderr)
            sys.exit(1)
        video_ids = [v.strip() for v in raw.replace(",", " ").split() if v.strip()]

    if not video_ids:
        logger.error("No valid video IDs after parsing.")
        print("\n[-] Error: no valid video IDs provided.", file=sys.stderr)
        sys.exit(1)

    service = VideoMetadataService()

    try:
        result = service.fetch_metadata(video_ids)
    except VideoMetadataError as exc:
        logger.error("Metadata fetch failed: %s", exc)
        print(f"\n[-] Metadata fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as exc:
        logger.critical("Configuration error: %s", exc)
        print(f"\n[-] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    videos = result["videos"]
    total_input = result["total_input"]
    total_retrieved = result["total_retrieved"]
    requests = result["total_requests"]
    dedup = result["deduplicated"]

    if dedup:
        print(f"    (removed {dedup} duplicate(s))")

    print(f"\n[+] Metadata fetch complete!")
    print(f"    Input IDs   : {total_input}")
    print(f"    Retrieved   : {total_retrieved}")
    print(f"    API requests: {requests}")

    if videos:
        print(f"\n    Videos ({'first 5 of ' if len(videos) > 5 else ''}{len(videos)}):")
        for v in videos[:5]:
            print(f"      - {v['video_id']} | {v['title']} | {v['duration']} | {v['views']} views")
        if len(videos) > 5:
            print(f"      ... and {len(videos) - 5} more")

    sys.exit(0)


if __name__ == "__main__":
    main()
