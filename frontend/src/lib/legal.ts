// Single source of truth for the contact email surfaced on legal/support
// pages and the "last updated" date stamped on policies. The mailbox
// must remain reachable in production — bounce-back from this address
// breaks every "Contact us" CTA across the app.
export const CONTACT_EMAIL = 'hello@aisignal.now';
// Pinned date the legal pages were last revised. Bump only when a
// policy actually changes — drifting this on every commit would erode
// the credibility of the "Last updated" line.
export const LEGAL_LAST_UPDATED = 'May 9, 2026';

export interface SupportLink {
  to:
    | '/about'
    | '/sources-policy'
    | '/privacy'
    | '/terms'
    | '/cookies'
    | '/accessibility'
    | '/contact';
  label: string;
}

// The order here matches the visual order of the support footer links
// across the app — keep them in this sequence (About first, Contact last)
// so the footer reads like a small site map.
export const SUPPORT_LINKS: SupportLink[] = [
  { to: '/about', label: 'About' },
  { to: '/sources-policy', label: 'Sources Policy' },
  { to: '/privacy', label: 'Privacy' },
  { to: '/terms', label: 'Terms' },
  { to: '/cookies', label: 'Cookies' },
  { to: '/accessibility', label: 'Accessibility' },
  { to: '/contact', label: 'Contact' },
];
