export function matchesSearchQuery(
  parts: Array<string | undefined | null>,
  raw: string,
): boolean {
  const q = raw.trim().toLowerCase();
  if (q.length < 1) return false;
  return parts.some((p) => (p ?? '').toLowerCase().includes(q));
}
