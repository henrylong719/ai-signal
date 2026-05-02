from typing import Literal

from pydantic.dataclasses import dataclass

Category = Literal["agents", "rag", "models", "engineering", "research", "other"]

CATEGORIES: tuple[Category, ...] = (
    "agents",
    "rag",
    "models",
    "engineering",
    "research",
    "other",
)


@dataclass(frozen=True)
class Source:
    name: str
    rss_url: str
    default_category: Category


SOURCES: tuple[Source, ...] = (
    Source("Anthropic", "https://rsshub.app/anthropic/engineering", "models"),
    Source("OpenAI", "https://openai.com/blog/rss.xml", "models"),
    Source("Google DeepMind", "https://deepmind.google/blog/rss.xml", "research"),
    Source(
        "Simon Willison", "https://simonwillison.net/atom/everything/", "engineering"
    ),
    Source(
        "HF Daily Papers",
        "https://azuresilent.github.io/hf-paper-rss/feed.xml",
        "research",
    ),
)
