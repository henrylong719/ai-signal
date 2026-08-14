from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app import crud as app_crud
from app.models import Article
from app.services import for_you, ranking
from app.services.recommender import UserProfile

NOW = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)


def _article(
    *,
    title: str,
    category: str = "models",
    source: str = "Example",
    tags: list[str] | None = None,
    age_days: int = 0,
) -> Article:
    return Article(
        id=uuid4(),
        url=f"https://example.com/{uuid4()}",
        title=title,
        source=source,
        excerpt="excerpt",
        category=category,
        tags=tags or [category],
        published_at=NOW - timedelta(days=age_days),
    )


def test_build_user_profile_aggregates_all_recommendation_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    saved_id = uuid4()
    dismissed_id = uuid4()
    interests = SimpleNamespace(
        categories=["agents"],
        tags=["tool-use"],
        preferred_sources=["OpenAI", "Anthropic"],
    )

    monkeypatch.setattr(
        app_crud,
        "get_interests",
        lambda *, session, user_id: interests,
    )
    monkeypatch.setattr(
        app_crud,
        "get_saved_signals",
        lambda *, session, user_id: ({"evals": 1.0}, {"OpenAI": 1.0}),
    )
    monkeypatch.setattr(
        app_crud,
        "get_clicked_signals",
        lambda *, session, user_id: ({"rag": 1.0}, {"LangChain": 1.0}),
    )
    monkeypatch.setattr(
        app_crud,
        "get_saved_article_ids",
        lambda *, session, user_id: [saved_id],
    )
    monkeypatch.setattr(
        app_crud,
        "get_event_article_ids",
        lambda *, session, user_id, event_type: [dismissed_id],
    )

    fake_session: Any = object()

    profile = for_you.build_user_profile(session=fake_session, user_id=user_id)

    assert profile == UserProfile(
        interest_categories=frozenset({"agents"}),
        interest_tags=frozenset({"tool-use"}),
        preferred_sources=frozenset({"OpenAI", "Anthropic"}),
        saved_tags={"evals": 1.0},
        saved_sources={"OpenAI": 1.0},
        clicked_tags={"rag": 1.0},
        clicked_sources={"LangChain": 1.0},
        saved_article_ids=frozenset({saved_id}),
        dismissed_article_ids=frozenset({dismissed_id}),
    )


