import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchDisplayAds, fetchHomeFeed } from '@/data/api/endpoints';
import { readCachedFeed, upsertFeedStories } from '@/data/db/feedRepository';
import { useAuthStore } from '@/data/stores/authStore';
import { useSettingsStore } from '@/data/stores/settingsStore';
import type { DisplayAd, StoryCard, WallItem } from '@/data/types/api';
import { mixDisplayAds, storiesToWall } from '@/features/home/mixDisplayAds';
import { shuffleCopy } from '@/shared/utils/shuffle';

export function useFeed() {
  const token = useAuthStore((s) => s.accessToken);
  const topics = useSettingsStore((s) => s.selectedTopics);
  const listeningPreference = useSettingsStore((s) => s.listeningPreference);
  const [cached, setCached] = useState<StoryCard[]>([]);
  const [items, setItems] = useState<StoryCard[]>([]);
  const [wallItems, setWallItems] = useState<WallItem[]>([]);
  const [ads, setAds] = useState<DisplayAd[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const mode = listeningPreference === 'voice_ready_only' ? 'listen' : 'any';
  const pageSize = 10;

  useEffect(() => {
    void readCachedFeed().then((rows) => {
      setCached(rows);
      if (!items.length) {
        setItems(rows);
        setWallItems(storiesToWall(rows));
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const paintPage = useCallback((stories: StoryCard[], inventory: DisplayAd[]) => {
    setItems(stories);
    setWallItems(mixDisplayAds(stories, inventory));
  }, []);

  const query = useQuery({
    queryKey: ['home-feed', topics.join(','), mode, pageSize],
    queryFn: async () => {
      const [res, adRes] = await Promise.all([
        fetchHomeFeed({ topics, limit: pageSize, token, mode }),
        fetchDisplayAds({ slot: 'home_wall', limit: 6, token }),
      ]);
      await upsertFeedStories(res.items);
      setAds(adRes.items);
      setCursor(res.nextCursor ?? null);
      paintPage(res.items, adRes.items);
      return res.items;
    },
    placeholderData: cached.length ? cached : undefined,
    staleTime: 60_000,
  });

  /** Pull-to-refresh: fresh page, shuffled order, pagination reset. Ads re-roll. */
  const refreshRandom = useCallback(async (): Promise<StoryCard[]> => {
    setRefreshing(true);
    try {
      const [res, adRes] = await Promise.all([
        fetchHomeFeed({ topics, limit: pageSize, token, mode }),
        fetchDisplayAds({ slot: 'home_wall', limit: 6, token }),
      ]);
      const next = shuffleCopy(res.items);
      if (next.length) await upsertFeedStories(next);
      setAds(adRes.items);
      setCursor(res.nextCursor ?? null);
      paintPage(next, adRes.items);
      return next;
    } finally {
      setRefreshing(false);
    }
  }, [topics, token, mode, pageSize, paintPage]);

  const loadMore = useCallback(async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await fetchHomeFeed({
        topics,
        limit: pageSize,
        cursor,
        token,
        mode,
      });
      if (res.items.length) {
        await upsertFeedStories(res.items);
        const mixed = mixDisplayAds(res.items, ads);
        setItems((prev) => {
          const seen = new Set(prev.map((s) => s.storyId));
          return [...prev, ...res.items.filter((s) => !seen.has(s.storyId))];
        });
        setWallItems((prev) => [...prev, ...mixed]);
      }
      setCursor(res.nextCursor ?? null);
    } finally {
      setLoadingMore(false);
    }
  }, [cursor, loadingMore, topics, token, mode, pageSize, ads]);

  const display = items.length ? items : (query.data ?? cached);
  const wall = wallItems.length ? wallItems : storiesToWall(display);

  return {
    items: display,
    wallItems: wall,
    isLoading: query.isLoading && !display.length,
    isRefetching: refreshing || query.isRefetching,
    loadingMore,
    hasMore: !!cursor,
    error: query.error,
    refetch: query.refetch,
    refreshRandom,
    loadMore,
  };
}
