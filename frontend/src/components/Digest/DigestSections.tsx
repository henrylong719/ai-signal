import type { DigestSectionPublic } from '@/client'
import DigestArticle from '@/components/Digest/DigestArticle'

const signalCountLabel = (count: number) =>
  count === 1 ? '1 signal' : `${count} signals`

function DigestSections({ sections }: { sections: DigestSectionPublic[] }) {
  return (
    <div className="space-y-8 md:space-y-11">
      {sections.map((section, index) => (
        <section key={section.key} className="scroll-mt-20">
          <div
            className={`border-t border-slate-200/80 pt-8 dark:border-border/80 ${
              index === 0 ? 'border-t-0 pt-0' : ''
            }`}
          >
            <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400 dark:text-muted-foreground/80">
                {section.key === 'top' ? 'Start Here' : 'Topic'}
              </span>
              <span className="h-px w-8 bg-slate-200 dark:bg-border" />
              <span className="text-xs font-medium text-slate-400 dark:text-muted-foreground/75">
                {signalCountLabel(section.articles.length)}
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] md:items-end">
              <h2 className="font-serif text-4xl font-medium leading-none tracking-normal text-slate-950 sm:text-5xl dark:text-foreground">
                {section.title}
              </h2>
            </div>
          </div>

          <div className="mt-7 divide-y divide-slate-200/80 border-y border-slate-200/80 dark:divide-border/80 dark:border-border/80">
            {section.articles.map((article) => (
              <DigestArticle key={article.id} article={article} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

export default DigestSections