def test_build_user_profile_drops_retired_preferred_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retired names must not reach the ranker.

    A retired source's articles outlive its removal from SOURCES, so an
    unfiltered name here keeps boosting them and emits a "Because you
    follow 3Blue1Brown" reason for a source the Sources UI no longer
    shows as followed.
    """
    interests = SimpleNamespace(
        categories=[],
        tags=[],
        preferred_sources=["3Blue1Brown", "OpenAI"],
    )
    monkeypatch.setattr(app_crud, "get_interests", lambda **kwargs: interests)
    monkeypatch.setattr(app_crud, "get_saved_signals", lambda **kwargs: ({}, {}))
    monkeypatch.setattr(app_crud, "get_clicked_signals", lambda **kwargs: ({}, {}))
    monkeypatch.setattr(app_crud, "get_saved_article_ids", lambda **kwargs: [])
    monkeypatch.setattr(app_crud, "get_event_article_ids", lambda **kwargs: [])

    fake_session: Any = object()

    profile = for_you.build_user_profile(session=fake_session, user_id=uuid4())

    assert profile.preferred_sources == frozenset({"OpenAI"})


def test_build_user_profile_treats_missing_interests_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_crud, "get_interests", lambda **kwargs: None)
    monkeypatch.setattr(
        app_crud,
        "get_saved_signals",
        lambda **kwargs: ({}, {}),
    )
    monkeypatch.setattr(
        app_crud,
        "get_clicked_signals",
        lambda **kwargs: ({}, {}),
    )
    monkeypatch.setattr(app_crud, "get_saved_article_ids", lambda **kwargs: [])
    monkeypatch.setattr(app_crud, "get_event_article_ids", lambda **kwargs: [])

    fake_session: Any = object()

    profile = for_you.build_user_profile(session=fake_session, user_id=uuid4())

    assert profile == UserProfile()


def test_rank_for_you_excludes_negative_signals_and_paginates_after_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    saved = _article(title="Saved", category="rag", tags=["rag"], age_days=0)
    dismissed = _article(title="Dismissed", category="rag", tags=["rag"], age_days=0)
    strongest = _article(title="Best match", category="rag", tags=["rag"], age_days=3)
    fresh = _article(title="Fresh but generic", category="other", tags=[], age_days=0)
    old_match = _article(title="Older match", category="rag", tags=["rag"], age_days=20)
    captured_excluded: set[object] = set()

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            interest_categories=frozenset({"rag"}),
            interest_tags=frozenset({"rag"}),
            saved_article_ids=frozenset({saved.id}),
            dismissed_article_ids=frozenset({dismissed.id}),
        ),
    )

    def fake_candidates(**kwargs: object) -> list[Article]:
        excluded_ids = kwargs["excluded_ids"]
        limit = kwargs["limit"]
        assert isinstance(excluded_ids, set)
        captured_excluded.update(excluded_ids)
        assert limit == 200
        # Include saved/dismissed defensively; rank_for_you should filter them
        # even if the DB helper returned stale data.
        return [fresh, old_match, saved, dismissed, strongest]

    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        fake_candidates,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()

    items, total = for_you.rank_for_you(
        session=fake_session,
        user_id=user_id,
        skip=1,
        limit=1,
    )

    assert captured_excluded == {saved.id, dismissed.id}
    assert total == 3
    assert [item.scored.article.title for item in items] == ["Older match"]
    assert items[0].reason == "Because you follow RAG"


def test_rank_for_you_applies_diversity_rerank_to_large_pools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the candidate pool is large enough to trigger the
    diversity reranker, a single source's burst should not occupy the
    head of the For-You feed.

    This guards against regression of the integration between
    score_candidates and diversity_rerank in rank_for_you.
    """
    user_id = uuid4()

    # 50 articles from one bursty source, 50 from a mix of others.
    # All match the user's stated interest so they rank similarly on
    # the explicit-match component — without diversity reranking, the
    # bursty source would fill the head purely by recency.
    bursty: list[Article] = []
    for i in range(50):
        bursty.append(
            _article(
                title=f"Bursty {i}",
                category="rag",
                source="arXiv",
                tags=["rag"],
                age_days=0,
            )
        )
    others: list[Article] = []
    for i in range(50):
        others.append(
            _article(
                title=f"Other {i}",
                category="rag",
                source=f"source{i % 5}",
                tags=["rag"],
                age_days=1,  # slightly older — bursty would otherwise dominate
            )
        )
    all_articles = bursty + others

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            interest_categories=frozenset({"rag"}),
            interest_tags=frozenset({"rag"}),
        ),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: all_articles,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=20
    )

    head_sources = [item.scored.article.source for item in items]
    bursty_count = sum(1 for s in head_sources if s == "arXiv")
    distinct_sources = len(set(head_sources))

    # Without rerank, all 20 head positions would be arXiv. With rerank,
    # the burst is broken up.
    assert bursty_count < 12, (
        f"arXiv took {bursty_count}/20 of the For-You head — rerank not firing"
    )
    assert distinct_sources >= 4, (
        f"only {distinct_sources} distinct sources in For-You head"
    )


# ---------------------------------------------------------------------------
# _most_similar_saved_titles — pairwise candidate↔saved-article lookup
# powering the "Similar to: <title>" reason label.
# ---------------------------------------------------------------------------


def _article_with_embedding(
    *, title: str, embedding: list[float], age_days: int = 0, **kwargs: object
) -> Article:
    """Article fixture with an explicit embedding for similarity tests."""
    article = _article(title=title, age_days=age_days, **kwargs)  # type: ignore[arg-type]
    # Article.embedding is a pgvector field; in unit tests we just set it
    # directly. The helper reads it via getattr.
    object.__setattr__(article, "embedding", embedding)
    return article


