import type { category, SourcePublic } from '@/client'

export const CATEGORIES: category[] = [
  'agents',
  'rag',
  'models',
  'infrastructure',
  'engineering',
  'research',
  'applications',
  'business',
  'policy',
  'safety',
  'other',
]

export const previewSourceTypes: SourcePublic['source_type'][] = [
  'official',
  'research',
  'media',
  'newsletter',
  'independent',
  'community',
]

export const ARTICLES_PAGE_SIZE = 20
