#!/usr/bin/env python3
"""CLI entry point for the Google Sheets feedback automation.

Usage:
    python main.py            # run the sync
    python main.py --dry-run  # preview without writing
    python main.py --engine rule   # force offline rewriting

Configuration is read from environment variables / a local .env file
(see .env.example). Exit code is non-zero if the run hit any errors.
"""

from __future__ import annotations

import argparse
import os
import sys

from feedback_sync.config import ConfigError, load_config
from feedback_sync.logging_setup import setup_logging
from feedback_sync.rewriter import build_rewriter
from feedback_sync.sheets import SheetsClient
from feedback_sync.workflow import FeedbackSyncWorkflow


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync & enhance student feedback.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the work without writing to the destination sheet.",
    )
    p.add_argument(
        "--engine",
        choices=["anthropic", "rule"],
        help="Override REWRITE_ENGINE for this run.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # CLI overrides take effect before config is loaded.
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
    if args.engine:
        os.environ["REWRITE_ENGINE"] = args.engine

    try:
        cfg = load_config()
    except ConfigError as exc:
        # Logging may not be set up yet; print plainly.
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    logger = setup_logging(cfg.log_level, cfg.log_file)
    logger.info(
        "Starting feedback sync (source tab=%r -> dest tab=%r, dry_run=%s).",
        cfg.source_worksheet_title or f"gid:{cfg.source_worksheet_gid}",
        cfg.dest_worksheet_title,
        cfg.dry_run,
    )

    try:
        client = SheetsClient(cfg)
        rewriter = build_rewriter(cfg)
        workflow = FeedbackSyncWorkflow(cfg, client, rewriter)
        result = workflow.run()
    except Exception:  # noqa: BLE001 - top-level guard so cron gets a clear code
        logger.exception("Fatal error during sync.")
        return 1

    if result.errors:
        logger.warning("Completed with %d row-level error(s).", result.errors)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
