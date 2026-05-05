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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
            re.compile(r"\bagent\s+harness(es)?\b", re.I),
            re.compile(r"\bmulti[\s-]?agent\b", re.I),
        ],
        ["agents"],
    ),
    (
        "agents",
        [
            re.compile(r"\btool[\s-]?(use|calling)\b", re.I),
            re.compile(r"\bfunction\s+calling\b", re.I),
        ],
        ["agents", "tool-use"],
    ),
    (
        "agents",
        [
            re.compile(r"\bmcp\b", re.I),
            re.compile(r"\bmodel\s+context\s+protocol\b", re.I),
        ],
        ["agents", "mcp"],
    ),
    (
        "agents",
        [
            re.compile(r"\bworkflow(s)?\b", re.I),
            re.compile(r"\borchestrat(e|ion)\b", re.I),
        ],
        ["agents", "workflows"],
    ),
    (
        "agents",
        [
            re.compile(r"\bcomputer\s+use\b", re.I),
            re.compile(r"\bbrowser\s+use\b", re.I),
            re.compile(r"\bautonomous\s+(agent|agents|system|systems)\b", re.I),
        ],
        ["agents", "automation"],
    ),
    (
        "rag",
        [
            re.compile(r"\brag\b", re.I),
            re.compile(r"\bretrieval[\s-]?augmented\s+generation\b", re.I),
        ],
        ["rag"],
    ),
    (
        "rag",
        [
            re.compile(r"\bretrieval\b", re.I),
            re.compile(r"\bretriever(s)?\b", re.I),
            re.compile(r"\bsemantic\s+search\b", re.I),
        ],
        ["rag", "retrieval"],
    ),
    (
        "rag",
        [
            re.compile(r"\bembedding(s)?\b", re.I),
            re.compile(r"\bembed\s+model(s)?\b", re.I),
        ],
        ["rag", "embeddings"],
    ),
    (
        "rag",
        [
            re.compile(r"\bvector\s+(db|database|store)\b", re.I),
            re.compile(r"\bvector\s+search\b", re.I),
        ],
        ["rag", "vector-db"],
    ),
    (
        "rag",
        [
            re.compile(r"\brerank(er|ing)?\b", re.I),
            re.compile(r"\bcross[\s-]?encoder\b", re.I),
        ],
        ["rag", "reranking"],
    ),
    (
        "models",
        [
            re.compile(r"\b(gpt|claude|gemini|llama|mistral|qwen)[-\s]?\d", re.I),
            re.compile(r"\b(gpt|claude|gemini|llama|mistral|qwen)\s+model(s)?\b", re.I),
            re.compile(r"\bfrontier\s+model(s)?\b", re.I),
            re.compile(r"\bfoundation\s+model(s)?\b", re.I),
            re.compile(r"\blanguage\s+model(s)?\b", re.I),
        ],
        ["models", "llms"],
    ),
    (
        "models",
        [
            re.compile(r"\bbenchmark(s|ing)?\b", re.I),
            re.compile(r"\bleaderboard(s)?\b", re.I),
        ],
        ["models", "benchmarks"],
    ),
    (
        "models",
        [
            re.compile(r"\bcontext window\b", re.I),
            re.compile(r"\blong[\s-]?context\b", re.I),
        ],
        ["models", "long-context"],
    ),
    (
        "models",
        [
            re.compile(r"\breasoning\s+model(s)?\b", re.I),
            re.compile(r"\bchain[\s-]?of[\s-]?thought\b", re.I),
        ],
        ["models", "reasoning"],
    ),
    (
        "models",
        [
            re.compile(r"\bmultimodal\b", re.I),
            re.compile(r"\bvision[\s-]?language\b", re.I),
            re.compile(r"\baudio\s+model(s)?\b", re.I),
            re.compile(r"\bvideo\s+model(s)?\b", re.I),
        ],
        ["models", "multimodal"],
    ),
    (
        "models",
        [
            re.compile(r"\bopen[\s-]?(weight|weights|source)\b", re.I),
            re.compile(r"\bmodel\s+release\b", re.I),
        ],
        ["models", "open-weights"],
    ),
    (
        "models",
        [
            re.compile(r"\bfine[\s-]?tun(e|ing)\b", re.I),
            re.compile(r"\bpost[\s-]?training\b", re.I),
            re.compile(r"\brlhf\b", re.I),
            re.compile(r"\bdistillation\b", re.I),
        ],
        ["models", "training"],
    ),
    (
        "infrastructure",
        [
            re.compile(r"\binference\b", re.I),
            re.compile(r"\bserv(e|ing)\b", re.I),
            re.compile(r"\bdeployment(s)?\b", re.I),
            re.compile(r"\bproduction\b", re.I),
        ],
        ["infrastructure", "inference"],
    ),
    (
        "infrastructure",
        [
            re.compile(r"\b(gpu|tpu|cuda|h100|h200|b200)\b", re.I),
            re.compile(r"\baccelerator(s)?\b", re.I),
            re.compile(r"\bsilicon\b", re.I),
            re.compile(r"\bchip(s)?\b", re.I),
        ],
        ["infrastructure", "hardware"],
    ),
    (
        "infrastructure",
        [
            re.compile(r"\blatency\b", re.I),
            re.compile(r"\bthroughput\b", re.I),
            re.compile(r"\btokens?\s+per\s+second\b", re.I),
            re.compile(r"\bcost[\s-]?(efficient|efficiency|effective)\b", re.I),
        ],
        ["infrastructure", "performance"],
    ),
    (
        "infrastructure",
        [
            re.compile(r"\bkubernetes\b", re.I),
            re.compile(r"\bautoscal(e|ing)\b", re.I),
            re.compile(r"\bserverless\b", re.I),
            re.compile(r"\bdata\s+center(s)?\b", re.I),
        ],
        ["infrastructure", "deployment"],
    ),
    (
        "infrastructure",
        [
            re.compile(r"\bquantization\b", re.I),
            re.compile(r"\bkv\s+cache\b", re.I),
            re.compile(r"\bbatch(ing)?\b", re.I),
        ],
        ["infrastructure", "optimization"],
    ),
    (
        "engineering",
        [
            re.compile(r"\beval(uation)?s?\b", re.I),
            re.compile(r"\bllm[\s-]?as[\s-]?judge\b", re.I),
        ],
        ["engineering", "evals"],
    ),
    (
        "engineering",
        [
            re.compile(r"\bobservab", re.I),
            re.compile(r"\btracing\b", re.I),
            re.compile(r"\bmonitoring\b", re.I),
        ],
        ["engineering", "observability"],
    ),
    (
        "engineering",
        [
            re.compile(r"\bguardrail", re.I),
            re.compile(r"\bpolicy\s+enforcement\b", re.I),
        ],
        ["engineering", "guardrails"],
    ),
    (
        "engineering",
        [
            re.compile(r"\bprompt\s+(engineering|caching)\b", re.I),
        ],
        ["engineering", "prompting"],
    ),
    (
        "engineering",
        [
            re.compile(r"\bstructured\s+output(s)?\b", re.I),
            re.compile(r"\bschema(s)?\b", re.I),
            re.compile(r"\bjson\s+mode\b", re.I),
        ],
        ["engineering", "structured-outputs"],
    ),
    (
        "engineering",
        [
            re.compile(r"\bai\s+sdk\b", re.I),
            re.compile(r"\bdeveloper\s+tool(s|ing)?\b", re.I),
            re.compile(r"\bcode\s+assistant(s)?\b", re.I),
        ],
        ["engineering", "developer-tools"],
    ),
    (
        "applications",
        [
            re.compile(r"\b(use\s+case|use[\s-]?cases)\b", re.I),
            re.compile(r"\bproductivity\b", re.I),
            re.compile(r"\bworkplace\b", re.I),
            re.compile(r"\boffice\b", re.I),
        ],
        ["applications", "productivity"],
    ),
    (
        "applications",
        [
            re.compile(r"\beducation\b", re.I),
            re.compile(r"\bclassroom\b", re.I),
            re.compile(r"\btutor(s|ing)?\b", re.I),
        ],
        ["applications", "education"],
    ),
    (
        "applications",
        [
            re.compile(r"\bcustomer\s+support\b", re.I),
            re.compile(r"\bhealthcare\b", re.I),
            re.compile(r"\blegal\b", re.I),
            re.compile(r"\bfinance\b", re.I),
        ],
        ["applications", "industry-use-cases"],
    ),
    (
        "business",
        [
            re.compile(r"\bstartup(s)?\b", re.I),
            re.compile(r"\bfunding\b", re.I),
            re.compile(r"\brais(e|ed|es|ing)\b", re.I),
            re.compile(r"\bvaluation\b", re.I),
            re.compile(r"\bacquisition\b", re.I),
        ],
        ["business", "startups"],
    ),
    (
        "business",
        [
            re.compile(r"\benterprise\s+(adoption|ai)\b", re.I),
            re.compile(r"\bmarket\b", re.I),
            re.compile(r"\brevenue\b", re.I),
            re.compile(r"\binvest(or|ment|ing)\b", re.I),
        ],
        ["business", "market"],
    ),
    (
        "policy",
        [
            re.compile(r"\bregulat(e|ion|or|ors|ory)\b", re.I),
            re.compile(r"\bpolicy\b", re.I),
            re.compile(r"\bgovernance\b", re.I),
            re.compile(r"\bexecutive\s+order\b", re.I),
        ],
        ["policy", "regulation"],
    ),
    (
        "policy",
        [
            re.compile(r"\bcopyright\b", re.I),
            re.compile(r"\blawsuit\b", re.I),
            re.compile(r"\blicens(e|ing)\b", re.I),
        ],
        ["policy", "legal"],
    ),
    (
        "research",
        [
            re.compile(r"\barxiv\b", re.I),
            re.compile(r"\bpaper\b", re.I),
            re.compile(r"\babstract\b", re.I),
            re.compile(r"\bwe propose\b", re.I),
        ],
        ["research", "papers"],
    ),
    (
        "research",
        [
            re.compile(r"\bdataset(s)?\b", re.I),
            re.compile(r"\bsynthetic\s+data\b", re.I),
            re.compile(r"\bdata\s+mixture(s)?\b", re.I),
        ],
        ["research", "datasets"],
    ),
    (
        "safety",
        [
            re.compile(r"\balignment\b", re.I),
            re.compile(r"\bsafety\b", re.I),
            re.compile(r"\bred[\s-]?team", re.I),
        ],
        ["safety", "alignment"],
    ),
    (
        "safety",
        [
            re.compile(r"\bjailbreak(s|ing)?\b", re.I),
            re.compile(r"\bprompt\s+injection\b", re.I),
            re.compile(r"\bmisuse\b", re.I),
            re.compile(r"\bprivacy\b", re.I),
        ],
        ["safety", "security"],
    ),
]

_CATEGORY_PRIORITY: tuple[Category, ...] = (
    "agents",
    "rag",
    "safety",
    "infrastructure",
    "models",
    "engineering",
    "research",
    "applications",
    "policy",
    "business",
    "other",
)


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
    matched_categories = set(matched)
    primary = next(
        (category for category in _CATEGORY_PRIORITY if category in matched_categories),
        fallback,
    )
    return primary, sorted(set(tags))
