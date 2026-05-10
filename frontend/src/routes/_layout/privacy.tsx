import { createFileRoute } from '@tanstack/react-router'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'
import { CONTACT_EMAIL, LEGAL_LAST_UPDATED } from '@/lib/legal'
import { buildPageMeta } from '@/lib/meta'

export const Route = createFileRoute('/_layout/privacy')({
  component: PrivacyPage,
  head: () =>
    buildPageMeta({
      title: 'Privacy Policy',
      description:
        'How AI Signal collects, uses, and protects information about the people who use the product.',
      path: '/privacy',
    }),
})

function PrivacyPage() {
  return (
    <LegalPageLayout
      eyebrow="Privacy"
      title="Privacy Policy"
      intro="This page explains, in plain language, what information AI Signal collects, how it is used, and the choices you have. It is a working draft — we will keep it current as the product evolves."
      lastUpdated={LEGAL_LAST_UPDATED}
    >
      <PolicySection title="Who this applies to">
        <p>
          This policy covers anyone who visits AI Signal, signs in, or uses any
          of its reading and personalization features. It does not cover
          third-party publisher websites — when you click through to read a full
          article, you are visiting another company's site under their own
          privacy practices.
        </p>
      </PolicySection>

      <PolicySection title="Information we collect">
        <p>
          We try to collect as little as possible, and only what we need to run
          the product. Depending on how you use AI Signal, this may include:
        </p>
        <PolicyList
          items={[
            <span key="account">
              <strong>Account details.</strong> If you create an account, we
              store the basics needed to sign you in — typically a name and
              email address, or a unique identifier from a social sign-in
              provider you choose to use.
            </span>,
            <span key="library">
              <strong>Saved articles.</strong> Articles you save to your library
              are stored against your account so you can return to them.
            </span>,
            <span key="signals">
              <strong>Reading signals.</strong> When you are signed in, we
              record which articles you open and which ones you dismiss. These
              signals shape your <em>For You</em> feed and help us improve the
              recommendations.
            </span>,
            <span key="prefs">
              <strong>Preferences.</strong> Topics, tags, and sources you
              follow, and basic display preferences such as theme.
            </span>,
            <span key="device">
              <strong>Basic device and browser information.</strong> Your
              browser may share standard information such as IP address, user
              agent, and language. We use this for security, abuse prevention,
              and high-level usage understanding. AI Signal does not currently
              run third-party analytics or advertising trackers; if that ever
              changes, we will update this page first.
            </span>,
          ]}
        />
      </PolicySection>

      <PolicySection title="How we use information">
        <PolicyList
          items={[
            'To sign you in and keep your session secure.',
            'To save your library, preferences, and followed sources.',
            'To personalize the For You and Following feeds, and to improve recommendation quality over time.',
            'To diagnose problems, prevent abuse, and keep the service reliable.',
            'To respond to you when you contact us.',
          ]}
        />
        <p>
          We do not sell personal information, and we do not use your reading
          history to build profiles for advertisers.
        </p>
      </PolicySection>

      <PolicySection title="Cookies and browser storage">
        <p>
          AI Signal uses cookies and your browser's local and session storage
          for things like keeping you signed in, remembering your theme, and
          dismissing prompts you have already seen. There is more detail on our{' '}
          <a
            href="/cookies"
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            Cookie Policy
          </a>{' '}
          page.
        </p>
      </PolicySection>

      <PolicySection title="External links and third parties">
        <p>
          AI Signal is a discovery layer. When you open an article, you leave AI
          Signal and visit the original publisher's website. Those sites have
          their own privacy policies, cookie practices, and analytics tools, and
          we have no control over them. When you sign in with a social provider,
          that provider may also process information in line with their own
          policies.
        </p>
      </PolicySection>

      <PolicySection title="Third-party services">
        <p>
          We may use trusted service providers to host, secure, and operate AI
          Signal. These providers process information only as needed to provide
          their services to us.
        </p>
        <PolicyList
          items={[
            'Hosting and infrastructure providers that run the frontend, API, databases, and supporting services.',
            'PostgreSQL database infrastructure used to store accounts, article metadata, saved articles, preferences, and reading signals.',
            'Email delivery providers, when configured, for account and transactional emails.',
            'Google, GitHub, or Facebook only if you choose a social sign-in option that is enabled.',
            'Sentry error monitoring only when configured outside local development.',
            'Original article publishers when you click an outbound link to read their content.',
          ]}
        />
        <p>
          AI Signal does not currently run third-party analytics or advertising
          trackers. If that changes, we will update this policy and the Cookie
          Policy before describing the new practice as active.
        </p>
      </PolicySection>

      <PolicySection title="Data retention">
        <p>
          We keep account data, saved articles, and reading signals for as long
          as your account is active. When you remove a saved article, we remove
          that saved item from your library. If you delete your account from
          settings, account-linked saved articles, preferences, sessions, and
          related records are deleted where they are linked to your account,
          subject to backups and legal requirements. Aggregated, non-identifying
          data may be retained for longer to help us understand how the product
          is used.
        </p>
      </PolicySection>

      <PolicySection title="Your choices">
        <PolicyList
          items={[
            'Update topic, tag, and source preferences from the personalization screen.',
            'Save and unsave articles at any time.',
            'Change your display name, email, or password from your account settings.',
            'Delete your AI Signal account from the account settings screen, unless your account is restricted from self-deletion for administrative reasons.',
            'Contact us for help with account-related requests, subject to technical and legal limitations.',
            'Control cookies and storage from your browser settings.',
          ]}
        />
      </PolicySection>

      <PolicySection title="Security">
        <p>
          We use industry-standard practices — encrypted transport, secure
          authentication cookies, and access controls on the people and systems
          that handle data. No system is perfectly secure, but we take
          reasonable steps to protect what you trust us with, and we will tell
          you if a serious incident affects your account.
        </p>
      </PolicySection>

      <PolicySection title="Children">
        <p>
          AI Signal is built for adult professionals working in or learning
          about AI. It is not directed at children, and we do not knowingly
          collect information from children under 13.
        </p>
      </PolicySection>

      <PolicySection title="Changes to this policy">
        <p>
          We may update this policy as AI Signal changes. When we do, we will
          update the "Last updated" date at the top of the page. For material
          changes, we may provide notice through reasonable means, such as
          in-product messaging or account email where appropriate.
        </p>
      </PolicySection>

      <PolicySection title="Contact">
        <p>
          Questions, concerns, or a privacy request? Email{' '}
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
