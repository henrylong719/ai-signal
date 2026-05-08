import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArticlesService } from '@/client'
import { isLoggedIn } from './useAuth'
import useCustomToast from './useCustomToast'

const SAVED_IDS_KEY = ['savedArticleIds']
const SAVED_ARTICLES_STALE_TIME_MS = 1000 * 60

export function useSavedArticles() {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const { data: savedIds } = useQuery({
    queryKey: SAVED_IDS_KEY,
    queryFn: () => ArticlesService.readSavedArticleIds(),
    enabled: isLoggedIn(),
    staleTime: SAVED_ARTICLES_STALE_TIME_MS,
  })

  const savedArticleIds = new Set(savedIds?.article_ids ?? [])

  const saveMutation = useMutation({
    mutationFn: (articleId: string) =>
      ArticlesService.saveArticle({ articleId }),
    onMutate: async (articleId) => {
      await queryClient.cancelQueries({ queryKey: SAVED_IDS_KEY })
      const previous = queryClient.getQueryData(SAVED_IDS_KEY)
      queryClient.setQueryData(
        SAVED_IDS_KEY,
        (old: { article_ids: string[] } | undefined) => ({
          article_ids: [...(old?.article_ids ?? []), articleId],
        }),
      )
      return { previous }
    },
    onError: (_err, _articleId, context) => {
      queryClient.setQueryData(SAVED_IDS_KEY, context?.previous)
      showErrorToast('Could not save this article. Please try again.')
    },
    onSuccess: () => {
      showSuccessToast('Saved to your reading list.')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SAVED_IDS_KEY })
      queryClient.invalidateQueries({ queryKey: ['savedArticles'] })
    },
  })

  const unsaveMutation = useMutation({
    mutationFn: (articleId: string) =>
      ArticlesService.unsaveArticle({ articleId }),
    onMutate: async (articleId) => {
      await queryClient.cancelQueries({ queryKey: SAVED_IDS_KEY })
      const previous = queryClient.getQueryData(SAVED_IDS_KEY)
      queryClient.setQueryData(
        SAVED_IDS_KEY,
        (old: { article_ids: string[] } | undefined) => ({
          article_ids: (old?.article_ids ?? []).filter(
            (id) => id !== articleId,
          ),
        }),
      )
      return { previous }
    },
    onError: (_err, _articleId, context) => {
      queryClient.setQueryData(SAVED_IDS_KEY, context?.previous)
      showErrorToast('Could not remove this article. Please try again.')
    },
    onSuccess: () => {
      showSuccessToast('Removed from your reading list.')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SAVED_IDS_KEY })
      queryClient.invalidateQueries({ queryKey: ['savedArticles'] })
    },
  })

  const toggleSave = (articleId: string) => {
    if (savedArticleIds.has(articleId)) {
      unsaveMutation.mutate(articleId)
    } else {
      saveMutation.mutate(articleId)
    }
  }

  return { savedArticleIds, toggleSave }
}
