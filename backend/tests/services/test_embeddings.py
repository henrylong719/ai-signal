"""Tests for the embedding service.

These tests deliberately don't make real HTTP calls to the embeddings
provider — that would slow the suite and require an API key in CI.
Instead a tiny fake encoder produces deterministic toy vectors that
exercise the library code paths (text composition, weighted averaging,
normalization, cosine) without involving real network IO.

The fake's behavior: the embedding for a string is a sparse vector with
one component per unique character class. Same string → same vector;
similar strings (sharing many characters) → similar vectors. That's
enough to write meaningful semantic-similarity assertions.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import pytest

from app.models import Article
from app.services import embeddings as emb

_DIM = 8


class FakeEncoder:
    """Deterministic toy encoder producing 8-dimensional vectors.

    Hashes each input character into one of 8 buckets and counts. Then
    optionally normalizes to unit length. Two strings with overlapping
    characters produce similar vectors; two strings with no overlap
    produce orthogonal-ish vectors.

    Uses ``ord()`` rather than ``hash()`` for character bucketing because
    Python randomizes ``hash()``'s seed across process starts (see
    PYTHONHASHSEED), which made earlier versions of this fake produce
    different vectors on different test runs and caused intermittent
    failures in the user-vector weighting test.
    """

    def __init__(self) -> None:
        self.encode_calls = 0

    def encode(
        self,
        sentences: list[str] | str,
        *,
        normalize_embeddings: bool = True,
    ) -> Any:
        self.encode_calls += 1
        if isinstance(sentences, str):
            return self._encode_one(sentences, normalize_embeddings)
        return [self._encode_one(s, normalize_embeddings) for s in sentences]

    def _encode_one(self, text: str, normalize: bool) -> list[float]:
        vec = [0.0] * _DIM
        for ch in text.lower():
            # ord() is deterministic across processes.
            vec[ord(ch) % _DIM] += 1.0
        if normalize:
            n = math.sqrt(sum(x * x for x in vec))
            if n > 0:
                vec = [x / n for x in vec]
        return vec


@pytest.fixture(autouse=True)
def _fake_encoder() -> Iterator[FakeEncoder]:
    """Inject a fake encoder for every test in this module.

    autouse=True so individual tests don't need to remember to do this —
    the module's whole point is bypassing real model loading.
    """
    fake = FakeEncoder()
    emb.set_encoder_for_testing(fake)
    try:
        yield fake
    finally:
        emb.set_encoder_for_testing(None)


def _article(
    *,
    title: str = "Sample article",
    excerpt: str | None = "This is the excerpt.",
    source: str = "AnthropicNews",
    category: str = "agents",
    tags: tuple[str, ...] = ("agents", "tools"),
) -> Article:
    """Compact Article factory. Just enough for embedding tests."""
    return Article(
        id=uuid.uuid4(),
        url=f"https://example.com/{uuid.uuid4()}",
        title=title,
        excerpt=excerpt,
        source=source,
        category=category,  # type: ignore[arg-type]
        tags=list(tags),
        published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Text composition
# ---------------------------------------------------------------------------


def test_article_embedding_text_includes_all_fields() -> None:
    article = _article(
        title="Sample article",
        excerpt="Excerpt text",
        source="Anthropic",
        category="rag",
        tags=("rag", "evals"),
    )
    text = emb.article_embedding_text(article)

    assert "Sample article" in text
    assert "Excerpt text" in text
    assert "Anthropic" in text
    assert "rag" in text
    assert "evals" in text


def test_article_embedding_text_omits_empty_excerpt() -> None:
    """Articles without excerpts shouldn't get a stray empty section."""
    article = _article(excerpt=None)
    text = emb.article_embedding_text(article)

    # No double-period suggesting a missing field.
    assert ".." not in text
    # Title still present, source still present.
    assert article.title in text
    assert article.source in text


def test_article_embedding_text_puts_title_first() -> None:
    """Titles must appear before metadata so they survive token truncation."""
    article = _article(title="UNIQUEHEADLINE", source="Source")
    text = emb.article_embedding_text(article)

    assert text.index("UNIQUEHEADLINE") < text.index("Source")


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def test_embed_text_returns_list_of_floats() -> None:
    vec = emb.embed_text("hello world")
    assert isinstance(vec, list)
    assert all(isinstance(x, float) for x in vec)
    assert len(vec) == _DIM


def test_embed_texts_batches_in_one_encoder_call(_fake_encoder: FakeEncoder) -> None:
    """The whole point of batch encoding is one model invocation, not N."""
    _fake_encoder.encode_calls = 0
    vecs = emb.embed_texts(["a", "b", "c", "d"])

    assert len(vecs) == 4
    assert _fake_encoder.encode_calls == 1


def test_embed_texts_handles_empty_input() -> None:
    """Empty list should return empty list without invoking the encoder."""
    assert emb.embed_texts([]) == []


