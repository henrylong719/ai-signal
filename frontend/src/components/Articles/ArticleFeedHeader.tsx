import type { category } from "@/client"
import { capitalized, cn } from "@/lib/utils"

export type TopicFilter = "all" | category

const FILTER_TOPICS = [
  "all",
  "agents",
  "rag",
  "models",
  "infrastructure",
  "engineering",
  "research",
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
    <header className="max-w-7xl pb-6">
      <div className="max-w-3xl">
        <h1 className="font-serif text-3xl font-medium text-slate-900 mb-3 tracking-tight">
          Latest Signals
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed font-serif">
          Curated AI engineering updates on agents, RAG, LLM tools, research,
          and developer trends.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 mt-8">
        {FILTER_TOPICS.map((topic) => (
          <button
            type="button"
            key={topic}
            onClick={() => onTopicChange(topic)}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors border",
              activeTopic === topic
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50",
            )}
          >
            {capitalized(topic)}
          </button>
        ))}
      </div>
    </header>
  )
}
