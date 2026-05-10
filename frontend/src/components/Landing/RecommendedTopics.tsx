import { Link } from '@tanstack/react-router'
import { Sparkles } from 'lucide-react'
import type { category } from '@/client'
import { trackGuestEvent } from '@/lib/analytics'
import { capitalize } from '@/lib/utils'
import { Badge } from '../ui/badge'

const PREVIEW_TOPICS = [
  'agents',
  'rag',
  'models',
  'research',
  'engineering',
  'infrastructure',
  'applications',
  'business',
  'policy',
  'safety',
] satisfies category[]

const RecommendedTopics = () => {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2.5">
        <div className="text-slate-400 dark:text-muted-foreground">
          <Sparkles className="h-4 w-4 stroke-[1.6]" />
        </div>
        <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
          Recommended topics
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {PREVIEW_TOPICS.map((cat) => (
          <Link
            key={cat}
            to="/category-feed/$cat"
            params={{ cat }}
            onClick={() =>
              trackGuestEvent('guest_topic_click', { payload: { topic: cat } })
            }
            className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <Badge
              variant="secondary"
              className="h-8 cursor-pointer border-slate-200/70 bg-white px-3 text-[0.8125rem] font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.025)] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground"
            >
              {capitalize(cat)}
            </Badge>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default RecommendedTopics
