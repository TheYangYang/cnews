import { useCallback, useEffect, useState } from 'react';

import { fetchDisplayAds, fetchStorylines } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import type { DisplayAd, StorylineStatus, StorylineSummary } from '@/data/types/api';
import {
  mixStorylineAds,
  type StorylineListItem,
} from '@/features/home/mixDisplayAds';
import { shuffleCopy } from '@/shared/utils/shuffle';

type Filter = StorylineStatus | 'all';

const PAGE_SIZE = 10;

export function useStorylines(filter: Filter) {
  const token = useAuthStore((s) => s.accessToken);
  const [items, setItems] = useState<StorylineSummary[]>([]);
  const [listItems, setListItems] = useState<StorylineListItem[]>([]);
  const [ads, setAds] = useState<DisplayAd[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const paint = useCallback((threads: StorylineSummary[], inventory: DisplayAd[]) => {
    setItems(threads);
    setListItems(mixStorylineAds(threads, inventory));
  }, []);

  const loadFirst = useCallback(
    async (opts?: { shuffle?: boolean }) => {
      const [res, adRes] = await Promise.all([
        fetchStorylines({
          status: filter,
          limit: PAGE_SIZE,
          token,
        }),
        fetchDisplayAds({ slot: 'storylines_list', limit: 6, token }),
      ]);
      const next = opts?.shuffle ? shuffleCopy(res.items) : res.items;
      setAds(adRes.items);
      setCursor(res.nextCursor ?? null);
      paint(next, adRes.items);
      return next.length;
    },
    [filter, token, paint],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setItems([]);
    setListItems([]);
    setCursor(null);
    void loadFirst()
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setListItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loadFirst]);

  const refreshRandom = useCallback(async () => {
    setRefreshing(true);
    try {
      return await loadFirst({ shuffle: true });
    } finally {
      setRefreshing(false);
    }
  }, [loadFirst]);

  const loadMore = useCallback(async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await fetchStorylines({
        status: filter,
        limit: PAGE_SIZE,
        cursor,
        token,
      });
      if (res.items.length) {
        const mixed = mixStorylineAds(res.items, ads, { fillRate: 0.35 });
        setItems((prev) => {
          const seen = new Set(prev.map((t) => t.threadId));
          return [...prev, ...res.items.filter((t) => !seen.has(t.threadId))];
        });
        setListItems((prev) => [...prev, ...mixed]);
      }
      setCursor(res.nextCursor ?? null);
    } finally {
      setLoadingMore(false);
    }
  }, [cursor, loadingMore, filter, token, ads]);

  return {
    items,
    listItems,
    isLoading: loading,
    isRefetching: refreshing,
    loadingMore,
    hasMore: !!cursor,
    refreshRandom,
    loadMore,
  };
}
