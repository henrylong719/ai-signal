import { useMutation } from '@tanstack/react-query'

import { type FeedbackCreate, FeedbackService } from '@/client'
import { handleError } from '@/utils'
import useCustomToast from './useCustomToast'

const submitFeedback = (requestBody: FeedbackCreate) =>
  FeedbackService.submitFeedback({ requestBody })

export function useFeedback() {
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      showSuccessToast('Feedback sent.')
    },
    onError: handleError.bind(showErrorToast),
  })

  return {
    submit: mutation.mutate,
    isSubmitting: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    reset: mutation.reset,
  }
}
