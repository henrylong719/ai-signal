import { createFileRoute } from '@tanstack/react-router'
import { ArticleList } from '@/components/Articles/ArticleList'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import { useArticleFeed } from '@/hooks/useArticleFeed'

export const Route = createFileRoute('/_layout/search-feed/$q')({
  component: SearchFeed,
  // Search-results pages aren't crawl targets — their content depends on
  // the user's query and the live article index. Set the tab title for
  // back-button clarity and tell crawlers not to index.
  head: ({ params }) => ({
    meta: [
      { title: `Search: ${params.q} — AI Signal` },
      { name: 'robots', content: 'noindex,follow' },
    ],
  }),
})

function SearchFeed() {
  const { q } = Route.useParams()

  const { dataUpdatedAt: _latestUpdatedAt, ...feed } = useArticleFeed({
    search: q,
  })

  return (
    <PageContainer variant="default">
      <PageHeader
        eyebrow="Search results"
        title={`"${q}"`}
        titleClassName="break-words"
        description="Matching articles from across the AI Signal source network."
        descriptionClassName="max-w-xl"
      />
      <ArticleList
        {...feed}
        emptyTitle={`No results for "${q}"`}
        emptyDescription="Try a different phrase, check your spelling, or browse the latest AI signals."
        errorTitle="Could not load search results"
      />
    </PageContainer>
  )
}
