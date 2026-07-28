"""API tests for the admin /ingest-runs endpoint.

Auth (anonymous and non-superuser rejection), happy path with seeded
runs, and the status filter.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app import crud
from app.core.config import settings
from app.models import IngestRun


def _seed_runs(db: Session) -> tuple[IngestRun, IngestRun, IngestRun]:
    """Create one succeeded, one failed, one running run.

    Returned in (succeeded, failed, running) order; the listing endpoint
    will return them most-recent-first by started_at, but since they
    were created in that physical order, the API response order is
    [running, failed, succeeded].
    """
    db.exec(delete(IngestRun))
    db.commit()

    succeeded = crud.start_ingest_run(session=db)
    crud.finish_ingest_run(
        session=db,
        run_id=succeeded.id,
        inserted=10,
        skipped=2,
        embedded=10,
        errors=[],
    )

    failed = crud.start_ingest_run(session=db)
    crud.fail_ingest_run(
        session=db, run_id=failed.id, error="ConnectionError: db unreachable"
    )

    running = crud.start_ingest_run(session=db)

    return succeeded, failed, running


def test_read_ingest_runs_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/admin/ingest-runs")
    # FastAPI returns 401 for missing auth on a Depends(get_current_user)
    # endpoint; the existing admin_embeddings tests assume the same shape.
    assert response.status_code == 401


def test_read_ingest_runs_requires_superuser(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_read_ingest_runs_returns_runs_most_recent_first(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, running = _seed_runs(db)

    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 3
    assert len(body["data"]) == 3

    # Most recent first — the running run was created last.
    assert body["data"][0]["id"] == str(running.id)
    assert body["data"][0]["status"] == "running"
    assert body["data"][0]["finished_at"] is None
    assert body["data"][0]["duration_ms"] is None
    assert body["data"][0]["errors"] == []

    # The failed run is in the middle.
    assert body["data"][1]["status"] == "failed"
    assert body["data"][1]["errors"] == ["ConnectionError: db unreachable"]

    # The succeeded run has counts populated.
    assert body["data"][2]["status"] == "succeeded"
    assert body["data"][2]["inserted"] == 10
    assert body["data"][2]["skipped"] == 2
    assert body["data"][2]["embedded"] == 10


def test_read_ingest_runs_filters_by_status(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    succeeded, _, _ = _seed_runs(db)

    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs?status=succeeded",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["id"] == str(succeeded.id)


def test_read_ingest_runs_filters_degraded_status(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    db.exec(delete(IngestRun))
    db.commit()
    degraded = crud.start_ingest_run(session=db)
    crud.finish_ingest_run(
        session=db,
        run_id=degraded.id,
        inserted=5,
        skipped=2,
        embedded=3,
        errors=["Example: fetch failed (ConnectTimeout)"],
    )

    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs?status=degraded",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["id"] == str(degraded.id)
    assert body["data"][0]["status"] == "degraded"


def test_read_ingest_runs_respects_limit(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _seed_runs(db)

    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs?limit=1",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_read_ingest_runs_empty(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    db.exec(delete(IngestRun))
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/admin/ingest-runs",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["data"] == []
