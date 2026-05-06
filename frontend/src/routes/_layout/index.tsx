import { createFileRoute, Link } from "@tanstack/react-router"
import { LogInIcon } from "lucide-react"
import { useMemo, useRef, useState } from "react"
import {
  ArticleList,
  ArticleListState,
} from "@/components/Articles/ArticleList"
import { MobileSidebar, Sidebar } from "@/components/Landing/Sidebar"
import { useArticleFeed } from "@/hooks/useArticleFeed"
import { isLoggedIn } from "@/hooks/useAuth"
import { useForYouFeed } from "@/hooks/useForYouFeed"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "AI Signal",
      },
    ],
  }),
})

type Tab = "for-you" | "latest"

const tabs: { value: Tab; label: string }[] = [
  { value: "for-you", label: "For you" },
  { value: "latest", label: "Latest" },
]

function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("for-you")
  const feedTopRef = useRef<HTMLDivElement>(null)
  const latest = useArticleFeed()
  // useForYouFeed always runs, but its query needs auth — when the user
  // isn't logged in we render the sign-in CTA instead. Calling the hook
  // unconditionally keeps the hooks order stable.
  const forYou = useForYouFeed()

  // Build a stable id→reason map. ForYouArticle extends ArticlePublic so
  // the underlying article objects are compatible with ArticleList; the
  // reason is passed alongside via this map.
  const forYouReasons = useMemo(() => {
    const m = new Map<string, string | null>()
    for (const article of forYou.articles) {
      m.set(article.id, article.reason)
    }
    return m
  }, [forYou.articles])

  const handleTabChange = (tab: Tab) => {
    if (tab === activeTab) {
      return
    }

    setActiveTab(tab)
    window.requestAnimationFrame(() => {
      feedTopRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    })
  }

  return (
    <div className="flex">
      <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
        <div ref={feedTopRef} className="scroll-mt-20" aria-hidden="true" />
        <div className="sticky top-16 z-40 border-b border-slate-200 bg-white pt-6 sm:top-20">
          <div className="flex items-center">
            <MobileSidebar />
            <div className="flex gap-10">
              {tabs.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => handleTabChange(tab.value)}
                  className={`relative rounded-sm pb-5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
                    activeTab === tab.value
                      ? "text-slate-900"
                      : "text-slate-400 hover:text-slate-600"
                  }`}
                >
                  {tab.label}
                  {activeTab === tab.value && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 rounded-full" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {activeTab === "for-you" &&
          (isLoggedIn() ? (
            <ArticleList
              {...forYou}
              showDismiss
              reasons={forYouReasons}
              emptyTitle="No personalized signals yet"
              emptyDescription="Save a few articles or pick interests in Settings to start tailoring your feed."
            />
          ) : (
            <ArticleListState
              title="Sign in to personalize your feed"
              description="Your For You feed is built from articles you save, click, and the topics you tell us you care about."
              icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
              action={
                <Link
                  to="/login"
                  className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                >
                  Sign in
                </Link>
              }
            />
          ))}
        {activeTab === "latest" && <ArticleList {...latest} />}
      </div>
      <Sidebar />
    </div>
  )
}
