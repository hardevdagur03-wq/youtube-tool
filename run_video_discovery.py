"""Phase 3 entry point – Discover all uploaded public video IDs for a channel."""

import logging
import sys

from config.settings import ConfigurationError
from services.video_discovery import VideoDiscovery, VideoDiscoveryError
from utils.logging_config import setup_logging

logger = logging.getLogger("run_video_discovery")


def main() -> None:
    setup_logging()

    if len(sys.argv) > 1:
        channel_id = sys.argv[1]
    else:
        channel_id = input("Enter YouTube Channel ID (UC...): ").strip()

    if not channel_id:
        logger.error("No channel ID provided.")
        print("\n[-] Error: Channel ID is required.", file=sys.stderr)
        sys.exit(1)

    if not channel_id.startswith("UC"):
        logger.warning("Channel ID does not start with 'UC': %s", channel_id)

    discovery = VideoDiscovery()

    try:
        result = discovery.discover(channel_id)
    except VideoDiscoveryError as exc:
        logger.error("Video discovery failed: %s", exc)
        print(f"\n[-] Discovery failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as exc:
        logger.critical("Configuration error: %s", exc)
        print(f"\n[-] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    total = result["total_videos"]
    requests = result["total_requests"]

    print(f"\n[+] Video discovery complete!")
    print(f"    Channel ID  : {result['channel_id']}")
    print(f"    Total videos: {total}")
    print(f"    API requests: {requests}")

    if total > 0:
        print(f"\n    Video IDs ({'first 10 of ' if total > 10 else ''}{total}):")
        for vid in result["video_ids"][:10]:
            print(f"      - {vid}")
        if total > 10:
            print(f"      ... and {total - 10} more")

    sys.exit(0)


if __name__ == "__main__":
    main()
