import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.schemas.source import Category


class ArticleBase(SQLModel):
    url: str
    title: str
    source: str = Field(max_length=64)

    excerpt: str | None = None
    image_url: str | None = None
    author: str | None = None

    category: Category
    tags: list[str] = Field(default_factory=list)

    published_at: datetime | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(SQLModel):
    url: str | None = None
    title: str | None = None
    source: str | None = Field(default=None, max_length=64)
    excerpt: str | None = None
    image_url: str | None = None
    author: str | None = None
    category: Category | None = None
    tags: list[str] | None = None
    published_at: datetime | None = None


class ArticlePublic(ArticleBase):
    id: uuid.UUID
    fetched_at: datetime


class ArticlesPublic(SQLModel):
    data: list[ArticlePublic]
    count: int


class ScoreBreakdownPublic(SQLModel):
    """Per-article scoring components, surfaced for the admin debug panel.

    Mirrors ``services.recommender.ScoreBreakdown`` but pre-computes the
    weighted contributions (``weighted_*``) server-side. The frontend
    wants weighted values to render the dominant signal — making the FE
    recompute would mean duplicating ``ScoringWeights`` constants in JS
    and risking drift when we tune. Sending both raw and weighted is
    four extra floats and removes that whole class of bug.
    """

    semantic: float
    explicit: float
    source: float
    recency: float
    weighted_semantic: float
    weighted_explicit: float
    weighted_source: float
    weighted_recency: float
    total: float
    dominant_signal: str | None


class ForYouArticleDebugPublic(SQLModel):
    """Diagnostic payload attached to each For-You article when ``?debug=1``.

    Populated only when the request asks for debug AND the caller is a
    superuser — non-superusers always see ``None`` here regardless of the
    query param (see the route handler for the silent-ignore policy).
    """

    breakdown: ScoreBreakdownPublic
    was_exploration_injection: bool


class ScoringWeightsPublic(SQLModel):
    """The four weights used by the recommender, surfaced in the debug envelope.

    Lets the debug panel header show "weights: 0.30 / 0.40 / 0.15 / 0.15"
    so a weight tuning experiment is visible at a glance without reading
    code. Only included when the request asks for debug.
    """

    semantic: float
    explicit: float
    source: float
    recency: float


class ForYouArticlePublic(ArticlePublic):
    """Article + recommendation reason label, plus optional debug payload.

    The reason is built server-side from the dominant scoring component
    (see ``services.recommender.reason_for``). Optional because pure-recency
    recommendations may not justify a badge.

    ``debug`` is populated only when the caller is a superuser AND passed
    ``?debug=1``. Non-superusers always see ``None`` here, even if they
    pass the query param — the route handler silently ignores the flag
    rather than 403'ing, so a superuser's debug URL pasted to a regular
    user just renders the normal feed.
    """

    reason: str | None = None
    debug: ForYouArticleDebugPublic | None = None


class ForYouArticlesPublic(SQLModel):
    data: list[ForYouArticlePublic]
    count: int
    candidate_pool_cap: int
    # Surfaced only on debug responses; lets the frontend show the
    # active weight set as a header on the debug panel. Always None on
    # normal responses.
    weights: ScoringWeightsPublic | None = None
