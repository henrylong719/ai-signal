"""Embedding service for the recommender's semantic-similarity layer.

Calls the OpenAI Embeddings API (``text-embedding-3-small`` by default)
via an HTTP client. We previously ran ``sentence-transformers`` in-process,
which pinned ~2 GB of resident memory on the API container 24/7. Moving
to an external provider drops the API process to ~300-500 MB and the
cold-start cost from seconds to milliseconds.

Vectors are kept at 384 dimensions (via the OpenAI ``dimensions``
parameter) so the existing pgvector column doesn't need a schema change.
The catch is that vectors from different models aren't comparable — any
swap of ``OPENAI_EMBEDDING_MODEL`` requires re-embedding every article.

For testing, ``set_encoder_for_testing`` lets you inject a fake encoder
so tests don't have to make real HTTP calls. See the test suite for the
pattern.
"""

from __future__ import annotations

import dataclasses
import math
import threading
import uuid
from collections.abc import Iterable
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.models import Article

# ---------------------------------------------------------------------------
# Encoder loading and injection
# ---------------------------------------------------------------------------


class Encoder(Protocol):
    """Minimal interface our code uses against the embedding provider.

    Defining this as a Protocol means tests can swap in a tiny fake (one
    method) without depending on httpx or hitting the network.
    """

    def encode(
        self,
        sentences: list[str] | str,
        *,
        normalize_embeddings: bool = True,
    ) -> Any: ...


class _OpenAIEncoder:
    """Thin httpx wrapper around the OpenAI embeddings endpoint.

    The client is a long-lived ``httpx.Client`` — keeps the TLS
    connection pool warm so successive calls don't re-handshake. Reads
    its config from ``settings`` at construction so test fixtures that
    override the env vars take effect.

    The provider already returns L2-normalized vectors when ``dimensions``
    is supplied (Matryoshka truncation), but we re-normalize defensively
    so callers can rely on unit length regardless of provider quirks.
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; embeddings cannot be computed."
            )
        self._model = settings.OPENAI_EMBEDDING_MODEL
        self._dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS
        self._client = httpx.Client(
            base_url=settings.OPENAI_BASE_URL,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    def encode(
        self,
        sentences: list[str] | str,
        *,
        normalize_embeddings: bool = True,
    ) -> list[float] | list[list[float]]:
        single = isinstance(sentences, str)
        inputs = [sentences] if single else list(sentences)

        response = self._client.post(
            "/embeddings",
            json={
                "model": self._model,
                "input": inputs,
                "dimensions": self._dimensions,
            },
        )
        response.raise_for_status()
        payload = response.json()

        # OpenAI returns ``data`` in input order, but the documented
        # contract is "use the index field"; we sort to be safe.
        rows = sorted(payload["data"], key=lambda row: row["index"])
        vectors: list[list[float]] = [list(row["embedding"]) for row in rows]
        if normalize_embeddings:
            vectors = [_l2_normalize(v) for v in vectors]

        return vectors[0] if single else vectors


# Module-level singleton. None until the first ``_get_encoder()`` call.
# Test code calls ``set_encoder_for_testing(...)`` to bypass real loading.
_encoder: Encoder | None = None
_encoder_lock = threading.Lock()


def _get_encoder() -> Encoder:
    """Lazy-construct and cache the OpenAI encoder.

    Double-checked locking so concurrent first-callers share one client
    rather than each spinning up their own pool. After construction the
    encoder is reused for the lifetime of the process.
    """
    global _encoder
    if _encoder is None:
        with _encoder_lock:
            if _encoder is None:
                _encoder = _OpenAIEncoder()
    return _encoder


def set_encoder_for_testing(encoder: Encoder | None) -> None:
    """Inject a fake encoder. Pass None to clear and force re-load on next use."""
    global _encoder
    with _encoder_lock:
        _encoder = encoder


# ---------------------------------------------------------------------------
# Text composition
# ---------------------------------------------------------------------------


def article_embedding_text(article: Article) -> str:
    """Canonical text representation of an article for embedding.

    Order matters: the provider truncates long inputs, so we put the
    most informative content first. Title is the headline signal,
    excerpt adds detail, then metadata as a short tail.

    Joining with periods rather than newlines because the embedding
    model was trained on prose-like input, not structured fields. Empty
    fields are skipped to avoid leaving "Source: " floating in the input.
    """
    parts: list[str] = [article.title.strip()]
    if article.excerpt:
        parts.append(article.excerpt.strip())
    parts.append(f"Source: {article.source}")
    parts.append(f"Category: {article.category}")
    if article.tags:
        parts.append(f"Tags: {', '.join(article.tags)}")
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def embed_text(text: str) -> list[float]:
    """Encode a single string. Use ``embed_texts`` for batches — much faster."""
    encoder = _get_encoder()
    vec = encoder.encode(text, normalize_embeddings=True)
    # ``tolist()`` covers any numpy-returning fakes left in tests; the
    # production OpenAI encoder already returns plain lists.
    return vec.tolist() if hasattr(vec, "tolist") else list(vec)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-encode a list of strings.

    Materially faster than calling ``embed_text`` in a loop because
    the whole batch goes in a single HTTP round-trip. Use this for
    backfill and any request that embeds more than ~3 articles at once.
    """
    if not texts:
        return []
    encoder = _get_encoder()
    vecs = encoder.encode(texts, normalize_embeddings=True)
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vecs]


