import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from '@tanstack/react-router'

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from '@/client'
import { trackGuestEvent } from '@/lib/analytics'
import { clearLoginState, isLoggedIn } from '@/lib/auth-state'
import { handleError } from '@/utils'
import useCustomToast from './useCustomToast'

const CURRENT_USER_STALE_TIME_MS = 1000 * 60 * 5
const CURRENT_USER_GC_TIME_MS = 1000 * 60 * 30

const useAuth = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  // currentUser query is gated on the marker cookie. The server still
  // does its own auth check — the marker is only for UI suppression.
  const {
    data: user,
    isLoading,
    isError,
  } = useQuery<UserPublic | null, Error>({
    queryKey: ['currentUser'],
    queryFn: () => UsersService.readUserMe(),
    enabled: isLoggedIn(),
    staleTime: CURRENT_USER_STALE_TIME_MS,
    gcTime: CURRENT_USER_GC_TIME_MS,
  })

  // Login no longer reads the response body — the access cookie is set
  // server-side via Set-Cookie headers. The SDK call still works because
  // the backend continues to return the JSON token shape for backward
  // compatibility with non-browser callers (CLI, tests).
  //
  // The `remember` flag is accepted but ignored: with cookie auth, the
  // refresh cookie's 30-day TTL handles long-term sessions automatically.
  // The "Remember me" checkbox in SignInScreen is now decorative;
  // follow-up work should remove it from the UI to avoid the implicit
  // promise that unchecking it shortens the session.
  const login = async (
    data: AccessToken & { remember?: boolean },
  ): Promise<void> => {
    const { remember: _ignored, ...credentials } = data
    await LoginService.loginAccessToken({ formData: credentials })
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async () => {
      // After login the marker cookie is set — invalidate any cached
      // queries that were gated on logged-in state.
      try {
        const currentUser = await UsersService.readUserMe()
        queryClient.setQueryData(['currentUser'], currentUser)
      } catch {
        queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      }

      if (location.pathname === '/login' || location.pathname === '/signup') {
        navigate({ to: '/' })
      }
    },
    onError: handleError.bind(showErrorToast),
  })

  // Backend issues a session on successful signup (sets all three auth
  // cookies via Set-Cookie), so the response itself logs the user in.
  // We just need to seed the currentUser cache and navigate.
  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: (user) => {
      // Guest funnel: a successful signup is the conversion event. We
      // pass ``forceWhenLoggedIn`` because by the time React re-renders,
      // ``isLoggedIn()`` may already return true (the marker cookie is
      // set by the backend on signup). Failures here never block the
      // post-signup navigate.
      trackGuestEvent('guest_signup_completed', {
        forceWhenLoggedIn: true,
        payload: { user_id: user.id },
      })
      queryClient.setQueryData(['currentUser'], user)
      navigate({ to: '/' })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  // Logout calls the server endpoint to clear all three auth cookies.
  // Best-effort: if the server is unreachable we still clear local state
  // and navigate, because leaving a stale "logged in" UI after an
  // explicit logout would be worse than swallowing the network error.
  const logout = async () => {
    try {
      await LoginService.logout()
    } catch {
      // Network error or server down — keep going, clear client state.
    }
    clearLoginState()
    queryClient.setQueryData(['currentUser'], null)
    queryClient.clear()
    navigate({ to: '/' })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
    isLoading,
    isError,
  }
}

export { isLoggedIn }
export default useAuth
