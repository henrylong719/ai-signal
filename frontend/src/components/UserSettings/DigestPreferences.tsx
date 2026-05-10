import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDaysIcon, CheckIcon, ClockIcon } from 'lucide-react';
import { useMemo, useState } from 'react';

import { type DigestPreferencesUpdate, UsersService } from '@/client';
import { LoadingButton } from '@/components/ui/loading-button';
import useAuth from '@/hooks/useAuth';
import useCustomToast from '@/hooks/useCustomToast';
import { cn } from '@/lib/utils';

function detectTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

/**
 * Settings panel for the daily-digest email opt-in.
 *
 * Reads the current preference from the cached ``user`` and writes via
 * the dedicated digest-preferences endpoint. We refresh the timezone
 * every time the panel renders so the user sees the value the digest
 * sender would use right now (e.g. when they've moved devices).
 *
 * Submit is a single button rather than an instant-toggle so a casual
 * mistap doesn't silently change a recurring email subscription —
 * matches Substack/Medium etiquette for newsletter prefs.
 */
const DigestPreferences = () => {
  const queryClient = useQueryClient();
  const { showSuccessToast, showErrorToast } = useCustomToast();
  const { user } = useAuth();

  const detectedZone = useMemo(() => detectTimezone(), []);
  const initialEnabled = user?.daily_digest_enabled ?? false;
  const [enabled, setEnabled] = useState(initialEnabled);

  // The browser's resolvedOptions().timeZone is the source of truth for
  // "where the user is now"; we send it on save so the scheduler fires
  // at the user's local 6am. If the cached value already matches we
  // skip sending it to keep the request payload obvious.
  const timezoneToSend =
    detectedZone && detectedZone !== user?.timezone ? detectedZone : null;

  const mutation = useMutation({
    mutationFn: (body: DigestPreferencesUpdate) =>
      UsersService.updateDigestPreferences({ requestBody: body }),
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], data);
      showSuccessToast(
        data.daily_digest_enabled
          ? 'Daily digest is on. See you at 8 am.'
          : 'Daily digest is off.',
      );
    },
    onError: () => {
      showErrorToast('Could not update your digest preferences.');
    },
  });

  const dirty = enabled !== initialEnabled;

  const handleSave = () => {
    mutation.mutate({
      daily_digest_enabled: enabled,
      timezone: timezoneToSend,
    });
  };

  const displayedZone = user?.timezone ?? detectedZone ?? 'UTC';

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => setEnabled((v) => !v)}
        aria-pressed={enabled}
        className={cn(
          'flex w-full items-start gap-3 rounded-lg border px-4 py-4 text-left transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
          enabled
            ? 'border-slate-950 bg-slate-950 text-white dark:border-primary dark:bg-primary dark:text-primary-foreground'
            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 dark:border-border dark:bg-card/45 dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent',
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border',
            enabled
              ? 'border-white/45 bg-white/10 dark:border-primary-foreground/45 dark:bg-primary-foreground/10'
              : 'border-slate-300 bg-white dark:border-border dark:bg-background/20',
          )}
        >
          <CheckIcon
            className={cn(
              'h-3.5 w-3.5 stroke-[2.2]',
              enabled ? 'opacity-100' : 'opacity-0',
            )}
          />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2 text-sm font-semibold">
            <CalendarDaysIcon
              className="h-4 w-4 stroke-[1.8]"
              aria-hidden="true"
            />
            Daily digest at 8 am
          </span>
          <span
            className={cn(
              'mt-1 block text-xs leading-5',
              enabled
                ? 'text-white/75 dark:text-primary-foreground/80'
                : 'text-slate-500 dark:text-muted-foreground',
            )}
          >
            One email per day, grouped by signal area, in your local time.
            Unsubscribe anytime from the footer of every email.
          </span>
        </span>
      </button>

      <p className="inline-flex items-center gap-2 text-xs text-slate-500 dark:text-muted-foreground">
        <ClockIcon className="h-3.5 w-3.5 stroke-[1.7]" aria-hidden="true" />
        <span>
          Timezone:{' '}
          <span className="font-medium text-slate-700 dark:text-foreground/86">
            {displayedZone}
          </span>
          {detectedZone && detectedZone !== user?.timezone && (
            <>
              {' '}
              — will update to{' '}
              <span className="font-medium text-slate-700 dark:text-foreground/86">
                {detectedZone}
              </span>{' '}
              on save
            </>
          )}
        </span>
      </p>

      <div className="flex justify-end">
        <LoadingButton
          onClick={handleSave}
          loading={mutation.isPending}
          disabled={!dirty && !timezoneToSend}
          className="inline-flex h-10 items-center rounded-full bg-slate-950 px-5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92"
        >
          Save preference
        </LoadingButton>
      </div>
    </div>
  );
};

export default DigestPreferences;
