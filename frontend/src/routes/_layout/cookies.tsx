import { createFileRoute } from '@tanstack/react-router'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL, LEGAL_LAST_UPDATED } from '@/lib/legal'

export const Route = createFileRoute('/_layout/cookies')({
  component: CookiesPage,
  head: () => ({
    meta: [
      { title: 'Cookie Policy — AI Signal' },
      {
        name: 'description',
        content:
          'How AI Signal uses cookies, local storage, and similar technologies to keep the product running.',
      },
    ],
  }),
})

function CookiesPage() {
  return (
    <LegalPageLayout
      eyebrow="Cookies"
      title="Cookie Policy"
      intro="Cookies and similar technologies make AI Signal work. This page explains what we use, why, and how you can control them."
      lastUpdated={LEGAL_LAST_UPDATED}
    >
      <PolicySection title="What we mean by cookies">
        <p>
          A cookie is a small piece of data your browser stores on behalf of a
          website. AI Signal also uses related technologies — most notably your
          browser's <em>local storage</em> and
          <em> session storage</em> — which work in a similar way for our
          purposes here. We use the word "cookies" loosely to cover all of them.
        </p>
      </PolicySection>

      <PolicySection title="What AI Signal uses today">
        <PolicyList
          items={[
            <span key="auth">
              <strong>Authentication.</strong> When you sign in, we set a secure
              cookie that keeps you signed in across pages and across tabs.
              Without it, every action would log you out.
            </span>,
            <span key="theme">
              <strong>Display preferences.</strong> Your chosen theme (light,
              dark, or system) is stored in your browser's local storage so AI
              Signal opens the way you expect next time.
            </span>,
            <span key="prompts">
              <strong>In-product prompts.</strong> Some prompts (for example,
              the gentle nudge to sign in after scrolling) use session storage
              to remember that you have already dismissed them so they do not
              reappear in the same session.
            </span>,
            <span key="security">
              <strong>Security.</strong> We may use cookies and request metadata
              for fraud and abuse prevention.
            </span>,
          ]}
        />
        <p>
          AI Signal does not currently load third-party advertising or tracking
          pixels, and we do not run analytics that follow you across sites. If
          we add a privacy-respecting analytics tool in the future, we will list
          it here first.
        </p>
      </PolicySection>

      <PolicySection title="Third-party services">
        <p>
          When you choose to sign in with a social provider, that provider may
          set its own cookies as part of its sign-in flow. Those cookies are
          governed by that provider's policies, not ours. External article links
          also take you to publisher sites that have their own cookies and
          tracking practices.
        </p>
      </PolicySection>

      <PolicySection title="How long cookies stick around">
        <PolicyList
          items={[
            'Session cookies are removed when you close your browser.',
            'Persistent cookies and local storage values stay until they expire or until you (or we) clear them. Authentication cookies are typically refreshed while you are active and removed when you sign out.',
          ]}
        />
      </PolicySection>

      <PolicySection title="How to control cookies">
        <p>
          Every modern browser lets you view, block, and delete cookies and
          local storage. Look for the privacy or "Site data" section in your
          browser's settings, or use a private/incognito window if you prefer
          not to keep state between sessions.
        </p>
        <p>
          If you block authentication cookies, AI Signal will not be able to
          keep you signed in, so the personalized features (saved articles, For
          You, Following) will not work. Most other parts of the product still
          function as a public reading experience.
        </p>
      </PolicySection>

      <PolicySection title="Changes">
        <p>
          When we add or remove a cookie that materially changes how information
          is stored, we will update this page and bump the "Last updated" date
          below.
        </p>
      </PolicySection>

      <PolicySection title="Contact">
        <p>
          Questions about cookies or browser storage? Email{' '}
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
