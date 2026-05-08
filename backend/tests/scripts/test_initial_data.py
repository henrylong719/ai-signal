from unittest.mock import MagicMock

from app import initial_data


def test_init_opens_session_and_initializes_database(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session = MagicMock()
    session.__enter__.return_value = session
    init_db = MagicMock()

    monkeypatch.setattr(initial_data, "Session", lambda _engine: session)
    monkeypatch.setattr(initial_data, "init_db", init_db)

    initial_data.init()

    init_db.assert_called_once_with(session)


def test_main_logs_and_runs_init(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    init = MagicMock()
    info = MagicMock()

    monkeypatch.setattr(initial_data, "init", init)
    monkeypatch.setattr(initial_data.logger, "info", info)

    initial_data.main()

    init.assert_called_once_with()
    assert [call.args[0] for call in info.call_args_list] == [
        "Creating initial data",
        "Initial data created",
    ]
