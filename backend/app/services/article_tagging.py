# apps/api/src/ai_signal_api/tagger.py
from app.models import Category
import re

_RULES: list[tuple[Category, list[re.Pattern], list[str]]] = [
    (
        "agents",
        [
            re.compile(r"\bagent(s|ic)?\b", re.I),
            re.compile(r"\btool[\s-]?(use|calling)\b", re.I),
            re.compile(r"\bmcp\b", re.I),
        ],
        ["agents"],
    ),
    (
        "rag",
        [
            re.compile(r"\brag\b", re.I),
            re.compile(r"\bretrieval\b", re.I),
            re.compile(r"\bembedding", re.I),
            re.compile(r"\bvector\s+(db|database|store)\b", re.I),
        ],
        ["rag"],
    ),
    (
        "models",
        [
            re.compile(r"\b(gpt|claude|gemini|llama|mistral|qwen)[-\s]?\d", re.I),
            re.compile(r"\bbenchmark", re.I),
            re.compile(r"\bcontext window\b", re.I),
        ],
        ["models"],
    ),
    (
        "engineering",
        [
            re.compile(r"\beval(uation)?s?\b", re.I),
            re.compile(r"\bobservab", re.I),
            re.compile(r"\bguardrail", re.I),
            re.compile(r"\bprompt\s+(engineering|caching)\b", re.I),
        ],
        ["engineering"],
    ),
    (
        "research",
        [
            re.compile(r"\barxiv\b", re.I),
            re.compile(r"\bpaper\b", re.I),
            re.compile(r"\bwe propose\b", re.I),
        ],
        ["research"],
    ),
]


def tag_article(
    *, title: str, excerpt: str, fallback: Category
) -> tuple[Category, list[str]]:
    haystack = f"{title} {excerpt}"
    matched: list[Category] = []
    tags: list[str] = []
    for category, patterns, tag_list in _RULES:
        if any(p.search(haystack) for p in patterns):
            matched.append(category)
            tags.extend(tag_list)
    primary: Category = matched[0] if matched else fallback
    return primary, sorted(set(tags))
