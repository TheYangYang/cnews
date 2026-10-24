import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchDisplayAds, fetchStorylines } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import type { DisplayAd, StorylineStatus, StorylineSummary } from '@/data/types/api';
import {
  mixStorylineAds,
  type StorylineListItem,
} from '@/features/home/mixDisplayAds';
import { releaseNativeAds, takeNativeAd } from '@/features/ads/nativeAdPool';
import { shuffleCopy } from '@/shared/utils/shuffle';

type Filter = StorylineStatus | 'all';

const PAGE_SIZE = 10;

const claimNative = takeNativeAd('storylines');

export function useStorylines(filter: Filter) {
  const token = useAuthStore((s) => s.accessToken);
  const [items, setItems] = useState<StorylineSummary[]>([]);
  const [listItems, setListItems] = useState<StorylineListItem[]>([]);
  const [ads, setAds] = useState<DisplayAd[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(false);
  // Bumped per first-page load so a late page for an old filter is dropped.
  const generation = useRef(0);

  const paint = useCallback((threads: StorylineSummary[], inventory: DisplayAd[]) => {
    setItems(threads);
    const list = mixStorylineAds(threads, inventory, { takeNative: claimNative });
    // A new first page replaces the list: free the Google ads the old one held.
    releaseNativeAds(
      'storylines',
      list.flatMap((entry) => (entry.kind === 'native' ? [entry.slotId] : [])),
    );
    setListItems(list);
  }, []);

  const loadFirst = useCallback(
    async (opts?: { shuffle?: boolean }) => {
      const gen = ++generation.current;
      const [res, adRes] = await Promise.all([
        fetchStorylines({
          status: filter,
          limit: PAGE_SIZE,
          token,
        }),
        fetchDisplayAds({ slot: 'storylines_list', limit: 6, token }).catch(() => ({ items: [] })),
      ]);
      if (gen !== generation.current) return 0;
      setError(false);
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
          setError(true);
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
    } catch {
      // Keep the current list when a refresh fails.
      setError(true);
      return 0;
    } finally {
      setRefreshing(false);
    }
  }, [loadFirst]);

  const loadMore = useCallback(async () => {
    if (!cursor || loadingMore) return;
    const gen = generation.current;
    setLoadingMore(true);
    try {
      const res = await fetchStorylines({
        status: filter,
        limit: PAGE_SIZE,
        cursor,
        token,
      });
      if (gen !== generation.current) return;
      const seen = new Set(items.map((t) => t.threadId));
      const fresh = res.items.filter((t) => !seen.has(t.threadId));
      if (fresh.length) {
        setItems((prev) => [...prev, ...fresh]);
        setListItems((prev) => [
          ...prev,
          ...mixStorylineAds(fresh, ads, { fillRate: 0.35, takeNative: claimNative }),
        ]);
      }
      setCursor(res.nextCursor ?? null);
    } catch {
      // Keep the cursor so the next scroll retries.
    } finally {
      setLoadingMore(false);
    }
  }, [cursor, loadingMore, filter, token, ads, items]);

  return {
    items,
    listItems,
    isLoading: loading,
    isRefetching: refreshing,
    error,
    loadingMore,
    hasMore: !!cursor,
    refreshRandom,
    loadMore,
  };
}
