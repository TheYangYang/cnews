import { useCallback, useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';

import { useAuthStore } from '@/data/stores/authStore';
import { useFeedStore } from '@/data/stores/feedStore';
import { useSettingsStore } from '@/data/stores/settingsStore';

/**
 * Home feed (always `mode=listen`). State lives in `feedStore`, so Home, the
 * in-tab reader, and the Play button all see the same pages in the same order.
 */
export function useFeed() {
  const token = useAuthStore((s) => s.accessToken);
  const topics = useSettingsStore((s) => s.selectedTopics);
  const state = useFeedStore(
    useShallow((s) => ({
      items: s.items,
      wallItems: s.wallItems,
      cursor: s.cursor,
      loading: s.loading,
      refreshing: s.refreshing,
      loadingMore: s.loadingMore,
      error: s.error,
      ensureLoaded: s.ensureLoaded,
      refresh: s.refreshRandom,
      more: s.loadMore,
    })),
  );
  const { ensureLoaded, refresh, more } = state;

  useEffect(() => {
    ensureLoaded({ topics, token });
  }, [ensureLoaded, topics, token]);

  const refreshRandom = useCallback(() => refresh({ topics, token }), [refresh, topics, token]);
  const loadMore = useCallback(() => more({ topics, token }), [more, topics, token]);
  const refetch = refreshRandom;

  return {
    items: state.items,
    wallItems: state.wallItems,
    isLoading: state.loading && !state.items.length,
    isRefetching: state.refreshing,
    loadingMore: state.loadingMore,
    hasMore: !!state.cursor,
    error: state.error,
    refetch,
    refreshRandom,
    loadMore,
  };
}