def embed_article(article: Article) -> list[float]:
    """Compose article text and embed it. One-shot convenience."""
    return embed_text(article_embedding_text(article))


# ---------------------------------------------------------------------------
# User interest vector
# ---------------------------------------------------------------------------


# Weights for combining the three user-vector components. Mirrors the
# explicit-match-score weighting in the recommender (saves > clicks >
# stated interests) so semantic and explicit signals tell a consistent
# story about user preferences.
_W_SAVED = 3.0
_W_CLICKED = 2.0
_W_STATED = 1.0


def _interest_text(
    interest_categories: Iterable[str], interest_tags: Iterable[str]
) -> str | None:
    """Compose stated interests into one embeddable sentence, or None.

    Format mirrors article_embedding_text so the user's interest vector
    lives in the same semantic neighborhood as articles about those
    same topics.
    """
    cats = list(interest_categories)
    tags = list(interest_tags)
    if not cats and not tags:
        return None
    parts = []
    if cats:
        parts.append(f"Topics of interest: {', '.join(cats)}")
    if tags:
        parts.append(f"Specific interests: {', '.join(tags)}")
    return ". ".join(parts)


def build_user_interest_vector(
    *,
    saved_article_embeddings: list[list[float]],
    clicked_article_embeddings: list[list[float]],
    interest_categories: Iterable[str],
    interest_tags: Iterable[str],
) -> list[float] | None:
    """Weighted combination of three user-signal embeddings, unit-normalized.

    Returns None when the user has no signal at all — the For-You service
    uses this to decide whether to skip the semantic-similarity step.

    Weights match the recommender's explicit-match scoring (saved 3,
    clicked 2, stated 1). Each input vector is presumed already
    unit-normalized (which is what our embed_* functions return); we
    re-normalize the final combined vector so cosine similarity against
    article embeddings stays in [-1, 1].
    """
    components: list[tuple[float, list[float]]] = []

    if saved_article_embeddings:
        # Average the saved-article embeddings, then weight the average.
        # This means a user with 100 saves contributes the same magnitude
        # as a user with 5 — what matters is the centroid direction, not
        # how many examples produced it.
        avg = _average_vectors(saved_article_embeddings)
        components.append((_W_SAVED, avg))
    if clicked_article_embeddings:
        avg = _average_vectors(clicked_article_embeddings)
        components.append((_W_CLICKED, avg))

    interest_text = _interest_text(interest_categories, interest_tags)
    if interest_text is not None:
        # Stated interests are a single text — embed and weight.
        stated_vec = embed_text(interest_text)
        components.append((_W_STATED, stated_vec))

    if not components:
        return None

    # Weighted sum of unit vectors. The result is generally not unit-length
    # (it would be only if all components pointed exactly the same direction
    # and weights summed to 1), so we re-normalize at the end.
    total_weight = sum(w for w, _ in components)
    dim = len(components[0][1])
    accum = [0.0] * dim
    for weight, vec in components:
        scale = weight / total_weight
        for i in range(dim):
            accum[i] += scale * vec[i]
    return _l2_normalize(accum)


