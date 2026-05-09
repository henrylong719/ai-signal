import { createFileRoute } from '@tanstack/react-router'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL, LEGAL_LAST_UPDATED } from '@/lib/legal'

export const Route = createFileRoute('/_layout/terms')({
  component: TermsPage,
  head: () => ({
    meta: [
      { title: 'Terms of Service — AI Signal' },
      {
        name: 'description',
        content:
          'The terms that apply when you use AI Signal — written in plain English, not boilerplate.',
      },
    ],
  }),
})

function TermsPage() {
  return (
    <LegalPageLayout
      eyebrow="Terms"
      title="Terms of Service"
      intro="These terms describe how you can use AI Signal and what you can expect from us. We have tried to keep the language straightforward."
      lastUpdated={LEGAL_LAST_UPDATED}
    >
      <PolicySection title="Accepting these terms">
        <p>
          By creating an account or using AI Signal, you agree to these terms.
          If you are using AI Signal on behalf of an organization, you confirm
          that you are authorized to accept these terms for that organization.
        </p>
      </PolicySection>

      <PolicySection title="What AI Signal provides">
        <p>
          AI Signal is a reading and discovery product. We aggregate AI-related
          updates from public sources, present them in a focused dashboard, and
          offer optional features such as saved articles, followed sources,
          topic preferences, and personalized feeds.
        </p>
        <p>
          Articles surfaced in AI Signal link out to the original publishers. AI
          Signal does not republish full article content.
        </p>
      </PolicySection>

      <PolicySection title="Your account">
        <PolicyList
          items={[
            'Provide accurate information when you sign up and keep your contact details current.',
            'Keep your password and any authentication credentials private.',
            'You are responsible for activity that happens under your account.',
            'If you spot unauthorized activity on your account, contact us so we can help.',
          ]}
        />
      </PolicySection>

      <PolicySection title="Acceptable use">
        <p>While using AI Signal, please do not:</p>
        <PolicyList
          items={[
            'Try to break, probe, or overload the service or its underlying infrastructure.',
            'Scrape the product to rebuild a competing aggregator or to bypass publisher attribution.',
            'Use AI Signal for unlawful, infringing, or harmful purposes.',
            "Attempt to access other users' accounts or data.",
            'Misrepresent your affiliation with AI Signal or any publisher we surface.',
          ]}
        />
      </PolicySection>

      <PolicySection title="External content and third parties">
        <p>
          AI Signal links to articles hosted by third parties. We do not control
          that content, and surfacing it does not imply endorsement. The
          original publishers retain all rights to their material, and your use
          of their sites is governed by their own terms and policies.
        </p>
      </PolicySection>

      <PolicySection title="Intellectual property">
        <p>
          AI Signal — including its product design, branding, code, and curated
          source list — belongs to us. You may use the product as intended, but
          you do not gain ownership of any of it by using it.
        </p>
        <p>
          Article titles, excerpts, author attributions, and links shown in AI
          Signal are descriptive metadata pointing to the original publishers.
          The articles themselves remain the property of those publishers.
        </p>
      </PolicySection>

      <PolicySection title="Personalized recommendations">
        <p>
          The For You feed and similar features are informational. We use your
          saved articles, click and dismiss signals, and stated preferences to
          suggest things you may want to read. These suggestions are
          best-effort, not editorial endorsements, and you should evaluate any
          article on its own merits.
        </p>
      </PolicySection>

      <PolicySection title="AI-assisted features">
        <p>
          AI Signal may, now or in the future, use machine learning to help
          summarize, tag, or explain articles. Any AI-generated text is provided
          for convenience only, may contain errors, and should not replace
          reading the original article from the publisher.
        </p>
      </PolicySection>

      <PolicySection title="No guarantees on accuracy or completeness">
        <p>
          AI Signal is provided on an "as is" and "as available" basis. We do
          not promise that the product will be uninterrupted, that every source
          will be ingested on time, or that every article shown will be
          accurate, current, or complete. Always confirm important information
          with the original source.
        </p>
      </PolicySection>

      <PolicySection title="Service changes and availability">
        <p>
          The product will keep evolving. We may add, change, or remove
          features, sources, or sections of AI Signal at any time. We will try
          to give reasonable notice when a change is significant.
        </p>
      </PolicySection>

      <PolicySection title="Limitation of liability">
        <p>
          To the maximum extent allowed by law, AI Signal and the people behind
          it are not liable for indirect, incidental, special, or consequential
          damages arising from your use of the product, lost profits, lost data,
          or for any reliance you place on content shown here. Our total
          liability for any claim related to AI Signal is limited to the greater
          of what you have paid us in the prior twelve months, or one hundred US
          dollars.
        </p>
      </PolicySection>

      <PolicySection title="Termination">
        <p>
          You can stop using AI Signal at any time. We may suspend or terminate
          accounts that violate these terms or that put the service or other
          users at risk. We will try to give notice when we can.
        </p>
      </PolicySection>

      <PolicySection title="Changes to these terms">
        <p>
          We may update these terms when the product changes meaningfully. The
          "Last updated" date at the top of the page tells you when the most
          recent version took effect. Your continued use of AI Signal after a
          change means you accept the updated terms.
        </p>
      </PolicySection>

      <PolicySection title="Contact">
        <p>
          Questions about these terms? Email{' '}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </PolicySection>
    </LegalPageLayout>
  )
}
