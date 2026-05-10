import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
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
import { Input } from '@/components/ui/input'
import { LoadingButton } from '@/components/ui/loading-button'
import { isLoggedIn } from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { cn } from '@/lib/utils'
import { handleError } from '@/utils'

const formSchema = z.object({
  email: z.email(),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute('/recover-password')({
  component: RecoverPassword,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: '/',
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: 'Reset your password - AI Signal',
      },
    ],
  }),
})

function RecoverPassword() {
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: '',
    },
  })
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({
      email: data.email,
    })
  }

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showSuccessToast('Recovery email sent. Check your inbox.')
      form.reset()
    },
    onError: handleError.bind(showErrorToast),
  })

  const onSubmit = async (data: FormData) => {
    if (mutation.isPending) return
    mutation.mutate(data)
  }

  return (
    <AuthLayout>
      <div className="flex flex-col gap-7">
        <header className="flex flex-col gap-2">
          <h1 className="font-serif text-[1.75rem] leading-[1.15] tracking-tight text-slate-950 dark:text-foreground">
            Reset your password
          </h1>
          <p className="text-[14px] leading-relaxed text-slate-500 dark:text-muted-foreground">
            Enter your email and we&apos;ll send you a secure link to reset your
            password.
          </p>
        </header>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col gap-5"
          >
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>Email</FormLabel>
                  <FormControl>
                    <Input
                      autoComplete="email"
                      data-testid="email-input"
                      placeholder="you@example.com"
                      type="email"
                      className={AUTH_INPUT_CLASS}
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
              Send reset link
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
