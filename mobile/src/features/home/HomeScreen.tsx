import * as WebBrowser from 'expo-web-browser';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown, FadeOutUp } from 'react-native-reanimated';

import { MasonryWall } from '@/features/home/MasonryWall';
import { storiesToWall } from '@/features/home/mixDisplayAds';
import { useFeed } from '@/shared/hooks/useFeed';
import { MasonrySkeleton } from '@/shared/components/MasonrySkeleton';
import { EmptyState } from '@/shared/components/EmptyState';
import { Screen } from '@/shared/components/Screen';
import type { DisplayAd, StoryCard } from '@/data/types/api';
import { masonryReadingOrder, useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { columnWidthForScreen, splitIntoMasonryColumns } from '@/shared/utils/masonry';

export function HomeScreen() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const router = useRouter();
  const setSurface = usePlaySurfaceStore((s) => s.setSurface);
  const setReaderSource = usePlaySurfaceStore((s) => s.setReaderSource);
  const rebindWallQueueTail = usePlayerStore((s) => s.rebindWallQueueTail);

  useFocusEffect(
    useCallback(() => {
      const prev = usePlaySurfaceStore.getState().surface;
      setSurface('home');
      if (prev === 'search') {
        void usePlayerStore.getState().stop();
      }
    }, [setSurface]),
  );
  const {
    items,
    wallItems,
    isLoading,
    refreshRandom,
    isRefetching,
    loadMore,
    hasMore,
    loadingMore,
  } = useFeed();
  const scrollRef = useRef<ScrollView>(null);
  const [updatedToast, setUpdatedToast] = useState<string | null>(null);

  const onStoryPress = useCallback(
    (story: StoryCard) => {
      const speaking = useFeedUiStore.getState().speakingStoryId;
      if (speaking && speaking !== story.storyId) {
        void usePlayerStore.getState().stop();
      }
      setReaderSource('feed');
      router.push({
        pathname: '/(tabs)/story/[id]',
        params: { id: story.storyId },
      });
    },
    [router, setReaderSource],
  );

  const onAdPress = useCallback(async (ad: DisplayAd) => {
    if (!ad.clickUrl) return;
    await WebBrowser.openBrowserAsync(ad.clickUrl);
  }, []);

  useEffect(() => {
    if (!updatedToast) return;
    const t = setTimeout(() => setUpdatedToast(null), 2500);
    return () => clearTimeout(t);
  }, [updatedToast]);

  const onRefresh = useCallback(async () => {
    const next = await refreshRandom();
    if (next.length > 0) setUpdatedToast('Updated · fresh mix');

    const player = usePlayerStore.getState();
    if (player.context === 'wall' && player.queue.length > 0 && next.length > 0) {
      const colW = columnWidthForScreen(width);
      const { left, right } = splitIntoMasonryColumns(storiesToWall(next), colW);
      const orderedIds = masonryReadingOrder(left, right);
      rebindWallQueueTail(next, orderedIds);
    }
  }, [refreshRandom, width, rebindWallQueueTail]);

  const onNearEnd = useCallback(() => {
    if (hasMore && !loadingMore) void loadMore();
  }, [hasMore, loadingMore, loadMore]);

  return (
    <Screen static style={{ paddingTop: insets.top }}>
      {isLoading ? (
        <Animated.View entering={FadeIn.duration(motion.duration.fast)} style={{ flex: 1 }}>
          <MasonrySkeleton />
        </Animated.View>
      ) : items.length === 0 ? (
        <EmptyState
          title="Nothing to show"
          message="No stories match your topics yet."
          actionLabel="Adjust topics"
          onAction={() => router.push('/(tabs)/settings')}
        />
      ) : (
        <MasonryWall
          items={wallItems}
          onStoryPress={onStoryPress}
          onAdPress={onAdPress}
          scrollRef={scrollRef}
          onNearEnd={onNearEnd}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={onRefresh}
              tintColor={colors.accent}
              progressViewOffset={insets.top}
            />
          }
        />
      )}
      {updatedToast ? (
        <Animated.View
          entering={FadeInDown.duration(motion.duration.fast)}
          exiting={FadeOutUp.duration(motion.duration.fast)}
          style={[styles.updated, { top: insets.top + 8, backgroundColor: colors.toastBg }]}>
          <Text style={[styles.updatedText, { color: colors.toastText }]}>{updatedToast}</Text>
        </Animated.View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  updated: {
    position: 'absolute',
    alignSelf: 'center',
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 999,
  },
  updatedText: {
    fontSize: 13,
    fontWeight: '600',
  },
});
