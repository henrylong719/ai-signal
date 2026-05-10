"""Admin-only email preview endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import Article, User
from app.services.digest import DigestPublic, DigestSection, build_digest
from app.services.digest_email import render_digest_email_html

router = APIRouter(
    prefix="/admin/email-preview",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)

_EMPTY_PREVIEW_MESSAGE = "No articles available for today’s digest preview."


def _sample_digest(*, limit: int) -> DigestPublic:
    now = datetime.now(timezone.utc)
    count = max(limit, 3)
    articles = [
        Article(
            id=uuid.uuid4(),
            url=f"https://example.com/sample-{index}",
            title=title,
            source=source,
            category=category,
            excerpt=excerpt,
            published_at=now - timedelta(hours=index),
            tags=[category],
        )
        for index, (title, source, category, excerpt) in enumerate(
            [
                (
                    "OpenAI previews faster multimodal agents",
                    "OpenAI",
                    "agents",
                    "A new demo shows agents coordinating across text, image, and tool use.",
                ),
                (
                    "Anthropic publishes a practical safety evaluation guide",
                    "Anthropic",
                    "safety",
                    "The guide outlines lightweight checks teams can run before launch.",
                ),
                (
                    "Researchers improve retrieval for long-context models",
                    "AI Research Lab",
                    "rag",
                    "The method combines ranking signals with chunk-level citations.",
                ),
                (
                    "New inference stack reduces serving latency",
                    "Modal",
                    "infrastructure",
                    "Teams are tuning batch sizes and cache behavior for production workloads.",
                ),
                (
                    "Enterprise AI adoption shifts toward workflow automation",
                    "The Signal",
                    "business",
                    "Operators are moving from chat pilots to repeatable internal workflows.",
                ),
                (
                    "Policy teams publish guidance for AI evaluations",
                    "Policy Review",
                    "policy",
                    "The recommendations focus on documenting model limitations clearly.",
                ),
                (
                    "Engineers share lessons from agent observability",
                    "Engineering Notes",
                    "engineering",
                    "Tracing and replay tools are becoming central to production debugging.",
                ),
                (
                    "Open-source model release improves small-device performance",
                    "Hugging Face",
                    "models",
                    "The release targets lower memory usage without a large quality drop.",
                ),
            ][:count]
        )
    ]
    return DigestPublic(
        generated_at=now,
        window_start=now - timedelta(hours=24),
        sections=[
            DigestSection(
                key="top",
                title="Top stories",
                articles=articles,
                reasons={article.id: None for article in articles},
            )
        ],
        is_personalized=False,
    )


@router.get("/digest-html", response_class=HTMLResponse)
def preview_digest_html(
    session: SessionDep,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    user_id: uuid.UUID | None = None,
    sample: bool = False,
) -> HTMLResponse:
    """Render the Today’s Signal digest HTML without sending email."""
    preview_user = current_user
    if user_id is not None:
        preview_user = session.get(User, user_id)
        if preview_user is None:
            raise HTTPException(status_code=404, detail="User not found")

    digest = (
        _sample_digest(limit=limit)
        if sample
        else build_digest(session=session, user_id=preview_user.id)
    )
    html = render_digest_email_html(
        digest=digest,
        user=preview_user,
        article_limit=limit,
        empty_message=_EMPTY_PREVIEW_MESSAGE,
    )
    return HTMLResponse(content=html)
