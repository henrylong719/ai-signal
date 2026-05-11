import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { KeyRoundIcon } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { type UpdatePassword, UsersService } from '@/client'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { LoadingButton } from '@/components/ui/loading-button'
import { PasswordInput } from '@/components/ui/password-input'
import useCustomToast from '@/hooks/useCustomToast'
import { handleError } from '@/utils'

const formSchema = z
  .object({
    current_password: z
      .string()
      .min(1, { message: 'Password is required' })
      .min(8, { message: 'Password must be at least 8 characters' }),
    new_password: z
      .string()
      .min(1, { message: 'Password is required' })
      .min(8, { message: 'Password must be at least 8 characters' }),
    confirm_password: z
      .string()
      .min(1, { message: 'Password confirmation is required' }),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "The passwords don't match",
    path: ['confirm_password'],
  })

type FormData = z.infer<typeof formSchema>

const ChangePassword = () => {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onSubmit',
    criteriaMode: 'all',
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UpdatePassword) =>
      UsersService.updatePasswordMe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast('Password updated.')
      form.reset()
    },
    onError: handleError.bind(showErrorToast),
  })

  const onSubmit = async (data: FormData) => {
    mutation.mutate(data)
  }

  return (
    <div className="w-full max-w-lg">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          <FormField
            control={form.control}
            name="current_password"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                  Current password
                </FormLabel>
                <FormControl>
                  <PasswordInput
                    data-testid="current-password-input"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    aria-invalid={fieldState.invalid}
                    className="h-10 rounded-md border-slate-200 bg-white pl-3.5 pr-10 text-sm shadow-sm shadow-slate-950/[0.02] transition-colors focus-visible:border-slate-400 focus-visible:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="new_password"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                  New password
                </FormLabel>
                <FormControl>
                  <PasswordInput
                    data-testid="new-password-input"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    aria-invalid={fieldState.invalid}
                    className="h-10 rounded-md border-slate-200 bg-white pl-3.5 pr-10 text-sm shadow-sm shadow-slate-950/[0.02] transition-colors focus-visible:border-slate-400 focus-visible:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="confirm_password"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                  Confirm new password
                </FormLabel>
                <FormControl>
                  <PasswordInput
                    data-testid="confirm-password-input"
                    autoComplete="new-password"
                    placeholder="••••••••"
                    aria-invalid={fieldState.invalid}
                    className="h-10 rounded-md border-slate-200 bg-white pl-3.5 pr-10 text-sm shadow-sm shadow-slate-950/[0.02] transition-colors focus-visible:border-slate-400 focus-visible:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <LoadingButton
            type="submit"
            loading={mutation.isPending}
            size="sm"
            className="h-9 w-full rounded-full bg-slate-950 px-4 font-medium text-white shadow-sm hover:bg-slate-800 sm:w-auto dark:bg-foreground dark:text-background dark:hover:bg-foreground/92"
          >
            <KeyRoundIcon className="h-4 w-4" />
            Update password
          </LoadingButton>
        </form>
      </Form>
    </div>
  )
}

export default ChangePassword
