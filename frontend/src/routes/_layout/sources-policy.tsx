import { createFileRoute, Link } from '@tanstack/react-router'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL, LEGAL_LAST_UPDATED } from '@/lib/legal'

export const Route = createFileRoute('/_layout/sources-policy')({
  component: SourcesPolicyPage,
  head: () => ({
    meta: [
      { title: 'Sources & Content Policy — AI Signal' },
      {
        name: 'description',
        content:
          'How AI Signal selects sources, what we display, and how publishers and rights holders can reach us.',
      },
    ],
  }),
})

function SourcesPolicyPage() {
  return (
    <LegalPageLayout
      eyebrow="Sources"
      title="Sources & Content Policy"
      intro="AI Signal is a discovery layer for the AI ecosystem. We point readers to the people doing the work — we do not republish their articles. This page explains how that works."
      lastUpdated={LEGAL_LAST_UPDATED}
    >
      <PolicySection title="How sources are selected">
        <p>
          The catalogue is curated for relevance to AI builders, researchers,
          founders, and software engineers. It includes AI labs, research
          groups, engineering blogs, newsletters, and other respected voices in
          the field. We add and remove sources over time as the ecosystem
          changes.
        </p>
      </PolicySection>

      <PolicySection title="Where articles come from">
        <p>
          Articles are discovered from public RSS and Atom feeds, or other
          configured public endpoints provided by the publisher. We do not
          scrape behind paywalls and we do not sign in to gated services to
          fetch content.
        </p>
      </PolicySection>

      <PolicySection title="What AI Signal displays">
        <PolicyList
          items={[
            'Article title.',
            'Source name and, where available, the author.',
            'Published date.',
            'A short excerpt or description, when the publisher provides one.',
            'A representative image, when the feed includes one.',
            'A link that takes the reader directly to the original article.',
            'Tags and a topic category, used to help readers filter.',
          ]}
        />
        <p>
          Full article bodies always live on the publisher's website. AI Signal
          does not store or render the full text of an article in place of the
          original.
        </p>
      </PolicySection>

      <PolicySection title="Outbound clicks">
        <p>
          When you click an article in AI Signal, your browser is briefly routed
          through our backend so we can record a click event for your own
          personalization. Clicks from people who are not signed in are not
          logged. Either way, you end up on the publisher's page, on the
          publisher's domain.
        </p>
      </PolicySection>

      <PolicySection title="Rights and attribution">
        <p>
          Original publishers retain all rights to their articles. We attribute
          every article to its source by name, link straight back to the
          canonical URL, and treat publisher content as the authoritative
          version. We do not modify article copy.
        </p>
      </PolicySection>

      <PolicySection title="AI-assisted summaries (now or later)">
        <p>
          Some article excerpts come straight from publisher feeds. If we add
          AI-assisted summaries, "why this matters" notes, or similar generated
          text in the future, they will be clearly framed as AI-generated, may
          be imperfect, and are intended as supporting context — not as a
          replacement for reading the article.
        </p>
      </PolicySection>

      <PolicySection title="Suggesting a source">
        <p>
          Notice an important AI publication we are missing? We would love a
          pointer.{' '}
          <Link
            to="/contact"
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            Send us a suggestion
          </Link>{' '}
          with the publication name and feed URL.
        </p>
      </PolicySection>

      <PolicySection title="Publisher requests, corrections, and removals">
        <p>
          Publishers, authorized representatives, and rights holders can ask us
          to correct attribution, update source metadata, or remove links or
          excerpts from AI Signal.
        </p>
        <PolicyList
          items={[
            <span key="email">
              Email{' '}
              <a
                href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
                  'Publisher request',
                )}`}
                className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
              >
                {CONTACT_EMAIL}
              </a>{' '}
              from a domain associated with the publication when possible.
            </span>,
            'Include your name, role or relationship to the publisher, the source name, the article URL, and what you would like changed or removed.',
            'If the request is about rights, impersonation, or attribution, include enough context for us to verify it.',
          ]}
        />
        <p>
          We aim to respond to verified publisher correction, attribution, or
          removal requests within 5 business days. We review requests in good
          faith and may remove or adjust content sooner when the issue is clear.
        </p>
      </PolicySection>
    </LegalPageLayout>
  )
}
