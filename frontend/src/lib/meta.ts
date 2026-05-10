// Per-route Open Graph + canonical helper.
//
// Tanstack Router exposes per-route ``head()`` returns that emit document
// head tags. Without this helper, each route would have to repeat the
// same eight or so meta entries (title, description, og:* mirrors,
// twitter:* mirrors, canonical link). The shared ``index.html`` already
// carries the fallback OG/Twitter image, so individual routes only need
// to override the per-page text and the canonical / og:url for the
// preview to look correct on link unfurls.

const SITE_URL = 'https://aisignal.app'

interface BuildPageMetaInput {
  // Full page title. Don't include the site suffix — this helper appends
  // " — AI Signal" unless ``suppressSuffix`` is true (used for the
  // homepage where the suffix would be redundant).
  title: string
  // Short page summary. Aim for under 160 characters so search engines
  // and link previews don't truncate.
  description: string
  // Path within the app, e.g. ``/about`` or ``/all-article-sources``.
  // Used to build the canonical and og:url tags. Leading slash required.
  path: string
  // Optional override for the share preview image. Defaults to the
  // site-wide ``og-image.png`` already declared in index.html, which is
  // good enough for most pages.
  image?: string
  suppressSuffix?: boolean
}

interface MetaTag {
  title?: string
  name?: string
  property?: string
  content?: string
}

interface LinkTag {
  rel: string
  href: string
}

interface PageHead {
  meta: MetaTag[]
  links: LinkTag[]
}

export function buildPageMeta({
  title,
  description,
  path,
  image,
  suppressSuffix = false,
}: BuildPageMetaInput): PageHead {
  const fullTitle = suppressSuffix ? title : `${title} — AI Signal`
  const url = `${SITE_URL}${path}`
  const meta: MetaTag[] = [
    { title: fullTitle },
    { name: 'description', content: description },
    { property: 'og:title', content: fullTitle },
    { property: 'og:description', content: description },
    { property: 'og:url', content: url },
    { name: 'twitter:title', content: fullTitle },
    { name: 'twitter:description', content: description },
  ]
  if (image) {
    meta.push(
      { property: 'og:image', content: image },
      { name: 'twitter:image', content: image },
    )
  }
  return {
    meta,
    links: [{ rel: 'canonical', href: url }],
  }
}
