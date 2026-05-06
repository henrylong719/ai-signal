from app.services.article_tagging import normalize_excerpt, tag_article


def test_normalize_excerpt_strips_html_and_prefers_latin_duplicate_content() -> None:
    raw_excerpt = """
    <div class="paper-content">
      <p>Authors: Keming Wu, Zuhao Yang</p>
      <h3>arXiv Links</h3>
      <p><a href="https://arxiv.org/abs/2604.28185">arXiv</a> |
      <a href="https://arxiv.org/pdf/2604.28185.pdf">PDF</a></p>
      <h3>AI summary</h3>
      <p>Abstract Visual generation models need structural and causal understanding.</p>
      <p>\u6458\u8981\uff1a\u89c6\u89c9\u751f\u6210\u6a21\u578b\u9700\u8981\u7ed3\u6784\u548c\u56e0\u679c\u7406\u89e3\u3002</p>
    </div>
    """

    normalized = normalize_excerpt(raw_excerpt)

    assert "<div" not in normalized
    assert "Authors: Keming Wu, Zuhao Yang" in normalized
    assert "arXiv | PDF" in normalized
    assert "Abstract Visual generation models" in normalized
    assert "\u89c6\u89c9\u751f\u6210\u6a21\u578b" not in normalized


def test_normalize_excerpt_preserves_non_latin_content_without_latin_duplicate() -> (
    None
):
    raw_excerpt = (
        "<p>\u6458\u8981\uff1a\u89c6\u89c9\u751f\u6210\u6a21\u578b"
        "\u9700\u8981\u7ed3\u6784\u548c\u56e0\u679c\u7406\u89e3\u3002</p>"
    )

    assert (
        normalize_excerpt(raw_excerpt)
        == "\u6458\u8981\uff1a\u89c6\u89c9\u751f\u6210\u6a21\u578b"
        "\u9700\u8981\u7ed3\u6784\u548c\u56e0\u679c\u7406\u89e3\u3002"
    )


def test_tag_article_matches_against_normalized_excerpt() -> None:
    category, tags = tag_article(
        title="Storage notes",
        excerpt="<p>Use a vector&nbsp;database for retrieval.</p>",
        fallback="other",
    )

    assert category == "rag"
    assert tags == ["rag", "retrieval", "vector-db"]


def test_tag_article_identifies_infrastructure_topics() -> None:
    category, tags = tag_article(
        title="Serving Llama models with lower GPU latency",
        excerpt="Batching and KV cache tuning improve inference throughput.",
        fallback="other",
    )

    assert category == "infrastructure"
    assert tags == [
        "hardware",
        "inference",
        "infrastructure",
        "llms",
        "models",
        "optimization",
        "performance",
    ]


def test_tag_article_identifies_agent_subtopic_tags() -> None:
    category, tags = tag_article(
        title="Agent workflows with MCP tool calling",
        excerpt="A model context protocol server coordinates multi-agent workflows.",
        fallback="other",
    )

    assert category == "agents"
    assert tags == ["agents", "mcp", "tool-use", "workflows"]


def test_tag_article_identifies_expanded_categories() -> None:
    examples = [
        (
            "AI tutoring in the classroom",
            "Education use cases are changing workplace productivity.",
            "applications",
            {"applications", "education", "productivity"},
        ),
        (
            "AI startup raises new funding",
            "Investors lifted the company's valuation as enterprise AI adoption grows.",
            "business",
            {"business", "market", "startups"},
        ),
        (
            "AI regulation and copyright lawsuit update",
            "Policy makers are weighing governance rules and licensing requirements.",
            "policy",
            {"legal", "policy", "regulation"},
        ),
        (
            "Red-team report on prompt injection",
            "The study covers safety, alignment, jailbreaks, misuse, and privacy risks.",
            "safety",
            {"alignment", "safety", "security"},
        ),
    ]

    for title, excerpt, expected_category, expected_tags in examples:
        category, tags = tag_article(title=title, excerpt=excerpt, fallback="other")

        assert category == expected_category
        assert expected_tags.issubset(tags)
