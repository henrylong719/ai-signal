import { MenuIcon, SparklesIcon } from "lucide-react"
import { type CSSProperties, useLayoutEffect, useRef, useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import useAuth from "@/hooks/useAuth"
import ArticleSource from "./ArticleSource"
import RecentBookmarks from "./RecentBookmarks"
import RecommendedTopics from "./RecommendedTopics"

function SidebarSections() {
  const { user } = useAuth()

  return (
    <>
      <RecommendedTopics />
      <ArticleSource />
      {user && <RecentBookmarks />}
    </>
  )
}

export function MobileSidebar() {
  return (
    <div className="lg:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <button
            type="button"
            aria-label="Open explore menu"
            className="mr-4 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
          >
            <MenuIcon className="h-5 w-5 stroke-[1.7]" />
          </button>
        </SheetTrigger>

        <SheetContent side="left" className="w-[88vw] max-w-sm overflow-y-auto">
          <SheetHeader className="border-b border-slate-100 px-5 py-5">
            <SheetTitle className="flex items-center gap-2 text-slate-950">
              <SparklesIcon className="h-4 w-4 stroke-[1.8] text-slate-400" />
              Explore AI Signal
            </SheetTitle>
            <SheetDescription>
              Browse topics, sources, and saved articles.
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-8 px-5 pb-8 pt-5">
            <SidebarSections />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}

export function Sidebar() {
  const sidebarRef = useRef<HTMLElement>(null)
  const [sidebarHeight, setSidebarHeight] = useState(0)

  useLayoutEffect(() => {
    const sidebar = sidebarRef.current

    if (!sidebar) {
      return
    }

    const updateHeight = () => {
      setSidebarHeight(Math.ceil(sidebar.getBoundingClientRect().height))
    }

    updateHeight()

    if (typeof ResizeObserver === "undefined") {
      return
    }

    const observer = new ResizeObserver(updateHeight)
    observer.observe(sidebar)

    return () => observer.disconnect()
  }, [])

  // When the rail is taller than the viewport, the negative top lets it
  // scroll with the page until its bottom edge reaches the viewport.
  const sidebarStyle: CSSProperties = {
    top:
      sidebarHeight > 0
        ? `min(3rem, calc(100vh - ${sidebarHeight}px - 2rem))`
        : "3rem",
  }

  return (
    <aside
      ref={sidebarRef}
      style={sidebarStyle}
      className="flex-0 hidden space-y-10 self-start border-l border-slate-100 pb-8 pt-8 md:flex-2 lg:sticky lg:col-span-4 lg:block lg:pl-10"
    >
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

      <SidebarSections />
    </aside>
  )
}
