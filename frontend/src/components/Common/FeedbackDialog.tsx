import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2Icon, SendIcon } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import type { FeedbackCreate } from '@/client';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { LoadingButton } from '@/components/ui/loading-button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useFeedback } from '@/hooks/useFeedback';
import { cn } from '@/lib/utils';

const categoryOptions = [
  { value: 'general', label: 'General feedback' },
  { value: 'missing_topic_source_tag', label: 'Missing topic/source/tag' },
  { value: 'bad_recommendation', label: 'Bad recommendation' },
  { value: 'feature_request', label: 'Feature request' },
  { value: 'bug_report', label: 'Bug report' },
] as const satisfies ReadonlyArray<{
  value: FeedbackCreate['category'];
  label: string;
}>;

const formSchema = z.object({
  category: z.enum([
    'general',
    'missing_topic_source_tag',
    'bad_recommendation',
    'feature_request',
    'bug_report',
  ]),
  message: z
    .string()
    .trim()
    .min(10, 'Add at least 10 characters.')
    .max(2000, 'Keep it under 2,000 characters.'),
});

type FormData = z.infer<typeof formSchema>;

const defaultValues: FormData = {
  category: 'general',
  message: '',
};

function feedbackContext() {
  if (typeof window === 'undefined') {
    return undefined;
  }

  return {
    path: window.location.pathname,
    title: document.title,
    source: 'profile_menu',
  };
}

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FeedbackDialog({ open, onOpenChange }: FeedbackDialogProps) {
  const { submit, isSubmitting, isSuccess, isError, reset } = useFeedback();
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onBlur',
    defaultValues,
  });
  const message = form.watch('message');

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
    if (!nextOpen) {
      form.reset(defaultValues);
      reset();
    }
  };

  const onSubmit = (data: FormData) => {
    submit(
      {
        category: data.category,
        message: data.message.trim(),
        context: feedbackContext(),
      },
      {
        onSuccess: () => {
          form.reset(defaultValues);
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="gap-0 overflow-hidden border-slate-200/80 bg-white p-0 shadow-[0_22px_60px_rgba(15,23,42,0.18)] sm:max-w-[30rem] dark:border-border dark:bg-popover dark:shadow-[0_22px_60px_rgba(0,0,0,0.36)]">
        <DialogHeader className="border-b border-slate-100 px-5 py-5 text-left sm:px-6 dark:border-border">
          <DialogTitle className="font-display text-xl font-semibold tracking-normal text-slate-950 dark:text-foreground">
            Send feedback
          </DialogTitle>
          <DialogDescription className="text-sm leading-6 text-slate-500 dark:text-muted-foreground">
            Tell us what to improve.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-5 px-5 py-5 sm:px-6"
          >
            {isSuccess && (
              <div
                role="status"
                className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800 dark:border-emerald-400/25 dark:bg-emerald-400/10 dark:text-emerald-200"
              >
                <CheckCircle2Icon className="mt-0.5 h-4 w-4 shrink-0" />
                <span>Thanks. Your feedback was sent.</span>
              </div>
            )}

            {isError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:border-red-400/25 dark:bg-red-400/10 dark:text-red-200"
              >
                Could not send feedback. Please try again.
              </div>
            )}

            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                    Category
                  </FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      reset();
                      field.onChange(value);
                    }}
                  >
                    <FormControl>
                      <SelectTrigger className="h-10 w-full rounded-md border-slate-200 bg-white text-slate-800 shadow-sm shadow-slate-950/[0.02] focus:ring-slate-900/10 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:focus:ring-ring/15">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent className="border-slate-200 bg-white dark:border-border dark:bg-popover">
                      {categoryOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between gap-3">
                    <FormLabel className="text-sm font-medium text-slate-800 dark:text-foreground/88">
                      Message
                    </FormLabel>
                    <span
                      className={cn(
                        'text-xs text-slate-400 dark:text-muted-foreground/75',
                        message.length > 1900 && 'text-amber-600',
                      )}
                    >
                      {message.length}/2000
                    </span>
                  </div>
                  <FormControl>
                    <textarea
                      rows={5}
                      placeholder="What should change?"
                      className="min-h-32 w-full resize-none rounded-md border border-slate-200 bg-white px-3.5 py-3 text-sm leading-6 text-slate-900 shadow-sm shadow-slate-950/[0.02] outline-none transition-colors placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-900/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-border dark:bg-muted/35 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:focus:border-ring/55 dark:focus:ring-ring/15"
                      disabled={isSubmitting}
                      maxLength={2000}
                      {...field}
                      onChange={(event) => {
                        reset();
                        field.onChange(event);
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="border-t border-slate-100 pt-4 dark:border-border">
              <DialogClose asChild>
                <button
                  type="button"
                  className="inline-flex h-10 items-center justify-center rounded-md border border-slate-200 bg-white px-4 text-sm font-medium text-slate-600 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/10 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35"
                >
                  Cancel
                </button>
              </DialogClose>
              <LoadingButton
                type="submit"
                loading={isSubmitting}
                className="h-10 bg-slate-950 px-4 font-medium text-white shadow-sm shadow-slate-950/10 hover:bg-slate-800 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88"
              >
                <SendIcon className="h-4 w-4" />
                Send
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
