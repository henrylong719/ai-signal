import type { category, SourcePublic } from "@/client"

export const CATEGORIES: category[] = [
  "agents",
  "rag",
  "models",
  "infrastructure",
  "engineering",
  "research",
  "other",
]

export const previewSourceTypes: SourcePublic["source_type"][] = [
  "official",
  "research",
  "independent",
  "community",
]

export const ARTICLES_PAGE_SIZE = 20
