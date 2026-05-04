import { Link } from "@tanstack/react-router"
import { Sparkles } from "lucide-react"
import { CATEGORIES } from "@/lib/constants"
import { capitalize } from "@/lib/utils"
import { Badge } from "../ui/badge"

const RecommendedTopics = () => {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="text-slate-400 group-hover:text-slate-900 transition-colors ">
          <Sparkles className="w-5 h-5 stroke-[1.5]" />
        </div>
        <span className="font-medium text-slate-400 font-sans text-sm">
          Recommended topics
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <Link key={cat} to={`/category-feed/$cat`} params={{ cat: cat }}>
            <Badge
              variant="secondary"
              className="font-sans font-normal text-sm text-slate-900 bg-slate-100 border-transparent hover:bg-slate-200 px-6 py-2 cursor-pointer"
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
