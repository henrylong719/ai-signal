import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  InterestsService,
  type UserInterestPublic,
  type UserInterestUpdate,
} from "@/client"
import { isLoggedIn } from "@/lib/auth-state"
import useCustomToast from "./useCustomToast"

const INTERESTS_KEY = ["userInterests"] as const

const putInterests = (requestBody: UserInterestUpdate) =>
  InterestsService.updateInterests({ requestBody })

/**
 * Read + write the current user's stored interests.
 *
 * The query is gated on `isLoggedIn()` so anonymous visitors don't trigger
 * a 401. The PUT mutation also invalidates the For-You feed because
 * changing interests changes what should be recommended next time.
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
      queryClient.setQueryData<UserInterestPublic>(INTERESTS_KEY, {
        categories: newValues.categories ?? [],
        tags: newValues.tags ?? [],
        updated_at: previous?.updated_at ?? null,
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(INTERESTS_KEY, context.previous)
      }
      showErrorToast("Could not save your interests. Please try again.")
    },
    onSuccess: (data) => {
      // Replace the optimistic value with the canonical one returned by
      // the server. This catches normalization (e.g., "RAG " → "rag").
      queryClient.setQueryData(INTERESTS_KEY, data)
      showSuccessToast("Interests saved.")
    },
    onSettled: () => {
      // Future For-You feed will key off this; invalidating now means
      // the next visit re-fetches with new interests applied.
      queryClient.invalidateQueries({ queryKey: ["forYouFeed"] })
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
