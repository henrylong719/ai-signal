// Note: the `PrivateService` is only available when generating the client
// for local environments
import { OpenAPI, PrivateService } from '../../src/client'

// Node-side base URL, not the browser's. The browser talks to the API on
// its own origin (vite proxies /api) so that cookie-based auth works; this
// module runs in the test process, has no cookie jar to protect, and so
// addresses the backend container directly.
OpenAPI.BASE = process.env.PLAYWRIGHT_API_URL ?? process.env.VITE_API_URL ?? ''

export const createUser = async ({
  email,
  password,
}: {
  email: string
  password: string
}) => {
  return await PrivateService.createUser({
    requestBody: {
      email,
      password,
      is_verified: true,
      full_name: 'Test User',
    },
  })
}
