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
  'education',
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
  'video',
  'independent',
  'community',
]

export const ARTICLES_PAGE_SIZE = 20

export type source_types = 'all' | 'following' | source_type

export const SOURCE_TYPES: source_types[] = [
  'all',
  'following',
  'official',
  'research',
  'analysis',
  'policy',
  'education',
  'papers',
  'media',
  'newsletter',
  'podcast',
  'video',
  'independent',
  'community',
]

export const SOURCE_FILTER_LABELS: Record<source_types, string> = {
  all: 'All',
  following: 'Following',
  official: 'Official',
  research: 'Research',
  analysis: 'Analysis',
  policy: 'Policy',
  education: 'Education',
  papers: 'Papers',
  media: 'Media',
  newsletter: 'Newsletter',
  podcast: 'Podcast',
  video: 'Video',
  independent: 'Independent',
  community: 'Community',
}
