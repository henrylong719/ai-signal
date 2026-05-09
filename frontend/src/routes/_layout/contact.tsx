import { createFileRoute } from '@tanstack/react-router'
import { MailIcon } from 'lucide-react'
import {
  LegalPageLayout,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL } from '@/lib/legal'

export const Route = createFileRoute('/_layout/contact')({
  component: ContactPage,
  head: () => ({
    meta: [
      { title: 'Contact — AI Signal' },
      {
        name: 'description',
        content:
          'Reach out to AI Signal for feedback, bug reports, source suggestions, accessibility issues, or removal requests.',
      },
    ],
  }),
})

interface ReasonProps {
  title: string
  description: string
  subject: string
}

function ReasonRow({ title, description, subject }: ReasonProps) {
  const href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`
  return (
    <a
      href={href}
      className="group flex items-start justify-between gap-4 rounded-lg border border-slate-200/80 bg-white px-4 py-4 transition-colors hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 sm:px-5 dark:border-border dark:bg-card dark:hover:border-foreground/18 dark:hover:bg-accent dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
    >
      <div className="min-w-0">
        <p className="font-medium text-slate-950 dark:text-foreground">
          {title}
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          {description}
        </p>
      </div>
      <span className="mt-1 hidden text-xs font-medium text-slate-400 transition-colors group-hover:text-slate-700 sm:inline dark:text-muted-foreground/80 dark:group-hover:text-foreground/86">
        Email →
      </span>
    </a>
  )
}

function ContactPage() {
  return (
    <LegalPageLayout
      eyebrow="Contact"
      title="Get in touch"
      intro="AI Signal is a small project, and real feedback shapes what we build next. Pick the reason that fits your message — each link opens an email pre-tagged so it reaches the right place."
    >
      <PolicySection title="Email us">
        <p>
          For anything not covered below, write to{' '}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </PolicySection>

      <PolicySection title="Common reasons people reach out">
        <div className="grid gap-3">
          <ReasonRow
            title="Feedback or feature ideas"
            description="Tell us what is working, what is missing, and what would make AI Signal a better daily reading habit."
            subject="Feedback"
          />
          <ReasonRow
            title="Bug reports"
            description="Saw something broken, slow, or odd? Include what you did, what happened, and the browser/device if you can."
            subject="Bug report"
          />
          <ReasonRow
            title="Source suggestions"
            description="Suggest an AI lab, newsletter, blog, or research feed we should cover. Include the name and feed URL."
            subject="Source suggestion"
          />
          <ReasonRow
            title="Accessibility issues"
            description="Report keyboard, screen-reader, or contrast problems. We treat these as priority work."
            subject="Accessibility issue"
          />
          <ReasonRow
            title="Publisher requests"
            description="Request corrections, attribution updates, or removal of an article you publish. Email us from a domain tied to the publication when possible."
            subject="Publisher request"
          />
          <ReasonRow
            title="General questions"
            description="Anything else — partnerships, press, or just saying hello."
            subject="General question"
          />
        </div>
      </PolicySection>

      <PolicySection title="Response time">
        <p>
          AI Signal is run by a small team, so replies may take a few days. If a
          message is time-sensitive (security, legal, or accessibility), please
          say so in the subject line and we will prioritize it.
        </p>
        <p className="inline-flex items-center gap-2 text-sm text-slate-500 dark:text-muted-foreground">
          <MailIcon className="h-4 w-4 stroke-[1.7]" aria-hidden="true" />
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            {CONTACT_EMAIL}
          </a>
        </p>
      </PolicySection>
    </LegalPageLayout>
  )
}
