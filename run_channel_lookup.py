"""Phase 2 entry point – Resolve a YouTube channel handle to a channel ID."""

import logging
import sys

from config.settings import settings, ConfigurationError
from services.channel_resolver import (
    ChannelResolver,
    InvalidHandleError,
    ChannelResolverError,
)
from utils.logging_config import setup_logging

logger = logging.getLogger("run_channel_lookup")


def main() -> None:
    setup_logging()

    if len(sys.argv) > 1:
        raw_handle = " ".join(sys.argv[1:])
    else:
        raw_handle = input("Enter YouTube channel handle (e.g. @channel): ").strip()

    resolver = ChannelResolver()

    try:
        result = resolver.resolve(raw_handle)
    except InvalidHandleError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n[-] Invalid handle: {exc}", file=sys.stderr)
        sys.exit(1)
    except ChannelResolverError as exc:
        logger.error("Resolution failed: %s", exc)
        print(f"\n[-] Lookup failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as exc:
        logger.critical("Configuration error: %s", exc)
        print(f"\n[-] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n[+] Channel lookup successful!")
    print(f"    Channel ID : {result['channel_id']}")
    print(f"    Title      : {result['title']}")
    print(f"    Handle     : {result['handle']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
