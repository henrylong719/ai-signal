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
      <header className="pt-10 pb-8">
        <div className="text-center pb-5">
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 mb-3 tracking-tight">
            Your library
          </h1>
          <p className="text-lg text-slate-500 leading-relaxed font-serif">
            Articles you have saved for later.
          </p>
        </div>
      </header>
      <SavedArticleList />
    </div>
  )
}
