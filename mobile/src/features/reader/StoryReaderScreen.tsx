import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
  type ViewToken,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeIn } from 'react-native-reanimated';

import { ReaderPage } from '@/features/reader/ReaderPage';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useFeed } from '@/shared/hooks/useFeed';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import type { StoryCard } from '@/data/types/api';

type Props = {
  storyId: string;
};

/**
 * Full-screen vertical pager above the tab bar.
 * Opening a card never starts audio — only the Play tab does.
 * Opening the *currently speaking* card keeps Play going; back to Home keeps it going.
 * Opening / swiping to a *different* card stops Play.
 */
export function StoryReaderScreen({ storyId }: Props) {
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { items: feedItems, isLoading, loadMore, hasMore, loadingMore } = useFeed();
  const searchStories = usePlaySurfaceStore((s) => s.searchStories);
  const readerSource = usePlaySurfaceStore((s) => s.readerSource);
  const setSurface = usePlaySurfaceStore((s) => s.setSurface);
  const setReaderQueue = usePlaySurfaceStore((s) => s.setReaderQueue);
  const clearReaderQueue = usePlaySurfaceStore((s) => s.clearReaderQueue);
  const fromSearch =
    readerSource === 'search' && searchStories.some((s) => s.storyId === storyId);
  const items = fromSearch ? searchStories : feedItems;
  const listRef = useRef<FlatList<StoryCard>>(null);

  const [pageH, setPageH] = useState(0);
  const [index, setIndex] = useState(0);
  const [webOpen, setWebOpen] = useState(false);
  const indexRef = useRef(0);
  const itemsRef = useRef(items);
  const itemsLenRef = useRef(0);
  const hasMoreRef = useRef(false);
  const loadingMoreRef = useRef(false);
  const loadMoreRef = useRef(loadMore);

  const fromSearchRef = useRef(fromSearch);
  itemsRef.current = items;
  itemsLenRef.current = items.length;
  hasMoreRef.current = hasMore;
  loadingMoreRef.current = loadingMore;
  loadMoreRef.current = loadMore;
  fromSearchRef.current = fromSearch;

  const startIndex = useMemo(() => {
    const i = items.findIndex((s) => s.storyId === storyId);
    return i >= 0 ? i : 0;
  }, [items, storyId]);

  const syncReaderPlayQueue = useCallback(
    (fromIndex: number) => {
      const list = itemsRef.current;
      if (!list.length) {
        setReaderQueue([]);
        return;
      }
      const start = Math.max(0, Math.min(fromIndex, list.length - 1));
      setReaderQueue(list.slice(start).map((s) => s.storyId));
    },
    [setReaderQueue],
  );

  useFocusEffect(
    useCallback(() => {
      setSurface('reader');
      const speaking = useFeedUiStore.getState().speakingStoryId;
      // Only stop when this open card is not the one already playing.
      if (speaking && speaking !== storyId) {
        void usePlayerStore.getState().stop();
      }
      syncReaderPlayQueue(indexRef.current);
      return () => {
        // Back to Home: keep audio. Storylines/Settings stop on their own focus.
        clearReaderQueue();
      };
    }, [setSurface, syncReaderPlayQueue, clearReaderQueue, storyId]),
  );

  // Jump pager to the opened card. Runs when the card, the page height, or the first
  // page of items arrives — never on pagination, which must not move the pager or stop Play.
  const hasItems = items.length > 0;
  const startIndexRef = useRef(startIndex);
  startIndexRef.current = startIndex;
  useEffect(() => {
    if (!hasItems) return;
    const target = startIndexRef.current;
    setWebOpen(false);
    setIndex(target);
    indexRef.current = target;
    syncReaderPlayQueue(target);
    if (pageH <= 0) return;
    const id = requestAnimationFrame(() => {
      listRef.current?.scrollToIndex({ index: target, animated: false });
    });
    return () => cancelAnimationFrame(id);
  }, [storyId, hasItems, pageH, syncReaderPlayQueue]);

  // Keep reader Play order in sync when the feed grows (pagination).
  useEffect(() => {
    if (!items.length) return;
    syncReaderPlayQueue(indexRef.current);
  }, [items, syncReaderPlayQueue]);

  const goHome = useCallback(() => {
    if (router.canGoBack()) router.back();
    else router.replace('/(tabs)');
  }, [router]);

  const scrollToIndex = useCallback(
    (next: number, animated = true) => {
      if (next < 0 || next >= items.length || pageH <= 0) return;
      listRef.current?.scrollToIndex({ index: next, animated });
      indexRef.current = next;
      setIndex(next);
    },
    [items.length, pageH],
  );

  const syncReaderPlayQueueRef = useRef(syncReaderPlayQueue);
  syncReaderPlayQueueRef.current = syncReaderPlayQueue;

  const onViewableItemsChanged = useRef(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      const v = viewableItems[0];
      if (v?.index == null) return;
      if (v.index === indexRef.current) return;
      indexRef.current = v.index;
      setIndex(v.index);
      const nextId = itemsRef.current[v.index]?.storyId;
      const speaking = useFeedUiStore.getState().speakingStoryId;
      // Swiped away from the speaking card → stop; Play will start from this page.
      if (speaking && nextId && speaking !== nextId) {
        void usePlayerStore.getState().stop();
      }
      syncReaderPlayQueueRef.current(v.index);
      if (
        !fromSearchRef.current &&
        v.index >= itemsLenRef.current - 3 &&
        hasMoreRef.current &&
        !loadingMoreRef.current
      ) {
        void loadMoreRef.current();
      }
    },
  ).current;

  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 70,
  }).current;

  const onMomentumScrollEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (pageH <= 0) return;
    const next = Math.round(e.nativeEvent.contentOffset.y / pageH);
    if (next !== indexRef.current && next >= 0 && next < items.length) {
      indexRef.current = next;
      setIndex(next);
    }
  };

  const current = items[index];

  if (isLoading && !items.length) {
    return (
      <View style={[styles.loading, { backgroundColor: colors.readerBg }]}>
        <ActivityIndicator color={colors.accentBright} />
      </View>
    );
  }

  if (!items.length) {
    return (
      <View style={[styles.loading, { backgroundColor: colors.readerBg }]}>
        <Text style={{ color: colors.readerMuted }}>Story unavailable</Text>
        <Pressable onPress={goHome}>
          <Text style={{ color: colors.accentBright, fontWeight: '600' }}>Back to Home</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <Animated.View
      entering={FadeIn.duration(motion.duration.base)}
      style={[styles.root, { backgroundColor: colors.readerBg }]}
      onLayout={(e) => {
        const h = Math.round(e.nativeEvent.layout.height);
        if (h > 0 && h !== pageH) setPageH(h);
      }}>
      {pageH > 0 ? (
        <FlatList
          ref={listRef}
          key={`reader-${storyId}`}
          data={items}
          keyExtractor={(item) => item.storyId}
          pagingEnabled
          decelerationRate="fast"
          showsVerticalScrollIndicator={false}
          scrollEnabled={!webOpen}
          bounces={!webOpen}
          initialScrollIndex={Math.min(startIndex, Math.max(items.length - 1, 0))}
          getItemLayout={(_, i) => ({
            length: pageH,
            offset: pageH * i,
            index: i,
          })}
          onScrollToIndexFailed={({ index: i }) => {
            requestAnimationFrame(() => scrollToIndex(i, false));
          }}
          onMomentumScrollEnd={onMomentumScrollEnd}
          onViewableItemsChanged={onViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          renderItem={({ item }) => (
            <View style={{ height: pageH, width: '100%' }}>
              <ReaderPage
                story={item}
                viewportHeight={pageH}
                onOriginalOpenChange={setWebOpen}
              />
            </View>
          )}
        />
      ) : null}

      {!webOpen ? (
        <View style={[styles.topChrome, { paddingTop: insets.top + 4 }]} pointerEvents="box-none">
          <BlurView intensity={28} tint="dark" style={styles.chromeBlur}>
            <Pressable
              onPress={goHome}
              hitSlop={12}
              style={styles.chromeBtn}
              accessibilityLabel="Back to home feed">
              <Ionicons name="chevron-back" size={22} color="#fff" />
            </Pressable>
            <Text style={styles.indicator} numberOfLines={1}>
              {current?.outlet ?? 'Brief'}
              {items.length > 1 ? ` · ${index + 1}/${items.length}` : ''}
            </Text>
            <View style={styles.chromeBtn}>
              <Ionicons name="chevron-down" size={18} color="rgba(255,255,255,0.55)" />
            </View>
          </BlurView>
        </View>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  topChrome: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 12,
  },
  chromeBlur: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 18,
    overflow: 'hidden',
    paddingHorizontal: 6,
    paddingVertical: 4,
    backgroundColor: 'rgba(8,12,20,0.28)',
  },
  chromeBtn: {
    width: 40,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  indicator: {
    flex: 1,
    textAlign: 'center',
    fontSize: 13,
    color: 'rgba(255,255,255,0.88)',
    fontWeight: '700',
    letterSpacing: 0.2,
  },
});
