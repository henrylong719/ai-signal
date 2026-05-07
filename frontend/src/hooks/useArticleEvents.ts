import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { ArticlesService } from '@/client'
import useCustomToast from './useCustomToast'

/**
 * Dismiss-article mutation with session-local optimistic state.
 *
 * Model: the server is the source of truth — dismissals live in the
 * `article_events` table and are hard-filtered from the For-You feed by
 * the recommender. The frontend doesn't need to know across sessions
 * which articles were dismissed because they won't appear in the feed
 * response anyway.
 *
 * What we DO need is *within-session* tracking, so an article disappears
 * from the visible list the moment the user clicks dismiss. That's what
 * the in-memory `dismissedIds` set provides. It's reset on page reload,
 * which is fine — by then the server-side filter has taken over.
 */
export function useDismissArticle() {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  // Session-local set of dismissed article IDs. The list component
  // reads this and filters dismissed articles out of the rendered feed.
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => new Set())

  const dismissMutation = useMutation({
    mutationFn: (articleId: string) =>
      ArticlesService.dismissArticle({ articleId }),
    onMutate: async (articleId) => {
      // Optimistically add to the dismissed set. If the request fails,
      // we'll remove it again in onError.
      setDismissedIds((prev) => {
        const next = new Set(prev)
        next.add(articleId)
        return next
      })
      return { articleId }
    },
    onError: (_err, _articleId, context) => {
      if (context?.articleId) {
        setDismissedIds((prev) => {
          const next = new Set(prev)
          next.delete(context.articleId)
          return next
        })
      }
      showErrorToast('Could not dismiss article. Please try again.')
    },
    onSettled: () => {
      // The For-You feed query (when we add it) will be invalidated here
      // so the next paint reflects the server-side filter.
      queryClient.invalidateQueries({ queryKey: ['forYouFeed'] })
    },
  })

  return {
    dismissedIds,
    dismiss: (articleId: string) => dismissMutation.mutate(articleId),
    isDismissing: dismissMutation.isPending,
  }
}