def test_most_similar_saved_titles_picks_highest_cosine_match() -> None:
    """For each candidate, returns the saved-article title with the
    highest cosine similarity. Constructed so each candidate has an
    obvious nearest save."""
    saved_a = (uuid4(), "Saved A — about FSDP", [1.0, 0.0, 0.0])
    saved_b = (uuid4(), "Saved B — about RAG", [0.0, 1.0, 0.0])
    saved_c = (uuid4(), "Saved C — about agents", [0.0, 0.0, 1.0])

    candidate_near_a = _article_with_embedding(
        title="cand-a", embedding=[0.95, 0.1, 0.05]
    )
    candidate_near_b = _article_with_embedding(
        title="cand-b", embedding=[0.05, 0.9, 0.1]
    )

    result = for_you._most_similar_saved_titles(
        db_articles=[candidate_near_a, candidate_near_b],
        saved=[saved_a, saved_b, saved_c],
    )

    assert result[candidate_near_a.id] == "Saved A — about FSDP"
    assert result[candidate_near_b.id] == "Saved B — about RAG"


def test_most_similar_saved_titles_returns_empty_when_no_saves() -> None:
    """No saved articles with embeddings — empty map. Used by the
    no-saves cold-start path; the caller falls back to the generic
    semantic label for those candidates."""
    candidate = _article_with_embedding(title="c", embedding=[1.0, 0.0])

    assert for_you._most_similar_saved_titles(db_articles=[candidate], saved=[]) == {}


def test_most_similar_saved_titles_skips_candidates_without_embeddings() -> None:
    """Candidates without embeddings can't be compared, so they're
    absent from the result. The reason_for caller treats absence as
    "no personalized title available" and uses the generic label."""
    no_emb = _article(title="no-emb")  # no embedding set at all
    has_emb = _article_with_embedding(title="has-emb", embedding=[1.0, 0.0])

    saved = [(uuid4(), "Saved", [1.0, 0.0])]

    result = for_you._most_similar_saved_titles(
        db_articles=[no_emb, has_emb], saved=saved
    )

    assert no_emb.id not in result
    assert result[has_emb.id] == "Saved"


def test_rank_for_you_personalizes_semantic_reason_with_saved_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: when the semantic component dominates the score and
    the user has a saved article close to the candidate, the For-You
    item's reason label points at the specific saved article rather
    than the generic phrasing."""
    user_id = uuid4()

    # User has no explicit interests/tags — so the only signal is
    # semantic. Recency is also low (30 days old) so semantic dominates.
    saved_id = uuid4()
    saved_title = "How we trained a 70B model on 4 H100s using FSDP"
    candidate_title = "Distributed training of large language models"

    candidate = _article_with_embedding(
        title=candidate_title, embedding=[1.0, 0.0, 0.0], age_days=30
    )

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            saved_article_ids=frozenset({saved_id}),
        ),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: [candidate],
    )
    # Cached user vector exists and aligns with the candidate (cosine = 1.0).
    monkeypatch.setattr(
        app_crud,
        "get_user_embedding",
        lambda **kwargs: SimpleNamespace(embedding=[1.0, 0.0, 0.0]),
    )
    # And the user has one saved article whose embedding is also aligned —
    # so the pairwise lookup will return it as the closest match.
    monkeypatch.setattr(
        app_crud,
        "get_saved_articles_with_embeddings_and_titles",
        lambda **kwargs: [(saved_id, saved_title, [1.0, 0.0, 0.0])],
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=10
    )

    assert len(items) == 1
    # The reason label points at the specific saved article (truncated
    # if needed) rather than the generic "Similar to articles you saved".
    reason = items[0].reason
    assert reason is not None
    assert reason.startswith("Similar to: ")
    # The saved title is 48 chars; budget is 50, so it should pass through
    # untruncated.
    assert reason == f"Similar to: {saved_title}"


def test_rank_for_you_falls_back_to_generic_label_when_user_has_no_saves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user with explicit interests + clicks but no saves can still
    have semantic dominance (the user vector is built from clicks +
    interest text). In that case there's no saved title to point at,
    so the semantic branch falls back to the generic label."""
    user_id = uuid4()
    candidate = _article_with_embedding(
        title="Some article", embedding=[1.0, 0.0, 0.0], age_days=30
    )

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: [candidate],
    )
    monkeypatch.setattr(
        app_crud,
        "get_user_embedding",
        lambda **kwargs: SimpleNamespace(embedding=[1.0, 0.0, 0.0]),
    )
    # No saves with embeddings — empty list.
    monkeypatch.setattr(
        app_crud,
        "get_saved_articles_with_embeddings_and_titles",
        lambda **kwargs: [],
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=10
    )

    assert len(items) == 1
    assert items[0].reason == "Similar to articles you saved"


