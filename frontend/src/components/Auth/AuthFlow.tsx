import { zodResolver } from "@hookform/resolvers/zod"
import type { ReactNode } from "react"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { OpenAPI } from "@/client"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import {
  type LoginFormData,
  loginSchema,
  type SignUpFormData,
  signUpSchema,
} from "./authSchemas"
import type { AuthMode } from "./authTypes"
import { SignInScreen } from "./SignInScreen"
import { SignUpScreen } from "./SignUpScreen"
import type { SocialAuthProvider } from "./SocialLoginButtons"

export type { AuthMode } from "./authTypes"

interface AuthFlowProps {
  className?: string
  closeControl?: ReactNode
  initialMode?: AuthMode
}

export function AuthFlow({
  className,
  closeControl,
  initialMode = "sign-in",
}: AuthFlowProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [remember, setRemember] = useState(false)
  const { loginMutation, signUpMutation } = useAuth()
  const { showErrorToast } = useCustomToast()
  const socialErrorShown = useRef(false)

  useEffect(() => {
    const socialError = new URLSearchParams(window.location.search).get(
      "social_error",
    )
    if (socialError && !socialErrorShown.current) {
      socialErrorShown.current = true
      showErrorToast(socialError)

      const nextUrl = new URL(window.location.href)
      nextUrl.searchParams.delete("social_error")
      window.history.replaceState(null, "", nextUrl)
    }
  }, [showErrorToast])

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const signUpForm = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })

  const startSocialLogin = (provider: SocialAuthProvider) => {
    window.location.href = `${OpenAPI.BASE}/api/v1/login/${provider}`
  }

  const submitLogin = (data: LoginFormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate({ ...data, remember })
  }

  const submitSignUp = (data: SignUpFormData) => {
    if (signUpMutation.isPending) return

    const { confirm_password: _confirmPassword, ...submitData } = data
    signUpMutation.mutate(submitData)
  }

  return (
    <section
      className={cn(
        "relative flex w-full flex-col items-center bg-white px-6 py-8 text-slate-950 sm:px-10 sm:py-8 dark:bg-slate-950 dark:text-slate-100",
        className,
      )}
    >
      {closeControl}

      {mode === "sign-in" ? (
        <SignInScreen
          form={loginForm}
          loading={loginMutation.isPending}
          onCreateAccount={() => setMode("sign-up")}
          onSocialProviderClick={startSocialLogin}
          onSubmit={submitLogin}
          remember={remember}
          setRemember={setRemember}
        />
      ) : (
        <SignUpScreen
          form={signUpForm}
          loading={signUpMutation.isPending}
          onSignIn={() => setMode("sign-in")}
          onSocialProviderClick={startSocialLogin}
          onSubmit={submitSignUp}
        />
      )}
    </section>
  )
}

export default AuthFlow
