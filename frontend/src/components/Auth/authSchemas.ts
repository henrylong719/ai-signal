import { z } from 'zod'
import type { Body_login_login_access_token as AccessToken } from '@/client'

export const loginSchema = z.object({
  username: z.email(),
  password: z
    .string()
    .min(1, { message: 'Password is required' })
    .min(8, { message: 'Password must be at least 8 characters' }),
}) satisfies z.ZodType<AccessToken>

export const signUpSchema = z
  .object({
    email: z.email(),
    full_name: z.string().min(1, { message: 'Full Name is required' }),
    password: z
      .string()
      .min(1, { message: 'Password is required' })
      .min(8, { message: 'Password must be at least 8 characters' }),
    confirm_password: z
      .string()
      .min(1, { message: 'Password confirmation is required' }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ['confirm_password'],
  })

export type LoginFormData = z.infer<typeof loginSchema>
export type SignUpFormData = z.infer<typeof signUpSchema>
