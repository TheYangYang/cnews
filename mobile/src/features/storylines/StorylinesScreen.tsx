import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeInDown, LinearTransition } from 'react-native-reanimated';

import { fetchStorylineDetail, fetchStorylines } from '@/data/api/endpoints';
import { StorylineCard } from '@/features/storylines/StorylineCard';
import { updatesToCards } from '@/features/storylines/storylineUtils';
import { useAuthStore } from '@/data/stores/authStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { EmptyState } from '@/shared/components/EmptyState';
import { Screen } from '@/shared/components/Screen';
import { useStorylines } from '@/shared/hooks/useStorylines';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';
import type { StorylineStatus } from '@/data/types/api';

type Filter = 'open' | 'closed' | 'all';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'open', label: 'Ongoing' },
  { key: 'closed', label: 'Closed' },
  { key: 'all', label: 'All' },
];

export function StorylinesScreen() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const token = useAuthStore((s) => s.accessToken);
  const setSurface = usePlaySurfaceStore((s) => s.setSurface);
  const setStorylineQueue = usePlaySurfaceStore((s) => s.setStorylineQueue);
  const [filter, setFilter] = useState<Filter>('open');
  const {
    items,
    isLoading,
    isRefetching,
    loadingMore,
    hasMore,
    refreshRandom,
    loadMore,
  } = useStorylines(filter);

  // Build Play queue from currently loaded threads’ updates.
  const refreshPlayQueue = useCallback(async () => {
    const list = items.length
      ? items
      : (
          await fetchStorylines({
            status: filter === 'all' ? 'open' : (filter as StorylineStatus),
            limit: 8,
            token,
          })
        ).items;
    const open = list.filter((t) => t.status === 'open' || filter === 'all' || filter === 'closed');
    const details = await Promise.all(
      open.slice(0, 8).map((t) => fetchStorylineDetail(t.threadId, token).catch(() => null)),
    );
    const stories = details.flatMap((d) => (d ? updatesToCards(d) : []));
    const storyIdToThreadId: Record<string, string> = {};
    for (const d of details) {
      if (!d) continue;
      for (const u of d.updates) storyIdToThreadId[u.storyId] = d.threadId;
    }
    setStorylineQueue(stories, { storyIdToThreadId });
  }, [items, filter, token, setStorylineQueue]);

  useFocusEffect(
    useCallback(() => {
      setSurface('storylines');
      // Leaving Home/reader for Storylines always stops wall/reader audio.
      void usePlayerStore.getState().stop();
      void refreshPlayQueue();
      return () => {
        void usePlayerStore.getState().stop();
      };
    }, [setSurface, refreshPlayQueue]),
  );

  const onScroll = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
      if (contentOffset.y + layoutMeasurement.height > contentSize.height - 320) {
        if (hasMore && !loadingMore) void loadMore();
      }
    },
    [hasMore, loadingMore, loadMore],
  );

  return (
    <Screen style={{ paddingTop: insets.top }}>
      <View style={styles.headerPad}>
        <Animated.Text
          entering={FadeInDown.duration(motion.duration.base)}
          style={[styles.heading, { color: colors.text }]}>
          Storylines
        </Animated.Text>
        <Text style={[styles.sub, { color: colors.textSecondary }]}>
          Follow a story as outlets update it — Play reads each brief in order.
        </Text>
        <View style={styles.segment}>
          {FILTERS.map((f) => {
            const active = filter === f.key;
            return (
              <Pressable
                key={f.key}
                onPress={() => setFilter(f.key)}
                style={[
                  styles.chip,
                  {
                    backgroundColor: active ? colors.text : colors.surface,
                    borderColor: active ? colors.text : colors.border,
                  },
                ]}>
                <Text
                  style={[
                    styles.chipText,
                    { color: active ? colors.background : colors.textSecondary },
                  ]}>
                  {f.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.accent} />
      ) : items.length === 0 ? (
        <EmptyState title="Quiet for now" message="Longer-running stories collect here." />
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          onScroll={onScroll}
          scrollEventThrottle={16}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={() => void refreshRandom()}
              tintColor={colors.accent}
            />
          }>
          {items.map((item, i) => (
            <Animated.View
              key={item.threadId}
              layout={LinearTransition.duration(motion.duration.fast)}
              entering={FadeInDown.delay(Math.min(i, 8) * 45).duration(motion.duration.base)}>
              <StorylineCard
                item={item}
                onPress={() =>
                  router.push({
                    pathname: '/(tabs)/storyline/[id]',
                    params: { id: item.threadId },
                  })
                }
              />
            </Animated.View>
          ))}
          {loadingMore ? (
            <ActivityIndicator style={{ marginVertical: 16 }} color={colors.accent} />
          ) : null}
        </ScrollView>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  headerPad: {
    paddingHorizontal: spacing.lg,
  },
  heading: {
    fontSize: 30,
    fontWeight: '800',
    letterSpacing: -0.6,
  },
  sub: {
    marginTop: 6,
    marginBottom: spacing.md,
    fontSize: 15,
    lineHeight: 21,
  },
  segment: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 110,
  },
});