def test_get_encoder_loads_once_under_concurrent_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent requests should share one lazy encoder construction."""
    init_calls: list[None] = []

    class FakeOpenAIEncoder(FakeEncoder):
        def __init__(self) -> None:
            super().__init__()
            init_calls.append(None)
            # Sleep so concurrent callers actually race the lock; without
            # it the first thread's construction finishes before the
            # others reach the double-checked branch.
            time.sleep(0.02)

    monkeypatch.setattr(emb, "_OpenAIEncoder", FakeOpenAIEncoder)
    emb.set_encoder_for_testing(None)

    barrier = threading.Barrier(8)
    results: list[emb.Encoder] = []

    def load_encoder() -> None:
        barrier.wait()
        results.append(emb._get_encoder())

    threads = [threading.Thread(target=load_encoder) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(init_calls) == 1
    assert len(results) == 8
    assert all(result is results[0] for result in results)


def test_embed_article_uses_composed_text() -> None:
    """End-to-end: an article with rich text gets encoded to a non-zero vector."""
    article = _article()
    vec = emb.embed_article(article)

    assert len(vec) == _DIM
    assert any(x != 0.0 for x in vec)


# ---------------------------------------------------------------------------
# User interest vector
# ---------------------------------------------------------------------------


def test_build_user_vector_returns_none_when_no_signal() -> None:
    """Cold-start users with no saves, clicks, or interests have no vector.

    The For-You service uses this to skip the semantic step entirely
    rather than compare against a meaningless zero vector.
    """
    result = emb.build_user_interest_vector(
        saved_article_embeddings=[],
        clicked_article_embeddings=[],
        interest_categories=[],
        interest_tags=[],
    )
    assert result is None


def test_build_user_vector_works_from_interests_alone() -> None:
    """Users with stated interests but no behavior should still get a vector."""
    result = emb.build_user_interest_vector(
        saved_article_embeddings=[],
        clicked_article_embeddings=[],
        interest_categories=["rag"],
        interest_tags=["evals"],
    )
    assert result is not None
    assert len(result) == _DIM


def test_build_user_vector_is_unit_normalized() -> None:
    """Cosine similarity assumes unit-length vectors — verify the contract."""
    saved = [emb.embed_text("rag pipelines"), emb.embed_text("retrieval")]
    result = emb.build_user_interest_vector(
        saved_article_embeddings=saved,
        clicked_article_embeddings=[],
        interest_categories=["rag"],
        interest_tags=[],
    )
    assert result is not None
    norm = math.sqrt(sum(x * x for x in result))
    assert abs(norm - 1.0) < 1e-9


def test_build_user_vector_weights_saved_above_clicked_and_stated() -> None:
    """A user whose saves point one direction and clicks another should
    end up closer to the saved direction. Tests the 3:2:1 weighting."""
    direction_a = emb.embed_text("aaa aaa aaa aaa")
    direction_b = emb.embed_text("zzz zzz zzz zzz")

    # Saved → A direction (heaviest weight)
    # Clicked → B direction
    # Stated → also B direction
    result = emb.build_user_interest_vector(
        saved_article_embeddings=[direction_a, direction_a],
        clicked_article_embeddings=[direction_b, direction_b],
        interest_categories=["zzz"],
        interest_tags=[],
    )
    assert result is not None

    sim_to_a = emb.cosine_similarity(result, direction_a)
    sim_to_b = emb.cosine_similarity(result, direction_b)
    # Saved weight (3) > clicked (2) + stated (1) combined, so the
    # result should align more with the saved direction.
    assert sim_to_a > sim_to_b


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def test_cosine_similarity_of_identical_vectors_is_one() -> None:
    v = [1.0, 0.0, 0.0]
    assert abs(emb.cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_of_orthogonal_vectors_is_zero() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(emb.cosine_similarity(a, b)) < 1e-9


def test_cosine_similarity_handles_zero_vector_safely() -> None:
    """Embeddings of empty input could be all-zero; don't divide by zero."""
    a = [1.0, 0.0, 0.0]
    z = [0.0, 0.0, 0.0]
    assert emb.cosine_similarity(a, z) == 0.0
    assert emb.cosine_similarity(z, a) == 0.0


def test_cosine_similarity_handles_empty_vectors_as_no_signal() -> None:
    assert emb.cosine_similarity([], [1.0, 0.0]) == 0.0
    assert emb.cosine_similarity([1.0, 0.0], []) == 0.0


def test_cosine_similarity_raises_on_mismatched_lengths() -> None:
    a = [1.0, 0.0]
    b = [1.0, 0.0, 0.0]

    with pytest.raises(ValueError, match="lengths 2 and 3"):
        emb.cosine_similarity(a, b)


def test_cosine_similarities_returns_one_score_per_article() -> None:
    user = emb.embed_text("rag")
    articles = {
        uuid.uuid4(): emb.embed_text("rag pipelines"),
        uuid.uuid4(): emb.embed_text("totally unrelated topic"),
    }
    sims = emb.cosine_similarities(user, articles)

    assert len(sims) == 2
    assert all(-1.0 <= s <= 1.0 for s in sims.values())


