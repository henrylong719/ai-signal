import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
  useNavigate,
} from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { LoginService } from '@/client'
import {
  AUTH_INPUT_CLASS,
  AUTH_LABEL_CLASS,
  primaryButtonClass,
} from '@/components/Auth/AuthShared'
import { AuthLayout } from '@/components/Common/AuthLayout'
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
import { isLoggedIn } from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { cn } from '@/lib/utils'
import { handleError } from '@/utils'

const searchSchema = z.object({
  token: z.string().catch(''),
})

const formSchema = z
  .object({
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

export const Route = createFileRoute('/reset-password')({
  component: ResetPassword,
  validateSearch: searchSchema,
  beforeLoad: async ({ search }) => {
    if (isLoggedIn()) {
      throw redirect({ to: '/' })
    }
    if (!search.token) {
      throw redirect({ to: '/login' })
    }
  },
  head: () => ({
    meta: [
      {
        title: 'Set a new password - AI Signal',
      },
    ],
  }),
})

function ResetPassword() {
  const { token } = Route.useSearch()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const navigate = useNavigate()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      new_password: '',
      confirm_password: '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: { new_password: string; token: string }) =>
      LoginService.resetPassword({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast('Password updated. You can sign in now.')
      form.reset()
      navigate({ to: '/' })
    },
    onError: handleError.bind(showErrorToast),
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({ new_password: data.new_password, token })
  }

  return (
    <AuthLayout>
      <div className="flex flex-col gap-7">
        <header className="flex flex-col gap-2">
          <h1 className="font-serif text-[1.75rem] leading-[1.15] tracking-tight text-slate-950 dark:text-foreground">
            Set a new password
          </h1>
          <p className="text-[14px] leading-relaxed text-slate-500 dark:text-muted-foreground">
            Choose a new password to regain access to your AI Signal account.
          </p>
        </header>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col gap-5"
          >
            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>
                    New password
                  </FormLabel>
                  <FormControl>
                    <PasswordInput
                      autoComplete="new-password"
                      data-testid="new-password-input"
                      placeholder="At least 8 characters"
                      className={cn(AUTH_INPUT_CLASS, 'pr-12 sm:pr-16')}
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
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>
                    Confirm new password
                  </FormLabel>
                  <FormControl>
                    <PasswordInput
                      autoComplete="new-password"
                      data-testid="confirm-password-input"
                      placeholder="Re-enter your password"
                      className={cn(AUTH_INPUT_CLASS, 'pr-12 sm:pr-16')}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <LoadingButton
              type="submit"
              className={cn(primaryButtonClass, 'mt-1')}
              loading={mutation.isPending}
            >
              Update password
            </LoadingButton>
          </form>
        </Form>

        <p className="text-center text-sm text-slate-500 dark:text-muted-foreground">
          Remember your password?{' '}
          <RouterLink
            to="/login"
            className="font-semibold text-slate-950 underline-offset-4 hover:underline dark:text-foreground"
          >
            Log in
          </RouterLink>
        </p>
      </div>
    </AuthLayout>
  )
}
