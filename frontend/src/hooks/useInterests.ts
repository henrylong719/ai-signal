import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  InterestsService,
  type UserInterestPublic,
  type UserInterestUpdate,
} from '@/client'
import { isLoggedIn } from '@/lib/auth-state'
import useCustomToast from './useCustomToast'

const INTERESTS_KEY = ['userInterests'] as const

const putInterests = (requestBody: UserInterestUpdate) =>
  InterestsService.updateInterests({ requestBody })

/**
 * Read + write the current user's stored interests.
 *
 * The query is gated on `isLoggedIn()` so anonymous visitors don't trigger
 * a 401. The PUT mutation also invalidates the For-You feed because
 * changing interests changes what should be recommended next time.
 *
 * The body now carries three fields — categories, tags, preferred_sources —
 * but the wire shape is unchanged for callers that only set the first two
 * (`preferred_sources` is optional on the request type).
 */
export function useInterests() {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const { data, isLoading, isError } = useQuery<UserInterestPublic, Error>({
    queryKey: INTERESTS_KEY,
    queryFn: () => InterestsService.readInterests(),
    enabled: isLoggedIn(),
  })

  const saveMutation = useMutation({
    mutationFn: putInterests,
    onMutate: async (newValues) => {
      await queryClient.cancelQueries({ queryKey: INTERESTS_KEY })
      const previous =
        queryClient.getQueryData<UserInterestPublic>(INTERESTS_KEY)
      // Optimistic: show the new selection immediately. Backend echoes
      // back the canonical (sorted, deduped, lowercased) version on success.
      // Fields not present in the update payload should retain their previous
      // value so a partial save (e.g. only sources changed) doesn't blank
      // out the others in the cache.
      queryClient.setQueryData<UserInterestPublic>(INTERESTS_KEY, {
        categories: newValues.categories ?? previous?.categories ?? [],
        tags: newValues.tags ?? previous?.tags ?? [],
        preferred_sources:
          newValues.preferred_sources ?? previous?.preferred_sources ?? [],
        updated_at: previous?.updated_at ?? null,
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(INTERESTS_KEY, context.previous)
      }
      showErrorToast('Could not save your preferences. Please try again.')
    },
    onSuccess: (data) => {
      // Replace the optimistic value with the canonical one returned by
      // the server. This catches normalization (e.g., "RAG " → "rag" for
      // tags, sort + dedupe for sources).
      queryClient.setQueryData(INTERESTS_KEY, data)
      showSuccessToast('Preferences saved.')
    },
    onSettled: () => {
      // Future For-You feed will key off this; invalidating now means
      // the next visit re-fetches with new preferences applied.
      queryClient.invalidateQueries({ queryKey: ['forYouFeed'] })
    },
  })

  return {
    interests: data,
    isLoading,
    isError,
    save: saveMutation.mutate,
    isSaving: saveMutation.isPending,
  }
}
