import html
import re
from html.parser import HTMLParser

from app.models import Category

_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "details",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
_IGNORED_TAGS = {"script", "style"}
_PARAGRAPH_BREAK_RE = re.compile(r"\n+")
_WHITESPACE_RE = re.compile(r"[^\S\n]+")


class _ExcerptTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag in _IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag in _BLOCK_TAGS:
            self._append_break()

    def handle_endtag(self, tag: str) -> None:
        if tag in _IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return
        if tag in _BLOCK_TAGS:
            self._append_break()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._chunks.append(data.replace("\n", " "))

    def text(self) -> str:
        return "".join(self._chunks)

    def _append_break(self) -> None:
        if self._chunks and self._chunks[-1] != "\n":
            self._chunks.append("\n")


def normalize_excerpt(excerpt: str | None) -> str:
    if not excerpt:
        return ""

    parser = _ExcerptTextParser()
    parser.feed(excerpt)
    parser.close()

    paragraphs = [
        _WHITESPACE_RE.sub(" ", html.unescape(paragraph)).strip()
        for paragraph in _PARAGRAPH_BREAK_RE.split(parser.text())
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]

    return "\n\n".join(_prefer_latin_paragraphs(paragraphs))


def _prefer_latin_paragraphs(paragraphs: list[str]) -> list[str]:
    has_substantive_latin = any(
        _latin_letter_count(paragraph) >= 20 and _latin_letter_ratio(paragraph) >= 0.6
        for paragraph in paragraphs
    )
    if not has_substantive_latin:
        return paragraphs

    return [
        paragraph
        for paragraph in paragraphs
        if _latin_letter_ratio(paragraph) >= 0.5 or _letter_count(paragraph) == 0
    ]


def _letter_count(text: str) -> int:
    return sum(1 for char in text if char.isalpha())


def _latin_letter_count(text: str) -> int:
    return sum(1 for char in text if "A" <= char <= "Z" or "a" <= char <= "z")


def _latin_letter_ratio(text: str) -> float:
    letters = _letter_count(text)
    if letters == 0:
        return 1.0
    return _latin_letter_count(text) / letters


_RULES: list[tuple[Category, list[re.Pattern[str]], list[str]]] = [
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
    haystack = f"{title} {normalize_excerpt(excerpt)}"
    matched: list[Category] = []
    tags: list[str] = []
    for category, patterns, tag_list in _RULES:
        if any(p.search(haystack) for p in patterns):
            matched.append(category)
            tags.extend(tag_list)
    primary: Category = matched[0] if matched else fallback
    return primary, sorted(set(tags))
