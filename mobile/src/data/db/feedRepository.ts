import AsyncStorage from '@react-native-async-storage/async-storage';

import { tryGetSqlite } from '@/data/db/database';
import type { StoryCard } from '@/data/types/api';

const MEMORY_KEY = 'cnews.feed.cache.v1';

async function writeMemory(stories: StoryCard[]): Promise<void> {
  try {
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
  } catch {
    /* ignore */
  }
}

async function readMemory(limit: number): Promise<StoryCard[]> {
  try {
    const raw = await AsyncStorage.getItem(MEMORY_KEY);
    if (!raw) return [];
    return (JSON.parse(raw) as StoryCard[]).slice(0, limit);
  } catch {
    return [];
  }
}

export async function upsertFeedStories(stories: StoryCard[]): Promise<void> {
  if (!stories.length) return;
  await writeMemory(stories);

  const db = await tryGetSqlite();
  if (!db) return;
  const now = new Date().toISOString();
  try {
    for (const story of stories) {
      await db.runAsync(
        `INSERT INTO feed_stories (story_id, payload, published_at, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(story_id) DO UPDATE SET
           payload = excluded.payload,
           published_at = excluded.published_at,
           updated_at = excluded.updated_at`,
        [story.storyId, JSON.stringify(story), story.publishedAt, now],
      );
    }
  } catch {
    /* AsyncStorage already holds the cache */
  }
}

export async function readCachedFeed(limit = 40): Promise<StoryCard[]> {
  const db = await tryGetSqlite();
  if (db) {
    try {
      const rows = await db.getAllAsync<{ payload: string }>(
        'SELECT payload FROM feed_stories ORDER BY published_at DESC LIMIT ?',
        [limit],
      );
      if (rows.length) {
        return rows.map((r) => JSON.parse(r.payload) as StoryCard);
      }
    } catch {
      /* fall through */
    }
  }
  return readMemory(limit);
}

export async function maxPublishedAt(): Promise<string | null> {
  const items = await readCachedFeed(1);
  return items[0]?.publishedAt ?? null;
}
