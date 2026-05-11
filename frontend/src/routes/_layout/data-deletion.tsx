import { createFileRoute } from '@tanstack/react-router';
import {
  LegalPageLayout,
  PolicySection,
} from '@/components/Legal/LegalPageLayout';
import { CONTACT_EMAIL } from '@/lib/legal';
import { buildPageMeta } from '@/lib/meta';

export const Route = createFileRoute('/_layout/data-deletion')({
  component: DataDeletionPage,
  head: () =>
    buildPageMeta({
      title: 'Data Deletion Instructions',
      description:
        'How to request deletion of your AI Signal account and personal data.',
      path: '/data-deletion',
    }),
});

function DataDeletionPage() {
  return (
    <LegalPageLayout
      eyebrow="Privacy"
      title="Data Deletion Instructions"
      intro="AI Signal users can request deletion of their account and personal data by following the steps below."
    >
      <PolicySection title="How to request deletion">
        <p>
          Send an email to{' '}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            {CONTACT_EMAIL}
          </a>{' '}
          with the subject line <strong>Data Deletion Request</strong>. Please
          include the email address associated with your AI Signal account so we
          can locate and remove your data.
        </p>
      </PolicySection>

      <PolicySection title="What happens next">
        <p>
          We will process deletion requests within a reasonable timeframe. Once
          complete, your account, saved articles, preferences, and reading
          history linked to your account will be deleted.
        </p>
      </PolicySection>
    </LegalPageLayout>
  );
}
