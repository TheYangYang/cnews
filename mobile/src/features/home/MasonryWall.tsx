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
      setVisible(ids);
    },
    [left, right, viewportHeight, setVisible],
  );

  const handleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const y = e.nativeEvent.contentOffset.y;
    scrollYRef.current = y;
    onScroll?.(y);
    recomputeVisible(y);
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
    if (contentOffset.y + layoutMeasurement.height > contentSize.height - 320) {
      onNearEnd?.();
    }
  };

  const leftHeights = useMemo(
    () => left.map((s) => estimateCardHeight(s, colW)),
    [left, colW],
  );
  const rightHeights = useMemo(
    () => right.map((s) => estimateCardHeight(s, colW)),
    [right, colW],
  );

  useEffect(() => {
    let acc = 0;
    leftOffsetsRef.current = leftHeights.map((h) => {
      const y = acc;
      acc += h;
      return y;
    });
    acc = 0;
    rightOffsetsRef.current = rightHeights.map((h) => {
      const y = acc;
      acc += h;
      return y;
    });
    recomputeVisible(scrollYRef.current);
  }, [leftHeights, rightHeights, recomputeVisible, layoutTick]);

  useEffect(() => {
    if (!speakingId || !scrollRef?.current) return;
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
  }, [speakingId, left, right, scrollRef]);

  const renderCard = (item: WallItem, i: number, delay: number) => (
    <Animated.View
      key={wallItemId(item)}
      entering={FadeInDown.delay(Math.min(i, 6) * 40 + delay)
        .duration(motion.duration.base)
        .easing(motion.easing.out)}>
      {item.kind === 'ad' ? (
        <AdCard ad={item.ad} width={colW} onPress={() => onAdPress(item.ad)} />
      ) : (
        <FeedCard story={item.story} width={colW} onPress={() => onStoryPress(item.story)} />
      )}
    </Animated.View>
  );

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
        <View style={styles.column}>{left.map((item, i) => renderCard(item, i, 0))}</View>
        <View style={styles.column}>{right.map((item, i) => renderCard(item, i, 30))}</View>
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
