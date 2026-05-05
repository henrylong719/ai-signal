import type { category } from "@/client"
import { capitalize, cn } from "@/lib/utils"

export type TopicFilter = "all" | category

const FILTER_TOPICS = [
  "all",
  "agents",
  "rag",
  "models",
  "infrastructure",
  "engineering",
  "research",
  "applications",
  "business",
  "policy",
  "safety",
  "other",
] satisfies TopicFilter[]

interface ArticleFeedHeaderProps {
  activeTopic: TopicFilter
  onTopicChange: (topic: TopicFilter) => void
}

export function ArticleFeedHeader({
  activeTopic,
  onTopicChange,
}: ArticleFeedHeaderProps) {
  return (
    <header className="pb-6 pt-8">
      <div className="border-b border-slate-200/70 pb-6">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
          Feed
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Latest Signals
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500">
          Curated AI updates on agents, RAG, models, infrastructure,
          applications, policy, and developer trends.
        </p>
      </div>

      <div className="mt-6 rounded-lg border border-slate-200/80 bg-slate-50/70 p-2">
        <div className="flex flex-wrap gap-2">
          {FILTER_TOPICS.map((topic) => (
            <button
              type="button"
              key={topic}
              onClick={() => onTopicChange(topic)}
              className={cn(
                "min-h-9 rounded-full border px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2",
                activeTopic === topic
                  ? "border-slate-950 bg-slate-950 text-white shadow-sm"
                  : "border-transparent bg-transparent text-slate-600 hover:border-slate-200 hover:bg-white hover:text-slate-950",
              )}
            >
              {capitalize(topic)}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
