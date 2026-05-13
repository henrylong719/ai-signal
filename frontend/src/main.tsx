import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { Analytics } from '@vercel/analytics/react'
import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { OpenAPI } from './client'
import { ThemeProvider, useTheme } from './components/theme-provider'
import { Toaster } from './components/ui/sonner'
import './index.css'
import { authInterceptor } from './lib/auth-interceptor'
import { routeTree } from './routeTree.gen'

OpenAPI.BASE = import.meta.env.VITE_API_URL
// Send cookies on cross-origin API calls. This is the load-bearing line
// for cookie-based auth — without it, axios won't include the access
// cookie in requests to a different origin (frontend on :5173, backend
// on :8000 in dev).
OpenAPI.WITH_CREDENTIALS = true

// Response interceptor for the 401 → refresh → retry flow. The
// interceptor owns *all* auth-driven redirects: a 401 that reaches
// React Query past this point means the refresh attempt was transient
// (network/5xx) and the user should stay logged in for the next try.
OpenAPI.interceptors.response.use(authInterceptor)

const queryClient = new QueryClient({
  queryCache: new QueryCache(),
  mutationCache: new MutationCache(),
})

const router = createRouter({ routeTree })
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

function AppToaster() {
  const { resolvedTheme } = useTheme()

  return <Toaster theme={resolvedTheme} closeButton position="top-right" />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <AppToaster />
        <Analytics />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
