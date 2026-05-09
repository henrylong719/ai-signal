import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckIcon } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { UsersService, type UserUpdateMe } from '@/client'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoadingButton } from '@/components/ui/loading-button'
import useAuth from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { handleError } from '@/utils'

const formSchema = z.object({
  full_name: z.string().max(30).optional(),
  email: z.email({ message: 'Invalid email address' }),
})

type FormData = z.infer<typeof formSchema>

const UserInformation = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { user: currentUser } = useAuth()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      full_name: currentUser?.full_name ?? '',
      email: currentUser?.email ?? '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UserUpdateMe) =>
      UsersService.updateUserMe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast('Account details updated.')
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })

  const onSubmit = (data: FormData) => {
    const updateData: UserUpdateMe = {}

    // only include fields that have changed
    if (data.full_name !== (currentUser?.full_name ?? '')) {
      updateData.full_name = data.full_name || null
    }
    if (data.email !== currentUser?.email) {
      updateData.email = data.email
    }

    mutation.mutate(updateData)
  }

  return (
    <div className="w-full max-w-lg">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          <FormField
            control={form.control}
            name="full_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                  Full name
                </FormLabel>
                <FormControl>
                  <Input
                    type="text"
                    autoComplete="name"
                    className="h-10 rounded-md border-slate-200 bg-white px-3.5 text-sm shadow-sm shadow-slate-950/2 transition-colors placeholder:text-slate-400 focus-visible:border-slate-400 focus-visible:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                  Email address
                </FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    autoComplete="email"
                    className="h-10 rounded-md border-slate-200 bg-white px-3.5 text-sm shadow-sm shadow-slate-950/2 transition-colors placeholder:text-slate-400 focus-visible:border-slate-400 focus-visible:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="pt-2">
            <LoadingButton
              type="submit"
              size="sm"
              loading={mutation.isPending}
              disabled={!form.formState.isDirty}
              className="h-9 w-full rounded-full bg-slate-950 px-4 font-medium text-white shadow-sm hover:bg-slate-800 sm:w-auto dark:bg-foreground dark:text-background dark:hover:bg-foreground/92"
            >
              <CheckIcon className="h-4 w-4" />
              Save profile
            </LoadingButton>
          </div>
        </form>
      </Form>
    </div>
  )
}

export default UserInformation
