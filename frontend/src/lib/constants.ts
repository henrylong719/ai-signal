import type { category, SourcePublic, source_type } from '@/client'

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
  'analysis',
  'policy',
  'education',
  'papers',
  'media',
  'newsletter',
  'podcast',
  'independent',
  'community',
]

export const ARTICLES_PAGE_SIZE = 20

export type source_types = 'all' | source_type

export const SOURCE_TYPES: source_types[] = [
  'all',
  'official',
  'research',
  'analysis',
  'policy',
  'education',
  'papers',
  'media',
  'newsletter',
  'podcast',
  'independent',
  'community',
]

export const SOURCE_FILTER_LABELS: Record<source_types, string> = {
  all: 'All',
  official: 'Official',
  research: 'Research',
  analysis: 'Analysis',
  policy: 'Policy',
  education: 'Education',
  papers: 'Papers',
  media: 'Media',
  newsletter: 'Newsletter',
  podcast: 'Podcast',
  independent: 'Independent',
  community: 'Community',
}
