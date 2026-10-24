import type { DisplayAd, StoryCard, StorylineSummary, WallItem } from '@/data/types/api';

export type StorylineListItem =
  | { kind: 'thread'; thread: StorylineSummary }
  | { kind: 'ad'; ad: DisplayAd }
  | { kind: 'native'; slotId: string };

type MixOptions = {
  fillRate?: number;
  random?: () => number;
  /** Claims a loaded AdMob native ad when there is no first-party ad to show. */
  takeNative?: () => string | null;
};

/** First-party ads win; otherwise a loaded AdMob native ad; otherwise no ad. */
function pickAd(
  ads: DisplayAd[],
  rnd: () => number,
  takeNative?: () => string | null,
): { kind: 'ad'; ad: DisplayAd } | { kind: 'native'; slotId: string } | null {
  if (ads.length) {
    const ad = ads[Math.floor(rnd() * ads.length)];
    if (ad) return { kind: 'ad', ad };
  }
  const slotId = takeNative?.() ?? null;
  return slotId ? { kind: 'native', slotId } : null;
}

export function storiesToWall(stories: StoryCard[]): WallItem[] {
  return stories.map((story) => ({ kind: 'story', story }));
}

/** Insert 0–1 display ad into a story page so the wall still reads as masonry. */
export function mixDisplayAds(
  stories: StoryCard[],
  ads: DisplayAd[],
  opts?: MixOptions,
): WallItem[] {
  const wall = storiesToWall(stories);
  const rnd = opts?.random ?? Math.random;
  const fillRate = opts?.fillRate ?? 0.55;
  if (stories.length < 4 || rnd() > fillRate) return wall;

  const ad = pickAd(ads, rnd, opts?.takeNative);
  if (!ad) return wall;

  const min = 2;
  const max = Math.min(stories.length - 1, 5);
  const slot = min + Math.floor(rnd() * (max - min + 1));
  wall.splice(slot, 0, ad);
  return wall;
}

export function wallItemId(item: WallItem): string {
  if (item.kind === 'native') return `native:${item.slotId}`;
  return item.kind === 'ad' ? `ad:${item.ad.adId}` : item.story.storyId;
}

/** Native ad cards use one fixed shape so wall heights stay exact (media is cropped). */
export const NATIVE_AD_ASPECT = 0.8;

export function wallItemAspect(item: WallItem): number {
  if (item.kind === 'native') return NATIVE_AD_ASPECT;
  const aspect = item.kind === 'ad' ? item.ad.imageAspect : item.story.imageAspect;
  return aspect && aspect > 0.45 ? aspect : 0.72;
}

export function storiesFromWall(items: WallItem[]): StoryCard[] {
  return items.filter((item): item is { kind: 'story'; story: StoryCard } => item.kind === 'story').map((item) => item.story);
}

export function mixStorylineAds(
  threads: StorylineSummary[],
  ads: DisplayAd[],
  opts?: MixOptions,
): StorylineListItem[] {
  const list: StorylineListItem[] = threads.map((thread) => ({ kind: 'thread', thread }));
  const rnd = opts?.random ?? Math.random;
  const fillRate = opts?.fillRate ?? 0.55;
  if (threads.length < 2 || rnd() > fillRate) return list;

  const ad = pickAd(ads, rnd, opts?.takeNative);
  if (!ad) return list;

  const max = Math.min(threads.length - 1, 2);
  const slot = 1 + Math.floor(rnd() * Math.max(1, max));
  list.splice(slot, 0, ad);
  return list;
}
