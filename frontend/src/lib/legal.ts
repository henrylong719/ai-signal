// Single source of truth for the contact email surfaced on legal/support
// pages and the "last updated" date stamped on policies. Update both in
// one place when the project moves to a real domain or when a policy
// page is materially revised.
export const CONTACT_EMAIL = 'henrylong719@gmail.com';
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
