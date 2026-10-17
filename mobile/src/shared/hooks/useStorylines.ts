import { useCallback, useEffect, useState } from 'react';

import { fetchStorylines } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import type { StorylineStatus, StorylineSummary } from '@/data/types/api';
import { shuffleCopy } from '@/shared/utils/shuffle';

type Filter = StorylineStatus | 'all';

const PAGE_SIZE = 10;

export function useStorylines(filter: Filter) {
  const token = useAuthStore((s) => s.accessToken);
  const [items, setItems] = useState<StorylineSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadFirst = useCallback(
    async (opts?: { shuffle?: boolean }) => {
      const res = await fetchStorylines({
        status: filter,
        limit: PAGE_SIZE,
        token,
      });
      const next = opts?.shuffle ? shuffleCopy(res.items) : res.items;
      setItems(next);
      setCursor(res.nextCursor ?? null);
      return next.length;
    },
    [filter, token],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setItems([]);
    setCursor(null);
    void loadFirst()
      .catch(() => {
        if (!cancelled) setItems([]);
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
        setItems((prev) => {
          const seen = new Set(prev.map((t) => t.threadId));
          return [...prev, ...res.items.filter((t) => !seen.has(t.threadId))];
        });
      }
      setCursor(res.nextCursor ?? null);
    } finally {
      setLoadingMore(false);
    }
  }, [cursor, loadingMore, filter, token]);

  return {
    items,
    isLoading: loading,
    isRefetching: refreshing,
    loadingMore,
    hasMore: !!cursor,
    refreshRandom,
    loadMore,
  };
}
