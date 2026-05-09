import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowRightIcon } from 'lucide-react'
import {
  LegalPageLayout,
  PolicyList,
  PolicySection,
} from '@/components/Legal/LegalPageLayout'

export const Route = createFileRoute('/_layout/about')({
  component: AboutPage,
  head: () => ({
    meta: [
      { title: 'About AI Signal' },
      {
        name: 'description',
        content:
          'AI Signal is a focused reading dashboard that helps builders track the AI updates that matter — labs, research, engineering blogs, and trusted voices.',
      },
    ],
  }),
})

function AboutPage() {
  return (
    <LegalPageLayout
      eyebrow="About"
      title="Track the AI updates that matter."
      intro="AI Signal helps builders follow the fast-moving AI ecosystem by bringing together updates from labs, research sources, engineering blogs, and trusted builders in one focused reading experience."
    >
      <PolicySection title="What AI Signal is">
        <p>
          The pace of AI moves faster than any single feed reader can keep up
          with. Important launches, papers, and engineering write-ups land
          across dozens of disconnected sources every week, and most of it ends
          up scattered across newsletters, social timelines, and bookmarked
          tabs.
        </p>
        <p>
          AI Signal is a reading layer for that ecosystem. It brings curated
          updates into a single calm, editorial dashboard so builders,
          researchers, and founders can spend less time chasing links and more
          time understanding what shipped.
        </p>
      </PolicySection>

      <PolicySection title="What you can do here">
        <PolicyList
          items={[
            <span key="follow">
              Follow specific labs, newsletters, and engineering blogs so the
              voices you trust shape your feed.
            </span>,
            <span key="topics">
              Pick the topics and tags that interest you most — research,
              tooling, agents, evals, infrastructure, and more.
            </span>,
            <span key="save">
              Save articles to a personal library you can come back to later.
            </span>,
            <span key="for-you">
              Open a personalized <strong>For You</strong> feed that adapts
              quietly as you save, click, or dismiss articles.
            </span>,
            <span key="following">
              Switch to a <strong>Following</strong> feed for a clean
              chronological view of just the sources you follow.
            </span>,
          ]}
        />
      </PolicySection>

      <PolicySection title="A discovery layer, not a replacement">
        <p>
          AI Signal does not host or republish full articles. We surface
          headlines, source attribution, short excerpts, and a link straight
          back to the original publisher. The full story always lives on the
          author's site.
        </p>
        <p>
          Source selection is curated for relevance to AI builders, researchers,
          founders, and software engineers. If you think a source is missing, we
          would love to hear about it.
        </p>
      </PolicySection>

      <PolicySection title="Where to go next">
        <p>
          Have a suggestion, a bug, an accessibility issue, or a takedown
          request? You can{' '}
          <Link
            to="/contact"
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            get in touch
          </Link>
          . You can also read about{' '}
          <Link
            to="/sources-policy"
            className="font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            how we handle third-party content
          </Link>{' '}
          or browse the{' '}
          <Link
            to="/all-article-sources"
            className="inline-flex items-center gap-1 font-medium text-slate-950 underline underline-offset-4 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/86"
          >
            full source library
            <ArrowRightIcon
              className="h-3.5 w-3.5 stroke-[1.8]"
              aria-hidden="true"
            />
          </Link>
          .
        </p>
      </PolicySection>
    </LegalPageLayout>
  )
}
