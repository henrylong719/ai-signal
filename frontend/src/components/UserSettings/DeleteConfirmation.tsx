import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2Icon } from 'lucide-react'
import { useForm } from 'react-hook-form'

import { UsersService } from '@/client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { LoadingButton } from '@/components/ui/loading-button'
import useAuth from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { handleError } from '@/utils'

const DeleteConfirmation = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleSubmit } = useForm()
  const { logout } = useAuth()

  const mutation = useMutation({
    mutationFn: () => UsersService.deleteUserMe(),
    onSuccess: () => {
      showSuccessToast('Your account has been successfully deleted')
      logout()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
    },
  })

  const onSubmit = async () => {
    mutation.mutate()
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-9 w-full border-red-200 bg-white px-4 font-medium text-red-600 shadow-sm hover:bg-red-50 hover:text-red-700 sm:w-auto dark:border-red-400/25 dark:bg-transparent dark:text-red-300 dark:shadow-none dark:hover:bg-red-400/10 dark:hover:text-red-200"
        >
          <Trash2Icon className="h-4 w-4" />
          Delete account
        </Button>
      </DialogTrigger>
      <DialogContent className="rounded-lg border-red-100 dark:border-red-400/25">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader className="pr-6">
            <DialogTitle className="text-slate-950 dark:text-foreground">
              Delete account?
            </DialogTitle>
            <DialogDescription className="leading-6">
              All your account data will be{' '}
              <strong>permanently deleted.</strong> If you are sure, please
              confirm below. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              <Trash2Icon className="h-4 w-4" />
              Delete account
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default DeleteConfirmation
