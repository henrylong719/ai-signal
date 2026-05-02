from typing import Literal

from pydantic.dataclasses import dataclass

Category = Literal[
    "agents",
    "rag",
    "models",
    "infrastructure",
    "engineering",
    "research",
    "other",
]

CATEGORIES: tuple[Category, ...] = (
    "agents",
    "rag",
    "models",
    "infrastructure",
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
    Source("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "engineering"),
    Source("Google Research", "https://research.google/blog/rss/", "research"),
    Source("BAIR", "https://bair.berkeley.edu/blog/feed.xml", "research"),
    Source("Stanford CRFM", "https://crfm.stanford.edu/feed.xml", "research"),
    Source(
        "Apple ML Research", "https://machinelearning.apple.com/rss.xml", "research"
    ),
    Source("Microsoft AI", "https://blogs.microsoft.com/ai/feed/", "models"),
    Source(
        "AWS Machine Learning",
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        "infrastructure",
    ),
    Source(
        "NVIDIA GenAI",
        "https://developer.nvidia.com/blog/category/generative-ai/feed/",
        "infrastructure",
    ),
    Source("LangChain", "https://www.langchain.com/blog/rss.xml", "agents"),
    Source("Weaviate", "https://weaviate.io/blog/rss.xml", "rag"),
    Source("Latent Space", "https://www.latent.space/feed", "engineering"),
    Source("Interconnects", "https://www.interconnects.ai/feed", "models"),
    Source(
        "Simon Willison", "https://simonwillison.net/atom/everything/", "engineering"
    ),
    Source("Chip Huyen", "https://huyenchip.com/feed.xml", "engineering"),
    Source("Lilian Weng", "https://lilianweng.github.io/index.xml", "research"),
    Source("Eugene Yan", "https://eugeneyan.com/rss/", "engineering"),
    Source("The Gradient", "https://thegradient.pub/rss/", "research"),
    Source("Ahead of AI", "https://magazine.sebastianraschka.com/feed", "research"),
    Source("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL", "research"),
    Source("Distill", "https://distill.pub/rss.xml", "research"),
    Source(
        "HF Daily Papers",
        "https://azuresilent.github.io/hf-paper-rss/feed.xml",
        "research",
    ),
)
