import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { ArticleList } from "@/components/Articles/ArticleList"
import { Sidebar } from "@/components/Landing/Sidebar"
import { useArticleFeed } from "@/hooks/useArticleFeed"

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
  const [activeTab, setActiveTab] = useState<Tab>("latest")
  const feed = useArticleFeed()

  return (
    <div className="flex">
      <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
        <div className="border-b border-slate-200 pt-6 sticky top-20 bg-white z-40">
          <div className="flex gap-10">
            {tabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveTab(tab.value)}
                className={`pb-5 text-sm font-medium transition-colors relative ${
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

        {activeTab === "for-you" && <div />}
        {activeTab === "latest" && <ArticleList {...feed} />}
      </div>
      <Sidebar />
    </div>
  )
}
