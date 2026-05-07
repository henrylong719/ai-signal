import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  BadgeCheckIcon,
  ChevronRightIcon,
  FlaskConicalIcon,
  Library,
  type LucideIcon,
  MailIcon,
  MegaphoneIcon,
  NewspaperIcon,
  UsersIcon,
} from 'lucide-react'
import { useMemo } from 'react'
import { ArticlesService, type SourcePublic } from '@/client'
import { Badge } from '@/components/ui/badge'
import { previewSourceTypes } from '@/lib/constants'
import { capitalize } from '@/lib/utils'
import { Skeleton } from '../ui/skeleton'

const sourceTypeIcons: Record<SourcePublic['source_type'], LucideIcon> = {
  official: BadgeCheckIcon,
  independent: NewspaperIcon,
  community: UsersIcon,
  research: FlaskConicalIcon,
  media: MegaphoneIcon,
  newsletter: MailIcon,
}

const shuffle = <T,>(items: T[]) => {
  const shuffled = [...items]

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    const currentItem = shuffled[index]

    shuffled[index] = shuffled[swapIndex]
    shuffled[swapIndex] = currentItem
  }

  return shuffled
}

const getPreviewSources = (sources: SourcePublic[], limit = 4) => {
  const selected: SourcePublic[] = []
  const selectedNames = new Set<string>()
  const sourcesByType = new Map<SourcePublic['source_type'], SourcePublic[]>()

  for (const source of sources) {
    const existingSources = sourcesByType.get(source.source_type) ?? []

    sourcesByType.set(source.source_type, [...existingSources, source])
  }

  for (const sourceType of shuffle(previewSourceTypes)) {
    if (selected.length >= limit) break

    const source = shuffle(sourcesByType.get(sourceType) ?? [])[0]

    if (source) {
      selected.push(source)
      selectedNames.add(source.name)
    }
  }

  for (const source of shuffle(sources)) {
    if (selected.length >= limit) break

    if (!selectedNames.has(source.name)) {
      selected.push(source)
      selectedNames.add(source.name)
    }
  }

  return selected.slice(0, limit)
}

const ArticleSource = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['articleSources'],
    queryFn: () => ArticlesService.readSources(),
  })

  const sources = useMemo(() => getPreviewSources(data?.data ?? []), [data])

  return (
    <div>
      <div className="mb-4 flex items-center gap-2.5">
        <div className="text-slate-400 dark:text-muted-foreground">
          <Library className="h-4 w-4 stroke-[1.6]" />
        </div>
        <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
          Browse sources
        </span>
      </div>
      <div className="mt-3 space-y-1">
        {isLoading ? (
          ['a', 'b', 'c', 'd'].map((key) => (
            <div
              key={key}
              className="flex items-center gap-3 rounded-lg border border-slate-100 p-3 dark:border-border"
            >
              <Skeleton className="h-9 w-9 rounded-md bg-slate-100 dark:bg-muted" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-4 w-32 rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="h-3 w-24 rounded bg-slate-100 dark:bg-muted" />
              </div>
            </div>
          ))
        ) : isError ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            Could not load sources.
          </p>
        ) : sources.length === 0 ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            No sources available yet.
          </p>
        ) : (
          sources.map((source: SourcePublic) => {
            const SourceTypeIcon = sourceTypeIcons[source.source_type]

            return (
              <Link
                key={source.name}
                to="/article-sources/$s"
                params={{ s: source.name }}
                className="group flex items-center gap-3 rounded-lg border border-transparent p-2.5 transition-all hover:border-slate-200/80 hover:bg-white hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:hover:border-border dark:hover:bg-card/45 dark:hover:shadow-none dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-400 ring-1 ring-slate-100 transition-colors group-hover:bg-slate-950 group-hover:text-white group-hover:ring-slate-950 dark:bg-muted/45 dark:text-muted-foreground dark:ring-border dark:group-hover:bg-primary dark:group-hover:text-primary-foreground dark:group-hover:ring-primary">
                  <SourceTypeIcon className="h-4 w-4 stroke-[1.5]" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3 ">
                    <h4 className="truncate font-serif font-medium leading-snug text-slate-950 transition-colors group-hover:text-slate-700 dark:text-foreground dark:group-hover:text-foreground/78">
                      {source.name}
                    </h4>
                    {/* <ChevronRightIcon className="pt-4 h-3.5 w-3.5 shrink-0 text-slate-300 transition-colors group-hover:text-slate-500" /> */}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500 dark:text-muted-foreground">
                    <Badge
                      variant="secondary"
                      className="h-5 border-slate-200/70 bg-white px-2 py-0 text-[11px] font-medium text-slate-500 dark:border-border dark:bg-transparent dark:text-muted-foreground"
                    >
                      {capitalize(source.source_type)}
                    </Badge>
                    <span>{capitalize(source.topic)}</span>
                  </div>
                </div>
              </Link>
            )
          })
        )}
      </div>
      <Link
        to="/all-article-sources"
        className="mt-3 inline-flex items-center rounded-sm text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        See all sources <ChevronRightIcon className="w-3 h-3 ml-0.5 stroke-2" />
      </Link>
    </div>
  )
}

export default ArticleSource
