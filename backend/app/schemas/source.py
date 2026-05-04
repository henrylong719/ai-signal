from typing import Literal

from pydantic.dataclasses import dataclass
from sqlmodel import SQLModel

Category = Literal[
    "agents",
    "rag",
    "models",
    "infrastructure",
    "engineering",
    "research",
    "other",
]
SourceType = Literal["official", "independent", "community", "research"]

CATEGORIES: tuple[Category, ...] = (
    "agents",
    "rag",
    "models",
    "infrastructure",
    "engineering",
    "research",
    "other",
)
SOURCE_TYPES: tuple[SourceType, ...] = (
    "official",
    "independent",
    "community",
    "research",
)


@dataclass(frozen=True)
class Source:
    name: str
    rss_url: str
    default_category: Category
    source_type: SourceType = "independent"
    topic: str = "AI source"
    description: str = "Curated source for AI Signal."


class SourcePublic(SQLModel):
    name: str
    default_category: Category
    source_type: SourceType
    topic: str
    description: str


class SourcesPublic(SQLModel):
    data: list[SourcePublic]
    count: int


SOURCES: tuple[Source, ...] = (
    Source(
        "Anthropic",
        "https://rsshub.app/anthropic/engineering",
        "models",
        "official",
        topic="AI Research Lab",
        description="Engineering updates from Anthropic on Claude, agents, evaluations, and reliable AI systems.",
    ),
    Source(
        "OpenAI",
        "https://openai.com/blog/rss.xml",
        "models",
        "official",
        topic="AI Research Lab",
        description="Official research, product, safety, and engineering updates from OpenAI.",
    ),
    Source(
        "Google DeepMind",
        "https://deepmind.google/blog/rss.xml",
        "research",
        "official",
        topic="AI Research Lab",
        description="Research breakthroughs, product updates, and lab news from Google DeepMind.",
    ),
    Source(
        "Hugging Face Blog",
        "https://huggingface.co/blog/feed.xml",
        "engineering",
        "official",
        topic="Open AI Platform",
        description="Platform, model, dataset, and open source updates from the Hugging Face team.",
    ),
    Source(
        "Google Research",
        "https://research.google/blog/rss/",
        "research",
        "official",
        topic="Corporate Research Lab",
        description="Latest research publications, methods, and project updates from Google Research.",
    ),
    Source(
        "BAIR",
        "https://bair.berkeley.edu/blog/feed.xml",
        "research",
        "research",
        topic="Academic AI Lab",
        description="Research posts from the Berkeley Artificial Intelligence Research lab.",
    ),
    Source(
        "Stanford CRFM",
        "https://crfm.stanford.edu/feed.xml",
        "research",
        "research",
        topic="Foundation Model Research Lab",
        description="Research and policy work from Stanford's Center for Research on Foundation Models.",
    ),
    Source(
        "Apple ML Research",
        "https://machinelearning.apple.com/rss.xml",
        "research",
        "official",
        topic="Corporate AI Research",
        description="Machine learning research papers, talks, and project updates from Apple.",
    ),
    Source(
        "Microsoft AI",
        "https://blogs.microsoft.com/ai/feed/",
        "models",
        "official",
        topic="AI Company Updates",
        description="Official Microsoft AI news covering Copilot, Azure AI, customers, and responsible AI.",
    ),
    Source(
        "AWS Machine Learning",
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        "infrastructure",
        "official",
        topic="Cloud AI Platform",
        description="AWS posts on machine learning services, generative AI infrastructure, and production patterns.",
    ),
    Source(
        "NVIDIA GenAI",
        "https://developer.nvidia.com/blog/category/generative-ai/feed/",
        "infrastructure",
        "official",
        topic="AI Infrastructure",
        description="NVIDIA technical posts on generative AI, accelerated computing, and deployment tooling.",
    ),
    Source(
        "LangChain",
        "https://www.langchain.com/blog/rss.xml",
        "agents",
        "official",
        topic="Agent Framework",
        description="Official LangChain updates on agents, LangGraph, retrieval, evaluations, and app development.",
    ),
    Source(
        "Weaviate",
        "https://weaviate.io/blog/rss.xml",
        "rag",
        "official",
        topic="Vector Database",
        description="Weaviate posts on vector search, RAG architecture, embeddings, and production AI retrieval.",
    ),
    Source(
        "Latent Space",
        "https://www.latent.space/feed",
        "engineering",
        topic="AI Engineering Newsletter",
        description="Technical AI engineering commentary and interviews with builders from leading AI teams.",
    ),
    Source(
        "Interconnects",
        "https://www.interconnects.ai/feed",
        "models",
        topic="Model Research Analysis",
        description="Nathan Lambert's analysis of frontier models, open source AI, training, and policy.",
    ),
    Source(
        "One Useful Thing",
        "https://www.oneusefulthing.org/feed",
        "other",
        topic="Applied AI Commentary",
        description="Ethan Mollick's writing on how AI affects work, education, organizations, and daily life.",
    ),
    Source(
        "The Batch",
        "https://www.deeplearning.ai/the-batch/feed/",
        "other",
        topic="AI News Briefing",
        description="DeepLearning.AI's weekly AI news and insight briefing on research, business, and culture.",
    ),
    Source(
        "Understanding AI",
        "https://www.understandingai.org/feed",
        "other",
        topic="AI Technology Analysis",
        description="Timothy B. Lee's reporting and analysis on AI technology, policy, and economic impact.",
    ),
    Source(
        "AI Snake Oil",
        "https://www.aisnakeoil.com/feed",
        "other",
        topic="AI Accountability Analysis",
        description="Analysis from Sayash Kapoor and Arvind Narayanan on AI claims, risks, and deployment evidence.",
    ),
    Source(
        "GitHub AI & ML",
        "https://github.blog/ai-and-ml/feed/",
        "engineering",
        "official",
        topic="Developer AI Platform",
        description="GitHub posts on AI and machine learning for software development and open source workflows.",
    ),
    Source(
        "GitHub Changelog",
        "https://github.blog/changelog/feed/",
        "infrastructure",
        "official",
        topic="Developer Platform Releases",
        description="Product release notes and platform changes from the official GitHub Changelog.",
    ),
    Source(
        "Towards Data Science",
        "https://towardsdatascience.com/feed",
        "engineering",
        "community",
        topic="Data Science Publication",
        description="Community-authored writing on machine learning, data science, analytics, and AI engineering.",
    ),
    Source(
        "Netflix TechBlog",
        "https://netflixtechblog.com/feed",
        "engineering",
        "official",
        topic="Engineering Blog",
        description="Netflix engineering posts on large-scale systems, data platforms, personalization, and ML.",
    ),
    Source(
        "Replicate Blog",
        "https://replicate.com/blog/rss",
        "engineering",
        "official",
        topic="Model Deployment Platform",
        description="Replicate updates on running, deploying, and building with open models and AI media tools.",
    ),
    Source(
        "Hacker News AI",
        "https://hnrss.org/newest?q=AI+OR+LLM&points=100",
        "other",
        "community",
        topic="Community Discussion",
        description="High-signal Hacker News discussions matching AI and LLM topics.",
    ),
    Source(
        "Vercel AI SDK Releases",
        "https://github.com/vercel/ai/releases.atom",
        "engineering",
        "official",
        topic="AI SDK Releases",
        description="Release notes for Vercel's AI SDK packages and related framework integrations.",
    ),
    Source(
        "Ollama Releases",
        "https://github.com/ollama/ollama/releases.atom",
        "models",
        "official",
        topic="Local Model Runtime",
        description="Official Ollama release notes for running and managing local language models.",
    ),
    Source(
        "LangGraph Releases",
        "https://github.com/langchain-ai/langgraph/releases.atom",
        "agents",
        "official",
        topic="Agent Orchestration Releases",
        description="Official LangGraph releases for building stateful, multi-step agent workflows.",
    ),
    Source(
        "Simon Willison",
        "https://simonwillison.net/atom/everything/",
        "engineering",
        topic="AI Engineering Notebook",
        description="Simon Willison's practical notes on LLMs, software engineering, data, and developer tools.",
    ),
    Source(
        "Chip Huyen",
        "https://huyenchip.com/feed.xml",
        "engineering",
        topic="ML Systems Writing",
        description="Chip Huyen's writing on machine learning systems, evaluation, deployment, and AI engineering.",
    ),
    Source(
        "Lilian Weng",
        "https://lilianweng.github.io/index.xml",
        "research",
        "research",
        topic="AI Research Notes",
        description="Lilian Weng's long-form research notes on machine learning, agents, alignment, and LLMs.",
    ),
    Source(
        "Eugene Yan",
        "https://eugeneyan.com/rss/",
        "engineering",
        topic="Applied ML Engineering",
        description="Eugene Yan's writing on applied machine learning systems, recommendations, and evaluation.",
    ),
    Source(
        "The Gradient",
        "https://thegradient.pub/rss/",
        "research",
        "research",
        topic="AI Research Magazine",
        description="Independent essays and interviews explaining machine learning research and AI systems.",
    ),
    Source(
        "Ahead of AI",
        "https://magazine.sebastianraschka.com/feed",
        "research",
        topic="ML Research Newsletter",
        description="Sebastian Raschka's newsletter on machine learning research, model development, and education.",
    ),
    Source(
        "arXiv cs.CL",
        "https://export.arxiv.org/rss/cs.CL",
        "research",
        "research",
        topic="Research Preprints",
        description="Recent arXiv submissions in computation and language, including NLP and language models.",
    ),
    Source(
        "Distill",
        "https://distill.pub/rss.xml",
        "research",
        "research",
        topic="Machine Learning Research Journal",
        description="Interactive and visual explanations of machine learning research from Distill.",
    ),
    Source(
        "HF Daily Papers",
        "https://azuresilent.github.io/hf-paper-rss/feed.xml",
        "research",
        "research",
        topic="AI Paper Feed",
        description="Daily paper feed surfaced through Hugging Face Papers for new AI research.",
    ),
)
