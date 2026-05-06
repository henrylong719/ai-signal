import { Link } from "@tanstack/react-router"
import { Sparkles } from "lucide-react"
import { CATEGORIES } from "@/lib/constants"
import { capitalize } from "@/lib/utils"
import { Badge } from "../ui/badge"

const RecommendedTopics = () => {
  return (
    <div>
      <div className="mb-4 flex items-center gap-2.5">
        <div className="text-slate-400 dark:text-muted-foreground">
          <Sparkles className="h-4 w-4 stroke-[1.6]" />
        </div>
        <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
          Recommended topics
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <Link
            key={cat}
            to="/category-feed/$cat"
            params={{ cat }}
            className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <Badge
              variant="secondary"
              className="cursor-pointer border-slate-200/80 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground"
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
