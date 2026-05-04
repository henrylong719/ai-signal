import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import {
  BadgeCheckIcon,
  ChevronRightIcon,
  FlaskConicalIcon,
  Library,
  type LucideIcon,
  NewspaperIcon,
  UsersIcon,
} from "lucide-react"
import { ArticlesService, type SourcePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { previewSourceTypes } from "@/lib/constants"
import { capitalize } from "@/lib/utils"
import { Skeleton } from "../ui/skeleton"

const sourceTypeIcons: Record<SourcePublic["source_type"], LucideIcon> = {
  official: BadgeCheckIcon,
  independent: NewspaperIcon,
  community: UsersIcon,
  research: FlaskConicalIcon,
}

const getPreviewSources = (sources: SourcePublic[], limit = 4) => {
  const selected: SourcePublic[] = []
  const selectedNames = new Set<string>()

  for (const sourceType of previewSourceTypes) {
    const source = sources.find(
      (item) =>
        item.source_type === sourceType && !selectedNames.has(item.name),
    )

    if (source) {
      selected.push(source)
      selectedNames.add(source.name)
    }
  }

  for (const source of sources) {
    if (selected.length >= limit) break
    if (!selectedNames.has(source.name)) {
      selected.push(source)
      selectedNames.add(source.name)
    }
  }

  return selected.slice(0, limit)
}

const ArticleSource = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["articleSources"],
    queryFn: () => ArticlesService.readSources(),
  })

  const sources = getPreviewSources(data?.data ?? [])

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="text-slate-400 group-hover:text-slate-900 transition-colors ">
          <Library className="w-5 h-5 stroke-[1.5]" />
        </div>
        <span className="font-medium text-slate-400 font-sans text-sm">
          Browse sources
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {isLoading
          ? ["a", "b", "c", "d"].map((key) => (
              <div
                key={key}
                className="flex items-center gap-3 rounded-md border border-slate-100 p-3"
              >
                <Skeleton className="h-9 w-9 rounded-md" />
                <div className="min-w-0 flex-1 space-y-2">
                  <Skeleton className="h-4 w-32 rounded" />
                  <Skeleton className="h-3 w-24 rounded" />
                </div>
              </div>
            ))
          : sources.map((source: SourcePublic) => {
              const SourceTypeIcon = sourceTypeIcons[source.source_type]

              return (
                <Link
                  key={source.name}
                  to="/article-sources/$s"
                  params={{ s: source.name }}
                  className="group flex items-center gap-3 rounded-md transition-colors hover:bg-slate-50 p-2"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-400 ring-1 ring-slate-100 transition-colors group-hover:bg-white group-hover:text-slate-900 group-hover:ring-slate-200">
                    <SourceTypeIcon className="h-4 w-4 stroke-[1.5]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3 ">
                      <h4 className="truncate font-serif font-medium leading-snug text-slate-900 transition-colors group-hover:text-slate-600">
                        {source.name}
                      </h4>
                      {/* <ChevronRightIcon className="pt-4 h-3.5 w-3.5 shrink-0 text-slate-300 transition-colors group-hover:text-slate-500" /> */}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 font-sans text-[11px] text-slate-400">
                      <Badge
                        variant="secondary"
                        className="h-5 border-transparent bg-slate-100 px-2 py-0 font-sans text-[11px] font-normal text-slate-500"
                      >
                        {capitalize(source.source_type)}
                      </Badge>
                      <span>{source.topic}</span>
                    </div>
                  </div>
                </Link>
              )
            })}
      </div>
      <Link
        to="/all-article-sources"
        className="inline-flex items-center text-xs font-sans font-medium text-slate-400 hover:text-slate-900 transition-colors mt-3"
      >
        See all sources <ChevronRightIcon className="w-3 h-3 ml-0.5 stroke-2" />
      </Link>
    </div>
  )
}

export default ArticleSource
