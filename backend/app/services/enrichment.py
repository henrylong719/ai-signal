"""Call Claude to enrich a single article with summary / why-it-matters / difficulty.

This module owns the LLM interaction. It exposes one function,
`enrich_article`, that takes an article and returns structured enrichment
data. It does NOT touch the database, manage retries, or run concurrent
batches — those concerns belong to the worker that wraps it.

Failure modes:
    - Transient API errors (timeouts, 429, 5xx) → raise EnrichmentError
    - Schema validation failures               → raise EnrichmentError
    - Refusal / no tool call returned          → raise EnrichmentError

The worker is responsible for catching EnrichmentError, incrementing
the retry counter, and deciding whether to mark the row 'failed'.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from anthropic.types import Message, ToolParam, ToolUseBlock
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.models import Article
from app.schemas.source import Difficulty


# Bumped whenever the prompt changes meaningfully. Stored on the row so
# we can identify and re-enrich rows produced by older prompts.
#
# v2: Added explicit length targets (≤250 chars summary, ≤180 chars
#     why_it_matters) to keep card layouts uniform. Pushed back on
#     generic why-it-matters phrasing.
PROMPT_VERSION = 2

# Model identifier. Using the alias (not the dated snapshot) so we ride
# any minor improvements in the same family without code changes.
_MODEL = "claude-haiku-4-5"

# Cap on excerpt characters sent to the model. The first ~2000 chars of
# any well-written excerpt is enough to write a card; going longer wastes
# tokens with no quality benefit.
_EXCERPT_CHAR_CAP = 2000

# Output cap. Our entire JSON response is well under 250 tokens; anything
# higher just risks the model rambling inside the JSON.
_MAX_TOKENS = 400

# Per-call timeout. 30s is generous for Haiku on a small prompt; we'd
# rather fail and retry than block the worker.
_TIMEOUT_SECONDS = 30.0

_SYSTEM_PROMPT = """\
You are an editor for an AI engineering news dashboard. For each article \
you receive, you produce a short, honest card that helps a reader decide \
whether to click through.

You will be given a title, a source name, and an excerpt. The excerpt may \
be the full article body, a real abstract, or a short preview. Work with \
what you have. Do not invent facts that are not supported by the input.

Produce three things using the submit_enrichment tool:

1. summary: 1-2 sentences describing what the article is about. Aim for \
roughly 200 characters; never exceed 250. Plain, factual, no marketing \
language. If the excerpt is thin, hedge ("appears to discuss...", "likely \
covers..."). If you genuinely cannot tell from the input, say so briefly \
rather than guessing.

2. why_it_matters: one sentence on why an AI engineer might care. Aim for \
roughly 140 characters; never exceed 180. Be specific: name the concrete \
problem solved, the tool introduced, the tradeoff exposed, or the audience \
it serves. AVOID generic phrasings like "demonstrates a practical \
approach to..." or "engineers will benefit from..." — these say nothing. \
If you cannot name something concrete from the input, return: "General AI \
news; little engineering signal."

