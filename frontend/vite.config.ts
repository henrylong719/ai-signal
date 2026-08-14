import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react-swc'
import { defineConfig } from 'vite'

/**
 * Optional same-origin API proxy for the dev server.
 *
 * Auth is cookie-based, and cookies are keyed by *host* (ports are
 * ignored). Local dev gets away with `localhost:5173` → `localhost:8000`
 * because both are host `localhost`. The Playwright stack does not: the
 * browser loads the app from `localhost:5173` while the API lives on
 * `backend:8000`, so every auth cookie — including the JS-readable
 * `is_logged_in` marker — lands on host `backend` and is invisible to the
 * app. Login appeared to succeed and the app still rendered logged-out.
 *
 * Setting VITE_API_PROXY_TARGET makes vite serve the API under the same
 * origin as the app. Pair it with an empty VITE_API_URL so the client
 * issues relative `/api/...` requests. Unset (normal dev), nothing changes.
 */
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET

// https://vitejs.dev/config/
export default defineConfig({
  server: apiProxyTarget
    ? {
        proxy: {
          // changeOrigin stays false so the upstream sees the browser's
          // Host. Set-Cookie then has no Domain attribute and the browser
          // stores it host-only against localhost, which is the point.
          '/api': { target: apiProxyTarget, changeOrigin: false },
        },
      }
    : undefined,
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
})
