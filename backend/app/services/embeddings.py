"""Embedding service for the recommender's semantic-similarity layer.

Wraps sentence-transformers/all-MiniLM-L6-v2 with a thin, testable API.
The module is import-light: ``sentence_transformers`` and ``torch`` are
imported lazily inside ``_get_encoder`` so code paths that don't touch
embeddings (most of the test suite, request handlers that don't need
For-You) don't pay the multi-second import cost.

The model is lazy-loaded once per process via ``_get_encoder``. With the
default ``uvicorn --workers 1`` this means one load total, which is
fine for our scale. Multi-worker production deployments would each load
their own copy (~150MB RAM each) — at that scale the right move is a
dedicated embedding worker behind a queue, but that's premature here.

For testing, ``set_encoder_for_testing`` lets you inject a fake encoder
so tests don't have to download the real model. See the test suite for
the pattern.
"""

from __future__ import annotations

import dataclasses
import math
import uuid
from collections.abc import Iterable
from typing import Any, Protocol

from app.models import Article

# Canonical model identifier. Changing this requires updating
# ``app.models.EMBEDDING_DIM`` and the migration that defines the
# ``articles.embedding`` column dimension.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Encoder loading and injection
# ---------------------------------------------------------------------------


class Encoder(Protocol):
    """Minimal interface our code uses against sentence-transformers.

    Defining this as a Protocol means tests can swap in a tiny fake (one
    method) without depending on the real library.
    """

    def encode(
        self,
        sentences: list[str] | str,
        *,
        normalize_embeddings: bool = True,
    ) -> Any: ...


# Module-level singleton. None until the first ``_get_encoder()`` call.
# Test code calls ``set_encoder_for_testing(...)`` to bypass real loading.
_encoder: Encoder | None = None


def _get_encoder() -> Encoder:
    """Lazy-load and cache the embedding model.

    Importing ``sentence_transformers`` triggers a torch import, which
    is heavy (~1s on cold start) and unnecessary for code paths that
    don't actually embed anything. Local-import inside this function
    keeps that cost off the module-load critical path.
    """
    global _encoder
    if _encoder is None:
        # Local import — see module docstring.
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(MODEL_NAME)
    return _encoder


def set_encoder_for_testing(encoder: Encoder | None) -> None:
    """Inject a fake encoder. Pass None to clear and force re-load on next use."""
    global _encoder
    _encoder = encoder


# ---------------------------------------------------------------------------
# Text composition
# ---------------------------------------------------------------------------


def article_embedding_text(article: Article) -> str:
    """Canonical text representation of an article for embedding.

    Order matters: sentence-transformers truncates to 256 tokens, so we
    put the most informative content first. Title is the headline signal,
    excerpt adds detail, then metadata as a short tail.

    Joining with periods rather than newlines because the transformer
    was trained on prose-like input, not structured fields. Empty fields
    are skipped to avoid leaving "Source: " floating in the input.
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
    # SentenceTransformer returns numpy. .tolist() works for both numpy
    # arrays and our test fakes that return plain lists.
    return vec.tolist() if hasattr(vec, "tolist") else list(vec)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-encode a list of strings.

    Roughly 5-10x faster than calling embed_text in a loop because the
    encoder can batch the GPU/CPU forward pass. Use this for backfill
    and any request that embeds more than ~3 articles at once.
    """
    if not texts:
        return []
    encoder = _get_encoder()
    vecs = encoder.encode(texts, normalize_embeddings=True)
    # Numpy arrays support iteration row-wise; list-of-list fakes work too.
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
    if not a or not b or len(a) != len(b):
        return 0.0
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