3. difficulty: "beginner", "intermediate", or "advanced", based on the \
technical depth a reader needs to follow the article. Use beginner for \
product announcements, news, accessible explainers, and high-level \
overviews. Use advanced for research papers, low-level systems work, and \
posts assuming graduate-level ML knowledge. Intermediate is the middle \
ground. Use the full range — do not default to intermediate."""


class EnrichmentError(Exception):
    """Raised when enrichment fails for any reason."""


# --- Validation schema ---
# Pydantic model that mirrors the tool input. We validate the model's
# tool_use response against this — any mismatch raises EnrichmentError
# and the worker treats it as a failed attempt.


class _EnrichmentToolInput(BaseModel):
    # Prompt asks for ~200 chars (max 250). Validator allows some buffer
    # so a row 5 chars over doesn't fail-and-retry. Real runaway output
    # (e.g. the model ignoring the cap entirely) still gets rejected.
    summary: str = Field(min_length=1, max_length=300)
    # Prompt asks for ~140 chars (max 180). Same buffer logic.
    why_it_matters: str = Field(min_length=1, max_length=220)
    difficulty: Difficulty


# --- Public result type ---
# Plain dataclass returned to the worker. We keep this separate from the
# pydantic validator so the worker doesn't need to know about pydantic.


@dataclass(frozen=True)
class EnrichmentResult:
    summary: str
    why_it_matters: str
    difficulty: Difficulty
    prompt_version: int = PROMPT_VERSION


# --- Tool definition ---
# Anthropic tool use forces the model into our JSON shape. The schema here
# matches _EnrichmentToolInput exactly. If you change one, change both.

_ENRICHMENT_TOOL: ToolParam = {
    "name": "submit_enrichment",
    "description": (
        "Submit the editorial card for this article: a short summary, "
        "a why-it-matters note, and a difficulty label."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 sentence factual description of the article.",
            },
            "why_it_matters": {
                "type": "string",
                "description": "One sentence on why an AI engineer should care.",
            },
            "difficulty": {
                "type": "string",
                "enum": ["beginner", "intermediate", "advanced"],
                "description": "Technical depth required to follow the article.",
            },
        },
        "required": ["summary", "why_it_matters", "difficulty"],
    },
}


# --- Client ---
# Lazily instantiated so importing this module doesn't fail when the API
# key is unset (e.g. during tests, or for developers who haven't configured
# enrichment yet). The worker checks `enrichment_enabled()` before calling.

_client: anthropic.AsyncAnthropic | None = None


def enrichment_enabled() -> bool:
    """Whether this environment is configured for LLM enrichment."""
    return bool(settings.ANTHROPIC_API_KEY)


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise EnrichmentError(
                "ANTHROPIC_API_KEY is not configured; enrichment is disabled."
            )
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# --- The actual call ---


def _build_user_prompt(article: Article) -> str:
    """Assemble the user-turn prompt from one article."""
    excerpt = (article.excerpt or "").strip()
    if len(excerpt) > _EXCERPT_CHAR_CAP:
        excerpt = excerpt[:_EXCERPT_CHAR_CAP].rsplit(" ", 1)[0] + "..."

    return (
        f"Source: {article.source}\n"
        f"Title: {article.title}\n\n"
        f"Excerpt:\n{excerpt or '(no excerpt available)'}"
    )


def _extract_tool_input(message: Message) -> dict:
    """Pull the tool_use block's input dict out of the response."""
    for block in message.content:
        # The SDK types message.content as a union of many block types.
        # We narrow with isinstance so the type checker knows `block.name`
        # and `block.input` are safe to access.
        if isinstance(block, ToolUseBlock) and block.name == "submit_enrichment":
            # block.input is typed as `object` in the SDK because tool inputs
            # are user-defined; in practice the API always returns a dict
            # for our schema. Validate the shape before trusting it.
            if isinstance(block.input, dict):
                return block.input
            raise EnrichmentError(
                f"Tool input was not a dict: {type(block.input).__name__}"
            )
    raise EnrichmentError(
        f"Model did not call submit_enrichment. stop_reason={message.stop_reason}"
    )


async def enrich_article(article: Article) -> EnrichmentResult:
    """Call Claude to produce enrichment fields for one article.

    Raises EnrichmentError on any failure. Caller decides retry policy.
    """
    client = _get_client()

    try:
        message = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            timeout=_TIMEOUT_SECONDS,
            # System prompt marked for prompt caching. After the first call
            # in a 5-minute window, this portion costs 10% of normal.
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_ENRICHMENT_TOOL],
            tool_choice={"type": "tool", "name": "submit_enrichment"},
            messages=[
                {"role": "user", "content": _build_user_prompt(article)},
            ],
        )
    except anthropic.APIError as e:
        # Network errors, 429s, 5xxs, timeouts — all transient from our
        # perspective. Worker will retry on next pass up to summary_attempts.
        raise EnrichmentError(f"Anthropic API error: {e}") from e

    raw = _extract_tool_input(message)

    try:
        validated = _EnrichmentToolInput.model_validate(raw)
    except ValidationError as e:
        raise EnrichmentError(f"Invalid tool output: {e}") from e

    return EnrichmentResult(
        summary=validated.summary,
        why_it_matters=validated.why_it_matters,
        difficulty=validated.difficulty,
    )
