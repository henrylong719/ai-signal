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
    <header className="pb-6 pt-10 sm:pt-12">
      <div className="border-b border-slate-200/80 pb-7 dark:border-border">
        <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
          Feed
        </p>
        <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
          Latest Signals
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
          Curated AI updates on agents, RAG, models, infrastructure,
          applications, policy, and developer trends.
        </p>
      </div>

      <div className="mt-6 rounded-lg border border-slate-200/80 bg-white p-2 shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:border-border dark:bg-transparent dark:shadow-none">
        <div className="flex flex-wrap gap-2">
          {FILTER_TOPICS.map((topic) => (
            <button
              type="button"
              key={topic}
              onClick={() => onTopicChange(topic)}
              className={cn(
                "min-h-9 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background",
                activeTopic === topic
                  ? "border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground"
                  : "border-slate-200/70 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground",
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