def test_rank_for_you_skips_saved_lookup_when_user_has_no_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cold-start path: no user vector, no embeddings fetched, no
    saved-with-titles fetched. Verifies we don't hit the new CRUD
    when there's no semantic signal to label."""
    user_id = uuid4()
    candidate = _article_with_embedding(title="Some article", embedding=[1.0, 0.0, 0.0])

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: [candidate],
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    saved_lookup_called = False

    def boom(**kwargs: object) -> object:
        nonlocal saved_lookup_called
        saved_lookup_called = True
        return []

    monkeypatch.setattr(
        app_crud,
        "get_saved_articles_with_embeddings_and_titles",
        boom,
    )

    fake_session: Any = object()
    for_you.rank_for_you(session=fake_session, user_id=user_id, skip=0, limit=10)

    assert not saved_lookup_called, (
        "saved-titles lookup should be skipped when the user has no vector"
    )


# ---------------------------------------------------------------------------
# Exploration injection — reserves ~14% of slots for "outside your bubble"
# items so the feed doesn't compound into a narrow filter bubble.
# ---------------------------------------------------------------------------


def test_rank_for_you_injects_exploration_items_with_dedicated_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: pool with both personalized and outside-profile articles
    should produce a feed where some items carry the exploration label.

    The user has stated interest "rag". We feed in 25 rag-tagged
    articles (which will match explicitly) and 15 unrelated articles
    from sources/categories the user has zero signal for. The
    exploration step should pull some of the unrelated items into
    fixed slots and label them "Outside your usual interests".
    """
    user_id = uuid4()

    matching = [
        _article(
            title=f"Rag {i}",
            category="rag",
            source=f"RagSrc{i % 3}",
            tags=["rag"],
            age_days=1,
        )
        for i in range(25)
    ]
    # Outside-profile: different category, different sources, no
    # overlapping tags. Fresher than the matching articles so they
    # rank well on recency alone (which is what makes them eligible
    # for the exploration pool — exploration items are pure recency).
    outside = [
        _article(
            title=f"Outside {i}",
            category="hardware",  # not in user's interest_categories
            source=f"OutsideSrc{i % 5}",
            tags=["gpu"],  # not in user's interest_tags
            age_days=0,
        )
        for i in range(15)
    ]
    all_articles = matching + outside

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            interest_categories=frozenset({"rag"}),
            interest_tags=frozenset({"rag"}),
        ),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: all_articles,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=40
    )

    exploration_items = [
        it for it in items if it.reason == "Outside your usual interests"
    ]
    # 40-item page: slots at positions 2, 9, 16, 23, 30, 37 → 6 slots.
    # Pool has 15 exploration candidates available, so all 6 should
    # fill (we have plenty of pool to draw from).
    assert len(exploration_items) >= 4, (
        f"expected ~6 exploration slots filled, got {len(exploration_items)}"
    )
    # And every exploration item should actually be an outside-profile
    # article (its category/source/tags should not match the user's
    # interests).
    for it in exploration_items:
        article = it.scored.article
        assert article.category == "hardware"
        assert "rag" not in article.tags


def test_rank_for_you_skips_exploration_for_cold_start_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user with no signal at all should see no exploration items —
    every article would qualify, which is meaningless. The chronological
    ordering is already exploration."""
    user_id = uuid4()
    articles = [
        _article(title=f"a-{i}", source=f"S{i % 3}", age_days=i) for i in range(20)
    ]

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(),  # cold start
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: articles,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=20
    )

    assert all(it.reason != "Outside your usual interests" for it in items)


