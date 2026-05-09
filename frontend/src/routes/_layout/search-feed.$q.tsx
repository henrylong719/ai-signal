import { createFileRoute } from '@tanstack/react-router'
import { ArticleList } from '@/components/Articles/ArticleList'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import { useArticleFeed } from '@/hooks/useArticleFeed'

export const Route = createFileRoute('/_layout/search-feed/$q')({
  component: SearchFeed,
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
