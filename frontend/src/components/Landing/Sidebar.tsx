import useAuth from "@/hooks/useAuth"
import ArticleSource from "./ArticleSource"
import RecentBookmarks from "./RecentBookmarks"
import RecommendedTopics from "./RecommendedTopics"

export function Sidebar() {
  const { user } = useAuth()

  return (
    <aside className="pt-8 hidden lg:block lg:col-span-4 space-y-10 border-l border-slate-100 flex-0 lg:pl-10 md:flex-2">
      {/* Today's Digest Card */}
      {/* <div className="bg-slate-50 rounded-xl p-6 border-0">
        <div className="flex items-center gap-2 text-slate-500 mb-3">
          <CalendarIcon className="w-4 h-4 stroke-[1.5]" />
          <span className="text-xs font-medium uppercase tracking-wider font-sans">
            Today's Digest
          </span>
        </div>
        <h3 className="font-serif text-xl font-medium text-slate-900 mb-2">
          Significant leaps in multi-agent orchestration
        </h3>
        <p className="text-sm text-slate-600 mb-5 leading-relaxed font-serif">
          Plus, a new open-source eval framework gaining traction, and
          Anthropic's latest thoughts on context caching.
        </p>
        <Link
          to="/"
          className="inline-flex items-center text-sm font-sans font-medium text-slate-900 hover:text-slate-600 transition-colors"
        >
          Read the daily digest{' '}
          <ChevronRightIcon className="w-4 h-4 ml-1 stroke-[1.5]" />
        </Link>
      </div> */}

      {/* Recommended Topics */}
      <RecommendedTopics />

      {/* Sources */}
      <ArticleSource />

      {/* Saved Articles Shortcut */}
      {user && <RecentBookmarks />}
    </aside>
  )
}
