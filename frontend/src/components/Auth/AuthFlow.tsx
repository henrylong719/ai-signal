import { zodResolver } from '@hookform/resolvers/zod'
import type { ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { OpenAPI } from '@/client'
import useAuth from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { cn } from '@/lib/utils'
import { extractErrorMessage } from '@/utils'
import { AuthIntro } from './AuthIntro'
import {
  type LoginFormData,
  loginSchema,
  type SignUpFormData,
  signUpSchema,
} from './authSchemas'
import type { AuthMode } from './authTypes'
import { SignInScreen } from './SignInScreen'
import { SignUpScreen } from './SignUpScreen'
import {
  type SocialAuthProvider,
  SocialLoginButtons,
} from './SocialLoginButtons'

export type { AuthMode } from './authTypes'

interface AuthFlowProps {
  className?: string
  closeControl?: ReactNode
  description?: string
  initialMode?: AuthMode
  title?: string
}

export function AuthFlow({
  className,
  closeControl,
  description = 'Sign in to save articles, tune your feed, and keep your preferences in sync.',
  initialMode = 'sign-in',
  title = 'Welcome to AI Signal',
}: AuthFlowProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [authStep, setAuthStep] = useState<'providers' | 'email'>('providers')
  const { loginMutation, signUpMutation } = useAuth()
  const { showErrorToast } = useCustomToast()
  const socialErrorShown = useRef(false)

  useEffect(() => {
    const socialError = new URLSearchParams(window.location.search).get(
      'social_error',
    )
    if (socialError && !socialErrorShown.current) {
      socialErrorShown.current = true
      showErrorToast(socialError)

      const nextUrl = new URL(window.location.href)
      nextUrl.searchParams.delete('social_error')
      window.history.replaceState(null, '', nextUrl)
    }
  }, [showErrorToast])

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      username: '',
      password: '',
    },
  })

  const signUpForm = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      email: '',
      full_name: '',
      password: '',
    },
  })

  const startSocialLogin = (provider: SocialAuthProvider) => {
    window.location.href = `${OpenAPI.BASE}/api/v1/login/${provider}`
  }

  const submitLogin = (data: LoginFormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  const submitSignUp = (data: SignUpFormData) => {
    if (signUpMutation.isPending) return

    signUpMutation.mutate(data)
  }

  const switchEmailMode = (nextMode: AuthMode) => {
    setMode(nextMode)
  }

  return (
    <section
      className={cn(
        'relative flex w-full flex-col items-center bg-white px-6 pb-9 pt-12 text-slate-950 sm:px-10 sm:pb-10 sm:pt-14 dark:bg-card dark:text-card-foreground',
        className,
      )}
    >
      {closeControl}

      {authStep === 'providers' ? (
        <>
          <AuthIntro title={title} description={description} />
          <div className="mt-8 w-full">
            <SocialLoginButtons
              onEmailClick={() => setAuthStep('email')}
              onProviderClick={startSocialLogin}
            />
          </div>
          <p className="mt-5 max-w-82 text-center text-xs leading-relaxed text-slate-500 dark:text-muted-foreground">
            We&apos;ll take you back to your feed after sign-in.
          </p>
        </>
      ) : mode === 'sign-in' ? (
        <SignInScreen
          errorMessage={
            loginMutation.error
              ? extractErrorMessage(loginMutation.error)
              : undefined
          }
          form={loginForm}
          loading={loginMutation.isPending}
          onBackToProviders={() => setAuthStep('providers')}
          onCreateAccount={() => switchEmailMode('sign-up')}
          onSubmit={submitLogin}
        />
      ) : (
        <SignUpScreen
          form={signUpForm}
          loading={signUpMutation.isPending}
          onBackToProviders={() => setAuthStep('providers')}
          onSignIn={() => switchEmailMode('sign-in')}
          onSubmit={submitSignUp}
        />
      )}
    </section>
  )
}

export default AuthFlow