# ---------------------------------------------------------------------------
# Admin debug payload
# ---------------------------------------------------------------------------


def test_rank_for_you_sets_exploration_flag_consistent_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The new ``was_exploration_injection`` flag on ForYouItem should
    agree exactly with the EXPLORATION_REASON label.

    Uses the same pool shape as
    test_rank_for_you_injects_exploration_items_with_dedicated_reason
    so we know there will be at least some injected items, plus
    plenty of non-injected items, in the same response.
    """
    user_id = uuid4()

    matching = [
        _article(
            title=f"Rag {i}",
            category="rag",
            source=f"RagSrc{i % 3}",
            tags=["rag"],
            age_days=1,
        )
        for i in range(25)
    ]
    outside = [
        _article(
            title=f"Outside {i}",
            category="hardware",
            source=f"OutsideSrc{i % 5}",
            tags=["gpu"],
            age_days=0,
        )
        for i in range(15)
    ]
    all_articles = matching + outside

    monkeypatch.setattr(
        for_you,
        "build_user_profile",
        lambda *, session, user_id: UserProfile(
            interest_categories=frozenset({"rag"}),
            interest_tags=frozenset({"rag"}),
        ),
    )
    monkeypatch.setattr(
        app_crud,
        "get_recent_articles_excluding",
        lambda **kwargs: all_articles,
    )
    monkeypatch.setattr(app_crud, "get_user_embedding", lambda **kwargs: None)
    monkeypatch.setattr(
        ranking,
        "compute_and_save_user_vector",
        lambda **kwargs: None,
    )

    fake_session: Any = object()
    items, _total = for_you.rank_for_you(
        session=fake_session, user_id=user_id, skip=0, limit=40
    )

    # The flag and the reason label must agree exactly. If they ever
    # diverge it means the API layer can't trust the flag — and
    # consumers that pre-empt rendering on the flag would silently
    # render the wrong badge. Both are derived from the same
    # explored_ids set in rank_for_you, so they must be lockstep.
    for it in items:
        if it.was_exploration_injection:
            assert it.reason == "Outside your usual interests", (
                f"flag set but reason is {it.reason!r}"
            )
        else:
            assert it.reason != "Outside your usual interests", (
                "flag clear but reason is the exploration label"
            )

    # Sanity: the test setup actually exercises both branches.
    assert any(it.was_exploration_injection for it in items)
    assert any(not it.was_exploration_injection for it in items)


def test_build_debug_payload_preserves_raw_components_and_total() -> None:
    """The projection should round-trip every breakdown field the
    debug panel needs to render — no rounding, no rescaling.
    """
    from app.services.recommender import (
        CandidateArticle,
        ScoreBreakdown,
        ScoredArticle,
        ScoringWeights,
    )

    article = CandidateArticle(
        id=uuid4(),
        title="t",
        source="Example",
        category="models",
        tags=("rag",),
        published_at=NOW,
    )
    weights = ScoringWeights()
    breakdown = ScoreBreakdown(
        semantic=0.5,
        explicit=0.8,
        source=0.2,
        recency=0.9,
        weights=weights,
    )
    item = for_you.ForYouItem(
        scored=ScoredArticle(article=article, breakdown=breakdown),
        reason="Matches your interest in rag",
        was_exploration_injection=False,
    )

    payload = for_you.build_debug_payload(item)

    assert payload.breakdown.semantic == 0.5
    assert payload.breakdown.explicit == 0.8
    assert payload.breakdown.source == 0.2
    assert payload.breakdown.recency == 0.9
    # Total is computed from breakdown.total (which uses weights).
    # Re-derive here to assert lockstep, not to recompute it inside the
    # test in a way that could mask a bug.
    assert payload.breakdown.total == breakdown.total
    assert payload.was_exploration_injection is False


def test_build_debug_payload_pre_computes_weighted_contributions() -> None:
    """The point of the helper is to send weighted contributions so
    the FE doesn't have to reproduce ScoringWeights. Verify the math.
    """
    from app.services.recommender import (
        CandidateArticle,
        ScoreBreakdown,
        ScoredArticle,
        ScoringWeights,
    )

    article = CandidateArticle(
        id=uuid4(),
        title="t",
        source="Example",
        category="models",
        tags=(),
        published_at=NOW,
    )
    # Defaults: 0.30, 0.40, 0.15, 0.15
    weights = ScoringWeights()
    breakdown = ScoreBreakdown(
        semantic=1.0,
        explicit=1.0,
        source=1.0,
        recency=1.0,
        weights=weights,
    )
    item = for_you.ForYouItem(
        scored=ScoredArticle(article=article, breakdown=breakdown),
        reason=None,
        was_exploration_injection=False,
    )

    payload = for_you.build_debug_payload(item)

    assert payload.breakdown.weighted_semantic == pytest.approx(0.30)
    assert payload.breakdown.weighted_explicit == pytest.approx(0.40)
    assert payload.breakdown.weighted_source == pytest.approx(0.15)
    assert payload.breakdown.weighted_recency == pytest.approx(0.15)
    # All four components at 1.0 with weights summing to 1.0 → total 1.0.
    assert payload.breakdown.total == pytest.approx(1.0)


def test_build_debug_payload_dominant_signal_matches_breakdown() -> None:
    """The dominant_signal we send should be the same one the
    recommender computes — the FE shouldn't have to recompute it.
    """
    from app.services.recommender import (
        CandidateArticle,
        ScoreBreakdown,
        ScoredArticle,
        ScoringWeights,
    )

    article = CandidateArticle(
        id=uuid4(),
        title="t",
        source="Example",
        category="models",
        tags=(),
        published_at=NOW,
    )
    weights = ScoringWeights()
    # Explicit dominates: weighted contribution 0.40 * 0.9 = 0.36
    # vs semantic 0.30 * 1.0 = 0.30, source 0.15 * 1.0 = 0.15,
    # recency 0.15 * 1.0 = 0.15.
    breakdown = ScoreBreakdown(
        semantic=1.0,
        explicit=0.9,
        source=1.0,
        recency=1.0,
        weights=weights,
    )
    item = for_you.ForYouItem(
        scored=ScoredArticle(article=article, breakdown=breakdown),
        reason=None,
        was_exploration_injection=False,
    )

    payload = for_you.build_debug_payload(item)

    assert payload.breakdown.dominant_signal == "explicit"
    # And it agrees with what the breakdown itself reports — the only
    # thing worse than not sending dominant_signal is sending one that
    # disagrees with the recommender's view of itself.
    assert payload.breakdown.dominant_signal == breakdown.dominant_signal()


def test_build_debug_payload_carries_exploration_flag() -> None:
    """When the orchestrator sets was_exploration_injection on the
    ForYouItem, it must surface on the payload — that's the only way
    the FE can render the exploration badge."""
    from app.services.recommender import (
        CandidateArticle,
        ScoreBreakdown,
        ScoredArticle,
        ScoringWeights,
    )

    article = CandidateArticle(
        id=uuid4(),
        title="t",
        source="Example",
        category="models",
        tags=(),
        published_at=NOW,
    )
    # Exploration items have semantic = explicit = source = 0; only
    # recency is non-zero. We don't validate that invariant here (the
    # exploration module's tests do that) — we just verify the flag
    # plumbing.
    weights = ScoringWeights()
    breakdown = ScoreBreakdown(
        semantic=0.0,
        explicit=0.0,
        source=0.0,
        recency=0.7,
        weights=weights,
    )
    item = for_you.ForYouItem(
        scored=ScoredArticle(article=article, breakdown=breakdown),
        reason="Outside your usual interests",
        was_exploration_injection=True,
    )

    payload = for_you.build_debug_payload(item)

    assert payload.was_exploration_injection is True
