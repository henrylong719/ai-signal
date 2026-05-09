import type { DigestSectionPublic } from '@/client';
import DigestArticle from '@/components/Digest/DigestArticle';

function DigestSections({ sections }: { sections: DigestSectionPublic[] }) {
  return (
    <div className="space-y-16 md:space-y-20">
      {sections.map((section) => (
        <section key={section.key}>
          <div className="mb-9 flex items-center gap-4">
            <h2 className="shrink-0 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-muted-foreground">
              {section.title}
            </h2>
            <div className="h-px flex-1 bg-slate-200/70 dark:bg-border" />
          </div>

          <div className="space-y-10 sm:space-y-12">
            {section.articles.map((article) => (
              <DigestArticle key={article.id} article={article} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

export default DigestSections;
