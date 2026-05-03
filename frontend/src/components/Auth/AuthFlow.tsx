import { zodResolver } from '@hookform/resolvers/zod';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import useAuth from '@/hooks/useAuth';
import useCustomToast from '@/hooks/useCustomToast';
import { cn } from '@/lib/utils';
import { SignInScreen } from './SignInScreen';
import { SignUpScreen } from './SignUpScreen';
import {
  type LoginFormData,
  loginSchema,
  type SignUpFormData,
  signUpSchema,
} from './authSchemas';
import type { AuthMode } from './authTypes';

export type { AuthMode } from './authTypes';

interface AuthFlowProps {
  className?: string;
  closeControl?: ReactNode;
  initialMode?: AuthMode;
}

const providerUnavailable =
  'Social sign-in needs backend OAuth configuration before it can be enabled.';

export function AuthFlow({
  className,
  closeControl,
  initialMode = 'sign-in',
}: AuthFlowProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [remember, setRemember] = useState(false);
  const { loginMutation, signUpMutation } = useAuth();
  const { showErrorToast } = useCustomToast();

  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      username: '',
      password: '',
    },
  });

  const signUpForm = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    mode: 'onBlur',
    criteriaMode: 'all',
    defaultValues: {
      email: '',
      full_name: '',
      password: '',
      confirm_password: '',
    },
  });

  const unavailableProvider = () => {
    showErrorToast(providerUnavailable);
  };

  const submitLogin = (data: LoginFormData) => {
    if (loginMutation.isPending) return;
    loginMutation.mutate({ ...data, remember });
  };

  const submitSignUp = (data: SignUpFormData) => {
    if (signUpMutation.isPending) return;

    const { confirm_password: _confirmPassword, ...submitData } = data;
    signUpMutation.mutate(submitData);
  };

  return (
    <section
      className={cn(
        'relative flex w-full flex-col items-center bg-white px-6 py-8 text-slate-950 sm:px-10 sm:py-8',
        className,
      )}
    >
      {closeControl}

      {mode === 'sign-in' ? (
        <SignInScreen
          form={loginForm}
          loading={loginMutation.isPending}
          onCreateAccount={() => setMode('sign-up')}
          onSocialProviderClick={unavailableProvider}
          onSubmit={submitLogin}
          remember={remember}
          setRemember={setRemember}
        />
      ) : (
        <SignUpScreen
          form={signUpForm}
          loading={signUpMutation.isPending}
          onSignIn={() => setMode('sign-in')}
          onSocialProviderClick={unavailableProvider}
          onSubmit={submitSignUp}
        />
      )}
    </section>
  );
}

export default AuthFlow;
