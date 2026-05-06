"""CLI tool: embed all articles that don't yet have an embedding.

Run with:

    uv run python -m app.scripts.backfill_embeddings [--batch-size N] \
                                                    [--max-articles N]

The script loops calling ``backfill_article_embeddings`` until no
pending rows remain or ``--max-articles`` is reached. Progress is
printed to stdout. Ctrl+C is caught so an operator can stop early
without an ugly traceback.

For ad-hoc small runs from a logged-in admin browser session, prefer
the HTTP endpoint ``POST /admin/embed-articles`` instead — same core
logic, no shell access needed.
"""

# Print to stdout is intentional in this CLI script — that's how the
# operator sees progress. The T201 ruff rule is meant for app code.
# ruff: noqa: T201

import argparse
import logging
import signal
import sys
from typing import Any

from sqlmodel import Session

from app.core.db import engine
from app.services.embeddings import (
    BackfillReport,
    backfill_article_embeddings,
)


def _setup_logging() -> None:
    """Print INFO+ logs from app code so the operator sees what's happening
    inside the embedding pipeline (e.g., model loading)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _install_sigint_handler() -> None:
    """Convert Ctrl+C to a clean exit so the operator doesn't see a
    KeyboardInterrupt traceback after pressing Ctrl+C."""

    def handler(_signum: int, _frame: Any) -> None:
        print("\n\nInterrupted. Partial backfill is durable — re-run to continue.")
        sys.exit(130)  # 128 + SIGINT

    signal.signal(signal.SIGINT, handler)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="backfill_embeddings",
        description="Compute and store embeddings for articles missing them.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Articles encoded per batch (default: 32).",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help=(
            "Cap on the total number of articles processed in this run. "
            "Default: process until none remain."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _setup_logging()
    _install_sigint_handler()

    total_processed = 0

    print(f"Starting backfill (batch_size={args.batch_size}).")

    with Session(engine) as session:
        while True:
            # Each iteration runs at most ``batch_size`` articles —
            # we let backfill_article_embeddings own the per-call cap
            # so we can match the HTTP endpoint's behavior exactly.
            report: BackfillReport = backfill_article_embeddings(
                session=session,
                batch_size=args.batch_size,
                max_batches=1,
            )

            total_processed += report.processed
            if report.processed == 0:
                # Nothing left to do (or the model returned nothing).
                break

            print(
                f"  +{report.processed} embedded, "
                f"{report.remaining} remaining "
                f"(total this run: {total_processed})"
            )

            if args.max_articles is not None and total_processed >= args.max_articles:
                print(f"Reached --max-articles={args.max_articles} cap.")
                break

    print(f"\nDone. Embedded {total_processed} article(s) this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