# ---------------------------------------------------------------------------
# Vector math (kept simple — numpy is overkill for this volume)
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1]. Works on any-magnitude inputs."""
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        raise ValueError(
            f"Cannot compute cosine similarity for vectors with lengths "
            f"{len(a)} and {len(b)}"
        )
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def cosine_similarities(
    user_vec: list[float], article_vecs: dict[uuid.UUID, list[float]]
) -> dict[uuid.UUID, float]:
    """Batch cosine similarity for a user vector against many articles.

    Returns a {article_id: similarity} dict in [-1, 1] range. The For-You
    scorer further clamps this to [0, 1] before mixing with other signals
    — negative similarity (semantically opposite) is treated as zero
    rather than as a penalty, because penalizing semantic mismatch
    interacts unintuitively with the other signals.
    """
    return {
        article_id: cosine_similarity(user_vec, article_vec)
        for article_id, article_vec in article_vecs.items()
    }


def _average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    accum = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            accum[i] += v[i]
    return [x / len(vectors) for x in accum]


def _l2_normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]


# ---------------------------------------------------------------------------
# Cache write path — called from every endpoint that changes user signal
# ---------------------------------------------------------------------------


def compute_and_save_user_vector(
    *,
    session: Any,  # sqlmodel.Session — Any to avoid the import here
    user_id: uuid.UUID,
) -> list[float] | None:
    """Recompute the user's interest vector and write it to the cache.

    Called from every write path that affects what the recommender thinks
    the user wants:
      - PUT /users/me/interests
      - POST /articles/{id}/save
      - DELETE /articles/{id}/save
      - GET /articles/{id}/go (the click-tracking redirect)

    Returns the new vector (or None if the user has no signal yet — see
    ``build_user_interest_vector``). The cache row is upserted on
    success and removed on None — keeping a stale vector after the user
    cleared all their signal would be misleading.

    Local imports for ``app.crud`` and ``app.models`` avoid circular
    imports at module load: this services module is imported by the
    recommender, which is imported by route handlers, which import crud.
    The crud package importing this module would close the loop.
    """
    from app import crud
    from app.models import UserEmbedding

    interests = crud.get_interests(session=session, user_id=user_id)
    saved_embeddings = crud.get_saved_article_embeddings(
        session=session, user_id=user_id
    )
    clicked_embeddings = crud.get_clicked_article_embeddings(
        session=session, user_id=user_id
    )

    vector = build_user_interest_vector(
        saved_article_embeddings=saved_embeddings,
        clicked_article_embeddings=clicked_embeddings,
        interest_categories=interests.categories if interests else [],
        interest_tags=interests.tags if interests else [],
    )

    if vector is None:
        # No signal at all — drop any stale cache row rather than keeping
        # outdated data. The For-You service treats this as cold-start.
        existing = session.get(UserEmbedding, user_id)
        if existing is not None:
            session.delete(existing)
            session.commit()
        return None

    crud.upsert_user_embedding(session=session, user_id=user_id, embedding=vector)
    return vector


# ---------------------------------------------------------------------------
# Backfill — populate articles.embedding for existing rows
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BackfillReport:
    """What one call to ``backfill_article_embeddings`` actually did.

    ``processed`` and ``remaining`` together let the caller decide
    whether to call again. The CLI script loops while remaining > 0;
    the HTTP endpoint just returns the numbers and lets the operator
    re-call manually.
    """

    processed: int
    remaining: int
    batches: int


def backfill_article_embeddings(
    *,
    session: Any,  # sqlmodel.Session — see compute_and_save_user_vector
    batch_size: int = 32,
    max_batches: int = 4,
) -> BackfillReport:
    """Encode the next chunk of articles missing embeddings.

    Bounded by ``max_batches * batch_size`` per call so the function is
    safe to call from an HTTP endpoint without timing out. Operators
    handle "embed everything" by calling this in a loop (see the CLI
    script in ``app.scripts.backfill_embeddings``).

    Per-batch commits, not per-call: if an encode fails on batch 3 of
    4, the first two batches' work is durably saved. The exception
    propagates so the caller knows something went wrong.

    Concurrency note: see ``crud.get_pending_embedding_articles`` for
    why we don't lock rows. Two processes running this concurrently
    may re-encode the same article. Wasted work, not corruption.
    """
    from app import crud  # local import — see compute_and_save_user_vector

    processed = 0
    batches_run = 0

    for _ in range(max_batches):
        articles = list(
            crud.get_pending_embedding_articles(session=session, limit=batch_size)
        )
        if not articles:
            break

        # Compose all texts first, then batch-encode in one model call.
        # ``embed_texts`` is materially faster than calling ``embed_text``
        # in a loop because the encoder batches the forward pass.
        texts = [article_embedding_text(article) for article in articles]
        vectors = embed_texts(texts)

        embeddings_by_id = {
            article.id: vec for article, vec in zip(articles, vectors, strict=True)
        }
        crud.update_article_embeddings(session=session, embeddings=embeddings_by_id)

        processed += len(articles)
        batches_run += 1

    remaining = crud.count_pending_embeddings(session=session)
    return BackfillReport(processed=processed, remaining=remaining, batches=batches_run)
