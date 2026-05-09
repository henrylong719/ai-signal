import { createFileRoute } from '@tanstack/react-router'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL, LEGAL_LAST_UPDATED } from '@/lib/legal'

export const Route = createFileRoute('/_layout/accessibility')({
  component: AccessibilityPage,
  head: () => ({
    meta: [
      { title: 'Accessibility — AI Signal' },
      {
        name: 'description',
        content:
          'How AI Signal approaches accessibility, what we already do, and how to report issues.',
      },
    ],
  }),
})

function AccessibilityPage() {
  return (
    <LegalPageLayout
      eyebrow="Accessibility"
      title="Accessibility Statement"
      intro="AI Signal is meant to be a calm, readable place. We want it to work for as many people as possible, including readers using assistive technology."
      lastUpdated={LEGAL_LAST_UPDATED}
    >
      <PolicySection title="Our intent">
        <p>
          We design AI Signal as a reading product first. That means we care
          about readable typography, generous spacing, predictable navigation,
          and a layout that does not shift around as content loads. We aim, over
          time, to align with the WCAG 2.1 AA guidelines.
        </p>
      </PolicySection>

      <PolicySection title="What we try to do today">
        <PolicyList
          items={[
            'Use semantic HTML where it is the right tool for the job.',
            'Support full keyboard navigation, including the support and footer links.',
            'Provide clear focus states on interactive elements.',
            'Maintain readable contrast in both light and dark themes.',
            'Use responsive layouts that work on phones, tablets, and desktops.',
            'Add accessible names to icon-only buttons such as theme toggles, search, and menu controls.',
            'Use alt text on meaningful imagery and avoid relying on color alone to communicate state.',
          ]}
        />
      </PolicySection>

      <PolicySection title="Where we still have work to do">
        <p>
          AI Signal is an evolving product. Some areas — especially dynamic feed
          states, deeply personalized panels, and admin tools — may not yet meet
          every guideline we want to hit. We are working on this and would
          rather hear about specific issues than claim more than we can deliver.
        </p>
      </PolicySection>

      <PolicySection title="Compatibility">
        <p>
          We test the product against current versions of major browsers, and we
          use VoiceOver and standard screen readers when verifying critical
          paths such as sign-in, saving an article, and changing preferences. If
          you rely on a specific assistive technology and something does not
          work as expected, please let us know — that feedback shapes what we
          fix next.
        </p>
      </PolicySection>

      <PolicySection title="Reporting an accessibility issue">
        <p>
          If you encounter an accessibility barrier — a missing label, a trap in
          the keyboard order, a contrast issue, anything — email{' '}
          <a
            href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
              'Accessibility issue',
            )}`}
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            {CONTACT_EMAIL}
          </a>{' '}
          with the page URL, a short description of the issue, your browser or
          device, and any assistive technology you used. We treat accessibility
          reports as priority work.
        </p>
      </PolicySection>
    </LegalPageLayout>
  )
}
