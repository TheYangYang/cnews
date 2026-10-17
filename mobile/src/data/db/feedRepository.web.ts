import AsyncStorage from '@react-native-async-storage/async-storage';

import type { StoryCard } from '@/data/types/api';

const MEMORY_KEY = 'cnews.feed.cache.v1';

export async function upsertFeedStories(stories: StoryCard[]): Promise<void> {
  if (!stories.length) return;
  const existingRaw = await AsyncStorage.getItem(MEMORY_KEY);
  const byId = new Map<string, StoryCard>();
  if (existingRaw) {
    for (const s of JSON.parse(existingRaw) as StoryCard[]) {
      byId.set(s.storyId, s);
    }
  }
  for (const s of stories) byId.set(s.storyId, s);
  const merged = [...byId.values()].sort((a, b) =>
    a.publishedAt < b.publishedAt ? 1 : -1,
  );
  await AsyncStorage.setItem(MEMORY_KEY, JSON.stringify(merged.slice(0, 80)));
}

export async function readCachedFeed(limit = 40): Promise<StoryCard[]> {
  const raw = await AsyncStorage.getItem(MEMORY_KEY);
  if (!raw) return [];
  return (JSON.parse(raw) as StoryCard[]).slice(0, limit);
}

export async function maxPublishedAt(): Promise<string | null> {
  const items = await readCachedFeed(1);
  return items[0]?.publishedAt ?? null;
}
