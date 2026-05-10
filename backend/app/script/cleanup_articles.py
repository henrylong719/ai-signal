"""CLI tool: run the safe two-stage article cleanup.

Run with:

    cd backend
    python -m app.script.cleanup_articles --dry-run     # default
    python -m app.script.cleanup_articles --apply

Dry-run is the default. ``--apply`` is the only switch that lets the
script actually write — even passing both flags resolves to dry-run
so a copy-paste from the dry-run shell history can't accidentally
hard-delete.

Prefer this script for the very first real cleanup on a fresh
deployment: run ``--dry-run`` once, eyeball the reported archive and
delete counts, and only then run ``--apply``.
"""

# Print to stdout is intentional in this CLI script — operator wants
# to read the result without tailing a log. T201 is meant for app code.
# ruff: noqa: T201

import argparse
import logging
import sys

from sqlmodel import Session

from app.core.db import engine
from app.services.article_cleanup import (
    ArticleCleanupResult,
    run_article_cleanup,
)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cleanup_articles",
        description="Archive then delete stale, unsaved, unengaged articles.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without making any DB changes (default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Actually archive and delete articles. Use only after dry-run.",
    )
    parser.add_argument(
        "--archive-after-days",
        type=int,
        default=None,
        help="Override ARTICLE_ARCHIVE_AFTER_DAYS for this run.",
    )
    parser.add_argument(
        "--delete-after-days",
        type=int,
        default=None,
        help="Override ARTICLE_DELETE_AFTER_DAYS for this run.",
    )
    parser.add_argument(
        "--keep-clicked-after-days",
        type=int,
        default=None,
        help="Override ARTICLE_KEEP_CLICKED_AFTER_DAYS for this run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override ARTICLE_CLEANUP_BATCH_SIZE for this run.",
    )
    return parser.parse_args()


def _print_summary(result: ArticleCleanupResult) -> None:
    print()
    print(f"  dry_run               : {result.dry_run}")
    print(f"  archive_cutoff (UTC)  : {result.archive_cutoff}")
    print(f"  delete_cutoff  (UTC)  : {result.delete_cutoff}")
    print(f"  keep_clicked_since    : {result.keep_clicked_since}")
    print(f"  archived rows         : {result.archived_count}")
    print(f"  deleted  rows         : {result.deleted_count}")
    if result.errors:
        print(f"  errors                : {len(result.errors)}")
        for err in result.errors:
            print(f"    - {err}")


def main() -> int:
    args = _parse_args()
    _setup_logging()

    # Safety: ``--apply`` is the only way to flip off dry-run. Anything
    # else (including no flag at all) stays dry-run.
    dry_run = not args.apply

    if dry_run:
        print("Running article cleanup in DRY-RUN mode (no writes).")
    else:
        print("Running article cleanup in APPLY mode (real writes!).")

    with Session(engine) as session:
        result = run_article_cleanup(
            session=session,
            dry_run=dry_run,
            archive_after_days=args.archive_after_days,
            delete_after_days=args.delete_after_days,
            keep_clicked_after_days=args.keep_clicked_after_days,
            batch_size=args.batch_size,
        )

    _print_summary(result)
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
