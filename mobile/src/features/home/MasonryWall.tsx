import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  NativeScrollEvent,
  NativeSyntheticEvent,
  RefreshControl,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { NativeWallAdCard } from '@/features/ads/NativeAdCards';
import { AdCard } from '@/features/home/AdCard';
import { FeedCard } from '@/features/home/FeedCard';
import { wallItemId } from '@/features/home/mixDisplayAds';
import type { DisplayAd, StoryCard, WallItem } from '@/data/types/api';
import {
  splitIntoMasonryColumns,
  columnWidthForScreen,
  estimateCardHeight,
  GAP,
  PAD,
} from '@/shared/utils/masonry';
import {
  useFeedUiStore,
  masonryReadingOrder,
  visiblePlayOrder,
} from '@/data/stores/feedUiStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';

type Props = {
  items: WallItem[];
  onStoryPress: (story: StoryCard) => void;
  onAdPress: (ad: DisplayAd) => void;
  onScroll?: (y: number) => void;
  onNearEnd?: () => void;
  scrollRef?: React.RefObject<ScrollView | null>;
  refreshControl?: React.ReactElement<React.ComponentProps<typeof RefreshControl>>;
};

const TAB_BAR = 90;

/** Screens of cards kept mounted above and below the viewport. */
const WINDOW_SCREENS = 1.5;

type ColumnLayout = { offsets: number[]; heights: number[]; total: number };

function columnLayout(items: WallItem[], columnWidth: number): ColumnLayout {
  const heights = items.map((item) => estimateCardHeight(item, columnWidth));
  const offsets: number[] = [];
  let total = 0;
  for (const h of heights) {
    offsets.push(total);
    total += h;
  }
  return { offsets, heights, total };
}

function sameIds(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((id, i) => id === b[i]);
}

export function MasonryWall({
  items,
  onStoryPress,
  onAdPress,
  onScroll,
  onNearEnd,
  scrollRef,
  refreshControl,
}: Props) {
  const { colors } = useTheme();
  const { width, height: viewportHeight } = useWindowDimensions();
  const colW = columnWidthForScreen(width);
  const { left, right } = useMemo(
    () => splitIntoMasonryColumns(items, colW),
    [items, colW],
  );
  const setVisible = useFeedUiStore((s) => s.setVisibleStoryIds);
  const setWallOrder = useFeedUiStore((s) => s.setWallReadingOrderIds);
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const leftOffsetsRef = useRef<number[]>([]);
  const rightOffsetsRef = useRef<number[]>([]);
  const scrollYRef = useRef(0);
  const [layoutTick, setLayoutTick] = useState(0);

  useEffect(() => {
    setWallOrder(masonryReadingOrder(left, right));
  }, [left, right, setWallOrder]);

  const recomputeVisible = useCallback(
    (scrollY: number) => {
      const ids = visiblePlayOrder(
        left,
        right,
        scrollY,
        viewportHeight,
        leftOffsetsRef.current,
        rightOffsetsRef.current,
      );
      // Scroll fires ~60×/s; only publish when the visible set actually changes.
      if (!sameIds(ids, useFeedUiStore.getState().visibleStoryIds)) setVisible(ids);
    },
    [left, right, viewportHeight, setVisible],
  );

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const y = e.nativeEvent.contentOffset.y;
    scrollYRef.current = y;
    const nextStep = Math.max(0, Math.floor(y / step));
    if (nextStep !== windowStep) setWindowStep(nextStep);
    onScroll?.(y);
    recomputeVisible(y);
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
    if (contentOffset.y + layoutMeasurement.height > contentSize.height - 320) {
      onNearEnd?.();
    }
  };

  // Card heights are exact (width / aspect + gap), so offsets are known without measuring.
  const leftCol = useMemo(() => columnLayout(left, colW), [left, colW]);
  const rightCol = useMemo(() => columnLayout(right, colW), [right, colW]);
  leftOffsetsRef.current = leftCol.offsets;
  rightOffsetsRef.current = rightCol.offsets;

  useEffect(() => {
    recomputeVisible(scrollYRef.current);
  }, [leftCol, rightCol, recomputeVisible, layoutTick]);

  // Virtualize: mount only cards within a few screens of the viewport, so memory stays
  // flat however far the wall scrolls. The window moves in half-screen steps, so scrolling
  // re-renders a couple of times per screen, not every frame.
  const step = Math.max(1, Math.round(viewportHeight / 2));
  const [windowStep, setWindowStep] = useState(0);
  const windowTop = windowStep * step - viewportHeight * WINDOW_SCREENS;
  const windowBottom = windowStep * step + viewportHeight * (1 + WINDOW_SCREENS);
  const animatedIds = useRef(new Set<string>());

  // Follow the speaking card when Play advances — not when pages load, which would
  // yank the wall back up while the reader scrolls down.
  const columnsRef = useRef({ left, right });
  columnsRef.current = { left, right };
  useEffect(() => {
    if (!speakingId || !scrollRef?.current) return;
    const { left, right } = columnsRef.current;
    const li = left.findIndex((s) => s.kind === 'story' && s.story.storyId === speakingId);
    const ri = right.findIndex((s) => s.kind === 'story' && s.story.storyId === speakingId);
    const y =
      li >= 0
        ? leftOffsetsRef.current[li]
        : ri >= 0
          ? rightOffsetsRef.current[ri]
          : null;
    if (y == null) return;
    scrollRef.current.scrollTo({ y: Math.max(0, y - 12), animated: true });
  }, [speakingId, scrollRef]);

  const renderCard = (item: WallItem, i: number, delay: number) => {
    // Fade in on first appearance only; a card remounted by the window just shows.
    const id = wallItemId(item);
    const firstTime = !animatedIds.current.has(id);
    animatedIds.current.add(id);
    return (
      <Animated.View
        key={id}
        entering={
          firstTime
            ? FadeInDown.delay(Math.min(i, 6) * 40 + delay)
                .duration(motion.duration.base)
                .easing(motion.easing.out)
            : undefined
        }>
        {item.kind === 'native' ? (
          <NativeWallAdCard slotId={item.slotId} width={colW} />
        ) : item.kind === 'ad' ? (
          <AdCard ad={item.ad} width={colW} onPress={() => onAdPress(item.ad)} />
        ) : (
          <FeedCard story={item.story} width={colW} onPress={() => onStoryPress(item.story)} />
        )}
      </Animated.View>
    );
  };

  const renderColumn = (
    items: WallItem[],
    layout: ColumnLayout,
    delay: number,
  ) => {
    const { offsets, heights, total } = layout;
    let first = offsets.findIndex((y, i) => y + heights[i]! >= windowTop);
    if (first < 0) first = items.length;
    let end = first;
    while (end < items.length && offsets[end]! <= windowBottom) end++;
    return (
      <View style={[styles.column, { height: total }]}>
        <View style={{ height: offsets[first] ?? total }} />
        {items.slice(first, end).map((item, k) => renderCard(item, first + k, delay))}
      </View>
    );
  };

  return (
    <ScrollView
      ref={scrollRef}
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={[styles.content, { paddingBottom: TAB_BAR + 8 }]}
      showsVerticalScrollIndicator={false}
      scrollEventThrottle={16}
      onScroll={handleScroll}
      refreshControl={refreshControl}
      onContentSizeChange={() => setLayoutTick((t) => t + 1)}>
      <View style={[styles.row, { paddingHorizontal: PAD }]}>
        {renderColumn(left, leftCol, 0)}
        {renderColumn(right, rightCol, 30)}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: 0,
    flexGrow: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: GAP,
  },
  column: { flex: 1 },
});
