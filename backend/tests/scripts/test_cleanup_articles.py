"""Tests for the article-cleanup CLI.

The script's whole reason to exist is that it is safer than calling
``run_article_cleanup`` directly: dry-run is the default and ``--apply``
is the only way off it. These tests pin that safety property, the
pass-through of the tuning overrides, and the exit code contract that a
cron wrapper would key off.
"""

from unittest.mock import MagicMock

import pytest

from app.script import cleanup_articles
from app.services.article_cleanup import ArticleCleanupResult


def _patch_run(
    monkeypatch: pytest.MonkeyPatch,
    result: ArticleCleanupResult,
) -> dict[str, object]:
    """Stub run_article_cleanup, capturing the kwargs it was called with."""
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> ArticleCleanupResult:
        captured.update(kwargs)
        return result

    monkeypatch.setattr(cleanup_articles, "run_article_cleanup", fake_run)
    session = MagicMock()
    session.__enter__.return_value = session
    monkeypatch.setattr(cleanup_articles, "Session", lambda _engine: session)
    return captured


def _set_argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(cleanup_articles.sys, "argv", ["cleanup_articles", *args])


def test_defaults_to_dry_run_with_no_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No flags must never write. This is the script's core safety claim."""
    captured = _patch_run(monkeypatch, ArticleCleanupResult(dry_run=True))
    _set_argv(monkeypatch)

    exit_code = cleanup_articles.main()

    assert exit_code == 0
    assert captured["dry_run"] is True
    assert "DRY-RUN" in capsys.readouterr().out


def test_dry_run_flag_is_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_run(monkeypatch, ArticleCleanupResult(dry_run=True))
    _set_argv(monkeypatch, "--dry-run")

    cleanup_articles.main()

    assert captured["dry_run"] is True


def test_apply_is_the_only_way_to_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured = _patch_run(monkeypatch, ArticleCleanupResult(dry_run=False))
    _set_argv(monkeypatch, "--apply")

    cleanup_articles.main()

    assert captured["dry_run"] is False
    assert "APPLY" in capsys.readouterr().out


def test_dry_run_and_apply_together_is_rejected_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passing both flags must not reach a write.

    The module docstring says both flags "resolve to dry-run"; argparse's
    mutually exclusive group actually rejects the combination outright.
    Different mechanism, same guarantee — the point is that a copy-paste
    of both can never hard-delete, so that is what this asserts rather
    than the specific wording.
    """
    called = False

    def fake_run(**_kwargs: object) -> ArticleCleanupResult:
        nonlocal called
        called = True
        return ArticleCleanupResult()

    monkeypatch.setattr(cleanup_articles, "run_article_cleanup", fake_run)
    _set_argv(monkeypatch, "--dry-run", "--apply")

    with pytest.raises(SystemExit) as excinfo:
        cleanup_articles.main()

    assert excinfo.value.code == 2
    assert called is False


def test_tuning_overrides_are_passed_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_run(monkeypatch, ArticleCleanupResult())
    _set_argv(
        monkeypatch,
        "--archive-after-days",
        "10",
        "--delete-after-days",
        "20",
        "--keep-clicked-after-days",
        "30",
        "--batch-size",
        "40",
    )

    cleanup_articles.main()

    assert captured["archive_after_days"] == 10
    assert captured["delete_after_days"] == 20
    assert captured["keep_clicked_after_days"] == 30
    assert captured["batch_size"] == 40


def test_omitted_overrides_stay_none_so_settings_win(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """None means "defer to settings" — the script must not invent values."""
    captured = _patch_run(monkeypatch, ArticleCleanupResult())
    _set_argv(monkeypatch)

    cleanup_articles.main()

    assert captured["archive_after_days"] is None
    assert captured["delete_after_days"] is None
    assert captured["keep_clicked_after_days"] is None
    assert captured["batch_size"] is None


def test_exit_code_is_one_when_a_batch_errored(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Partial failures must surface to the shell, not just to stdout."""
    _patch_run(
        monkeypatch,
        ArticleCleanupResult(errors=["batch 3 blew up", "batch 7 blew up"]),
    )
    _set_argv(monkeypatch)

    exit_code = cleanup_articles.main()

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "errors                : 2" in out
    assert "batch 3 blew up" in out


def test_summary_reports_counts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_run(
        monkeypatch,
        ArticleCleanupResult(archived_count=12, deleted_count=3, dry_run=True),
    )
    _set_argv(monkeypatch)

    cleanup_articles.main()

    out = capsys.readouterr().out
    assert "archived rows         : 12" in out
    assert "deleted  rows         : 3" in out


def test_setup_logging_is_configured() -> None:
    """Smoke: the CLI configures logging without raising."""
    cleanup_articles._setup_logging()
