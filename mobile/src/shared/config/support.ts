/** Swap for your real Buy Me a Coffee page and a mailbox you actually read. */
export const SUPPORT_LINKS = {
  buyMeACoffee: 'https://www.buymeacoffee.com/cracknews',
  /** Content reports and publisher removal requests (shown in Settings). */
  contactEmail: 'support@cracknews.ca',
} as const;

export function reportContentMailto(): string {
  const subject = encodeURIComponent('CrackNews: report content / removal request');
  const body = encodeURIComponent(
    'Story or outlet:\nLink (if you have it):\nWhat is wrong (inaccurate brief, rights/removal request, other):\n',
  );
  return `mailto:${SUPPORT_LINKS.contactEmail}?subject=${subject}&body=${body}`;
}
