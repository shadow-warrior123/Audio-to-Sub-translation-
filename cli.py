from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.core.config import settings
from app.core.logging import configure_logging
from app.pipeline.processor import process_video


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Offline Japanese video to English hard-sub pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="Process a single video")
    process_parser.add_argument("video", type=Path)
    process_parser.add_argument("--output-dir", type=Path, default=settings.output_dir)

    args = parser.parse_args()
    settings.ensure_directories()

    if args.command == "process":
        logging.info("Processing %s", args.video)
        outputs = process_video(args.video, args.output_dir, settings)
        print(f"SRT: {outputs.subtitle_path}")
        print(f"Video: {outputs.rendered_video_path}")


if __name__ == "__main__":
    main()

