"""Full end-to-end pipeline: Channel ID → CSV export."""

import logging
import sys
from config.settings import ConfigurationError
from services.video_discovery import VideoDiscovery, VideoDiscoveryError
from services.video_metadata import VideoMetadataService, VideoMetadataError
from services.data_transformer import DataTransformer, DataTransformerError
from services.exporter import CSVExporter, CSVExporterError
from utils.logging_config import setup_logging

logger = logging.getLogger("run_pipeline")


def main() -> None:
    setup_logging()

    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py CHANNEL_ID")
        sys.exit(1)

    channel_id = sys.argv[1]

    # Phase 3 – Discover
    print(f"\n{'='*60}")
    print("PHASE 3: Discovering all video IDs...")
    print(f"{'='*60}")
    discovery = VideoDiscovery()
    try:
        disc_result = discovery.discover(channel_id)
    except VideoDiscoveryError as exc:
        logger.critical("Discovery failed: %s", exc)
        print(f"\n[-] Discovery failed: {exc}", file=sys.stderr)
        sys.exit(1)
    video_ids = disc_result["video_ids"]
    print(f"  [OK] {len(video_ids)} videos discovered in {disc_result['total_requests']} requests")

    # Phase 4 – Metadata
    print(f"\n{'='*60}")
    print("PHASE 4: Fetching video metadata...")
    print(f"{'='*60}")
    meta_service = VideoMetadataService()
    try:
        meta_result = meta_service.fetch_metadata(video_ids)
    except VideoMetadataError as exc:
        logger.critical("Metadata fetch failed: %s", exc)
        print(f"\n[-] Metadata fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  [OK] {meta_result['total_retrieved']} records in {meta_result['total_requests']} requests")

    # Phase 5 – Transform
    print(f"\n{'='*60}")
    print("PHASE 5: Transforming data...")
    print(f"{'='*60}")
    transform_result = DataTransformer.transform(meta_result["videos"])
    print(f"  [OK] {transform_result['transformed']} transformed, {transform_result['skipped']} skipped")

    # Phase 6 – Export
    print(f"\n{'='*60}")
    print("PHASE 6: Exporting to CSV...")
    print(f"{'='*60}")
    exporter = CSVExporter()
    try:
        export_result = exporter.export(transform_result["videos"])
    except CSVExporterError as exc:
        logger.critical("Export failed: %s", exc)
        print(f"\n[-] Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as exc:
        logger.critical("Config error: %s", exc)
        print(f"\n[-] Config error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE!")
    print(f"{'='*60}")
    print(f"  File      : {export_result['filepath']}")
    print(f"  Videos    : {export_result['exported']}")
    print(f"  Skipped   : {export_result['skipped']}")
    print(f"  Size      : {export_result['file_size_bytes']:,} bytes")
    print(f"  API calls : {disc_result['total_requests'] + meta_result['total_requests']} total")


if __name__ == "__main__":
    main()
