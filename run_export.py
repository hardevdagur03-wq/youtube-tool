"""Phase 6 entry point – Export transformed video data to CSV."""

import json
import logging
import sys
from pathlib import Path

from config.settings import ConfigurationError
from services.exporter import CSVExporter, CSVExporterError
from utils.logging_config import setup_logging

logger = logging.getLogger("run_export")


def main() -> None:
    setup_logging()

    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
        if not src.exists():
            logger.error("Input file not found: %s", src)
            print(f"\n[-] Error: file not found: {src}", file=sys.stderr)
            sys.exit(1)

        with open(src, encoding="utf-8") as f:
            records = json.load(f)
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            logger.error("No input data provided.")
            print("\n[-] Error: pipe JSON data or provide a file path.", file=sys.stderr)
            sys.exit(1)
        records = json.loads(raw)

    if not isinstance(records, list):
        logger.error("Input must be a JSON array.")
        print("\n[-] Error: input must be a JSON array of records.", file=sys.stderr)
        sys.exit(1)

    exporter = CSVExporter()

    try:
        result = exporter.export(records)
    except CSVExporterError as exc:
        logger.error("Export failed: %s", exc)
        print(f"\n[-] Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as exc:
        logger.critical("Configuration error: %s", exc)
        print(f"\n[-] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[+] Export complete!")
    print(f"    File      : {result['filepath']}")
    print(f"    Records   : {result['exported']} / {result['total_input']}")
    print(f"    Skipped   : {result['skipped']}")
    print(f"    Size      : {result['file_size_bytes']:,} bytes")
    sys.exit(0)


if __name__ == "__main__":
    main()
