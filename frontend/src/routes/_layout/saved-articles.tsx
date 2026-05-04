import { createFileRoute } from "@tanstack/react-router"
import { SavedArticleList } from "@/components/Articles/SavedArticleList"

export const Route = createFileRoute("/_layout/saved-articles")({
  component: SavedArticles,
  head: () => ({
    meta: [
      {
        title: "Your library",
      },
    ],
  }),
})

function SavedArticles() {
  return (
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 tracking-tight">
          Your library
        </h1>
        <p className="mt-3 text-lg text-slate-500 leading-relaxed font-serif">
          Articles you have saved for later.
        </p>
      </header>
      <SavedArticleList />
    </div>
  )
}
