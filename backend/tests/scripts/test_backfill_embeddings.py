from unittest.mock import MagicMock

from app.script import backfill_embeddings
from app.services.embeddings import BackfillReport


def test_parse_args_uses_defaults(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(backfill_embeddings.sys, "argv", ["backfill_embeddings"])

    args = backfill_embeddings._parse_args()

    assert args.batch_size == 32
    assert args.max_articles is None


def test_main_stops_when_no_articles_remain(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    session = MagicMock()
    session.__enter__.return_value = session
    reports = [
        BackfillReport(processed=2, remaining=1, batches=1),
        BackfillReport(processed=0, remaining=0, batches=0),
    ]

    monkeypatch.setattr(
        backfill_embeddings,
        "_parse_args",
        lambda: backfill_embeddings.argparse.Namespace(
            batch_size=2,
            max_articles=None,
        ),
    )
    monkeypatch.setattr(backfill_embeddings, "_setup_logging", lambda: None)
    monkeypatch.setattr(backfill_embeddings, "_install_sigint_handler", lambda: None)
    monkeypatch.setattr(backfill_embeddings, "Session", lambda _engine: session)
    monkeypatch.setattr(
        backfill_embeddings,
        "backfill_article_embeddings",
        lambda **_kwargs: reports.pop(0),
    )

    result = backfill_embeddings.main()

    assert result == 0
    assert "Starting backfill (batch_size=2)." in capsys.readouterr().out


def test_main_stops_at_max_articles(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    session = MagicMock()
    session.__enter__.return_value = session

    monkeypatch.setattr(
        backfill_embeddings,
        "_parse_args",
        lambda: backfill_embeddings.argparse.Namespace(
            batch_size=3,
            max_articles=3,
        ),
    )
    monkeypatch.setattr(backfill_embeddings, "_setup_logging", lambda: None)
    monkeypatch.setattr(backfill_embeddings, "_install_sigint_handler", lambda: None)
    monkeypatch.setattr(backfill_embeddings, "Session", lambda _engine: session)
    monkeypatch.setattr(
        backfill_embeddings,
        "backfill_article_embeddings",
        lambda **_kwargs: BackfillReport(processed=3, remaining=9, batches=1),
    )

    result = backfill_embeddings.main()

    out = capsys.readouterr().out
    assert result == 0
    assert "Reached --max-articles=3 cap." in out
    assert "Done. Embedded 3 article(s) this run." in out
