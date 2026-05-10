import { useMutation } from '@tanstack/react-query'

import { type SubscriptionCreate, SubscriptionsService } from '@/client'
import { handleError } from '@/utils'
import useCustomToast from './useCustomToast'

const subscribe = (requestBody: SubscriptionCreate) =>
  SubscriptionsService.createSubscription({ requestBody })

export function useSubscribe() {
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: subscribe,
    onSuccess: () => {
      showSuccessToast("You're subscribed to the daily digest.")
    },
    onError: handleError.bind(showErrorToast),
  })

  return {
    submit: mutation.mutate,
    isSubmitting: mutation.isPending,
    isSuccess: mutation.isSuccess,
    reset: mutation.reset,
  }
}
