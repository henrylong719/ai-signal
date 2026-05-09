import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import { createRouter, RouterProvider } from '@tanstack/react-router';
import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { ApiError, OpenAPI } from './client';
import { ThemeProvider, useTheme } from './components/theme-provider';
import { Toaster } from './components/ui/sonner';
import './index.css';
import { authInterceptor } from './lib/auth-interceptor';
import { clearLoginState } from './lib/auth-state';
import { routeTree } from './routeTree.gen';

OpenAPI.BASE = import.meta.env.VITE_API_URL;
// Send cookies on cross-origin API calls. This is the load-bearing line
// for cookie-based auth — without it, axios won't include the access
// cookie in requests to a different origin (frontend on :5173, backend
// on :8000 in dev).
OpenAPI.WITH_CREDENTIALS = true;

// Response interceptor for the 401 → refresh → retry flow.
OpenAPI.interceptors.response.use(authInterceptor);

// Error handler for everything the auth interceptor doesn't catch.
// 401s are *handled* by the interceptor (refresh + retry), so they don't
// usually reach this point. If they do — meaning even after a refresh
// attempt the server still says no — fall through to the same logged-out
// flow as the interceptor's onRefreshFailure.
const handleApiError = (error: Error) => {
  if (error instanceof ApiError && error.status === 401) {
    clearLoginState();
    window.location.href = '/login';
  }
};

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
});

const router = createRouter({ routeTree });
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

function AppToaster() {
  const { resolvedTheme } = useTheme();

  return <Toaster theme={resolvedTheme} closeButton position="top-right" />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <AppToaster />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