def test_cosine_similarities_propagates_dimension_mismatch() -> None:
    articles = {uuid.uuid4(): [1.0, 0.0, 0.0]}

    with pytest.raises(ValueError, match="lengths 2 and 3"):
        emb.cosine_similarities([1.0, 0.0], articles)


# ---------------------------------------------------------------------------
# Backfill orchestration
# ---------------------------------------------------------------------------
#
# These tests stub the CRUD layer rather than touch a real DB. The
# orchestrator's job is purely to drive the encoder and write back
# results — not to query Postgres — so DB-less tests cover the actual
# logic. Real-DB integration tests would belong in a separate suite
# marked @pytest.mark.integration.


class _FakeCrudModule:
    """Stand-in for ``app.crud`` that backfill_article_embeddings imports
    locally. Tracks calls and returns canned data per scenario."""

    def __init__(
        self,
        *,
        pending_batches: list[list[Article]],
        remaining_after: int = 0,
    ) -> None:
        self._pending_batches = list(pending_batches)
        self._remaining_after = remaining_after
        self.update_calls: list[dict[uuid.UUID, list[float]]] = []

    def get_pending_embedding_articles(
        self, *, session: Any, limit: int
    ) -> list[Article]:
        if not self._pending_batches:
            return []
        return self._pending_batches.pop(0)

    def update_article_embeddings(
        self, *, session: Any, embeddings: dict[uuid.UUID, list[float]]
    ) -> None:
        self.update_calls.append(embeddings)

    def count_pending_embeddings(self, *, session: Any) -> int:
        return self._remaining_after


def test_backfill_returns_zero_when_nothing_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCrudModule(pending_batches=[], remaining_after=0)
    monkeypatch.setattr(
        "app.crud.get_pending_embedding_articles", fake.get_pending_embedding_articles
    )
    monkeypatch.setattr(
        "app.crud.update_article_embeddings", fake.update_article_embeddings
    )
    monkeypatch.setattr(
        "app.crud.count_pending_embeddings", fake.count_pending_embeddings
    )

    report = emb.backfill_article_embeddings(session=object())

    assert report.processed == 0
    assert report.remaining == 0
    assert report.batches == 0
    # No work means no writes.
    assert fake.update_calls == []


def test_backfill_processes_one_full_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = [_article(title=f"Article {i}") for i in range(3)]
    fake = _FakeCrudModule(
        pending_batches=[articles],
        remaining_after=0,
    )
    monkeypatch.setattr(
        "app.crud.get_pending_embedding_articles", fake.get_pending_embedding_articles
    )
    monkeypatch.setattr(
        "app.crud.update_article_embeddings", fake.update_article_embeddings
    )
    monkeypatch.setattr(
        "app.crud.count_pending_embeddings", fake.count_pending_embeddings
    )

    report = emb.backfill_article_embeddings(session=object())

    assert report.processed == 3
    assert report.remaining == 0
    assert report.batches == 1
    # All three articles should have been written in one update call.
    assert len(fake.update_calls) == 1
    assert set(fake.update_calls[0].keys()) == {a.id for a in articles}
    # And each value is an 8-dim vector from our fake encoder.
    assert all(len(v) == _DIM for v in fake.update_calls[0].values())


def test_backfill_respects_max_batches_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded per call so an HTTP endpoint stays fast even with thousands
    of pending articles."""
    # Three batches available, but max_batches=2 should stop after two.
    batches = [[_article()], [_article()], [_article()]]
    fake = _FakeCrudModule(pending_batches=batches, remaining_after=1)
    monkeypatch.setattr(
        "app.crud.get_pending_embedding_articles", fake.get_pending_embedding_articles
    )
    monkeypatch.setattr(
        "app.crud.update_article_embeddings", fake.update_article_embeddings
    )
    monkeypatch.setattr(
        "app.crud.count_pending_embeddings", fake.count_pending_embeddings
    )

    report = emb.backfill_article_embeddings(session=object(), max_batches=2)

    assert report.batches == 2
    assert report.processed == 2
    # The third batch should still be queued — the fake's internal list
    # is a defensive copy, so we check it directly rather than the
    # caller's `batches` variable.
    assert len(fake._pending_batches) == 1


def test_backfill_stops_early_when_pending_runs_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If max_batches > available batches, we stop without an extra call."""
    fake = _FakeCrudModule(
        pending_batches=[[_article(), _article()]],
        remaining_after=0,
    )
    monkeypatch.setattr(
        "app.crud.get_pending_embedding_articles", fake.get_pending_embedding_articles
    )
    monkeypatch.setattr(
        "app.crud.update_article_embeddings", fake.update_article_embeddings
    )
    monkeypatch.setattr(
        "app.crud.count_pending_embeddings", fake.count_pending_embeddings
    )

    report = emb.backfill_article_embeddings(session=object(), max_batches=10)

    assert report.processed == 2
    assert report.batches == 1  # Stopped after the empty second poll.
