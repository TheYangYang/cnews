import type { DisplayAd, StoryCard, WallItem } from '@/data/types/api';

export function storiesToWall(stories: StoryCard[]): WallItem[] {
  return stories.map((story) => ({ kind: 'story', story }));
}

/** Insert 0–1 display ad into a story page so the wall still reads as masonry. */
export function mixDisplayAds(
  stories: StoryCard[],
  ads: DisplayAd[],
  opts?: { fillRate?: number; random?: () => number },
): WallItem[] {
  const wall = storiesToWall(stories);
  const rnd = opts?.random ?? Math.random;
  const fillRate = opts?.fillRate ?? 0.55;
  if (!ads.length || stories.length < 4 || rnd() > fillRate) return wall;

  const ad = ads[Math.floor(rnd() * ads.length)];
  if (!ad) return wall;

  const min = 2;
  const max = Math.min(stories.length - 1, 5);
  const slot = min + Math.floor(rnd() * (max - min + 1));
  wall.splice(slot, 0, { kind: 'ad', ad });
  return wall;
}

export function wallItemId(item: WallItem): string {
  return item.kind === 'ad' ? `ad:${item.ad.adId}` : item.story.storyId;
}

export function wallItemAspect(item: WallItem): number {
  const aspect = item.kind === 'ad' ? item.ad.imageAspect : item.story.imageAspect;
  return aspect && aspect > 0.45 ? aspect : 0.72;
}

export function storiesFromWall(items: WallItem[]): StoryCard[] {
  return items.filter((item): item is { kind: 'story'; story: StoryCard } => item.kind === 'story').map((item) => item.story);
}
