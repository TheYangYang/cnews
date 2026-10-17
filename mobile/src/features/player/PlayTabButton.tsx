import * as Haptics from 'expo-haptics';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useFeed } from '@/shared/hooks/useFeed';
import { useTheme } from '@/shared/theme/ThemeProvider';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/** Play is scoped to the focused page: Home wall, Search, in-tab reader, or Storylines. */
export function PlayTabButton() {
  const { colors } = useTheme();
  const { items } = useFeed();
  const visibleIds = useFeedUiStore((s) => s.visibleStoryIds);
  const wallReadingOrderIds = useFeedUiStore((s) => s.wallReadingOrderIds);
  const surface = usePlaySurfaceStore((s) => s.surface);
  const storylineStories = usePlaySurfaceStore((s) => s.storylineStories);
  const storylineOrderedIds = usePlaySurfaceStore((s) => s.storylineOrderedIds);
  const searchStories = usePlaySurfaceStore((s) => s.searchStories);
  const readerOrderedIds = usePlaySurfaceStore((s) => s.readerOrderedIds);
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const queueIndex = usePlayerStore((s) => s.queueIndex);
  const queue = usePlayerStore((s) => s.queue);
  const context = usePlayerStore((s) => s.context);
  const startWall = usePlayerStore((s) => s.startWallQueue);
  const startStorylines = usePlayerStore((s) => s.startStorylineQueue);
  const togglePause = usePlayerStore((s) => s.togglePause);
  const stop = usePlayerStore((s) => s.stop);
  const scale = useSharedValue(1);

  // Reader + home wall both use the wall player context.
  const expectedContext = surface === 'storylines' ? 'storylines' : 'wall';
  const belongsHere = context === expectedContext;

  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const startCurrentPage = () => {
    if (surface === 'storylines') {
      if (!storylineStories.length) {
        usePlayerStore.setState({ toastMessage: 'No storyline briefs ready yet' });
        return;
      }
      void startStorylines(storylineStories, storylineOrderedIds).catch(() => {
        void stop();
      });
      return;
    }

    if (surface === 'search') {
      if (!searchStories.length) {
        usePlayerStore.setState({ toastMessage: 'Search for a story first' });
        return;
      }
      const ordered = searchStories.map((s) => s.storyId);
      void startWall(searchStories, ordered).catch(() => {
        void stop();
      });
      return;
    }

    // In-tab reader: start from the open card, then continue down this pager.
    if (surface === 'reader') {
      const ordered =
        readerOrderedIds.length > 0 ? readerOrderedIds : items.map((s) => s.storyId);
      const fromSearch = usePlaySurfaceStore.getState().readerSource === 'search';
      const pool = fromSearch && searchStories.length ? searchStories : items;
      void startWall(pool, ordered).catch(() => {
        void stop();
      });
      return;
    }

    // Home wall: left→right, top→bottom (visible first; else full masonry order).
    const ordered = visibleIds.length
      ? visibleIds
      : wallReadingOrderIds.length
        ? wallReadingOrderIds
        : items.map((s) => s.storyId);
    void startWall(items, ordered).catch(() => {
      void stop();
    });
  };

  const onPress = () => {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    // Pause/resume only the queue for this page — never another tab's audio.
    if (belongsHere && (isPlaying || queue.length > 0)) {
      void togglePause();
      return;
    }
    startCurrentPage();
  };

  const onLongPress = () => {
    void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    void stop();
  };

  const progress =
    belongsHere && queue.length > 0
      ? `${Math.min(queueIndex + 1, queue.length)}/${queue.length}`
      : null;
  const showPause = belongsHere && isPlaying;

  return (
    <AnimatedPressable
      onPress={onPress}
      onLongPress={onLongPress}
      onPressIn={() => {
        scale.value = withSpring(0.92, { damping: 16, stiffness: 320 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 14, stiffness: 260 });
      }}
      style={[styles.wrap, anim]}
      accessibilityRole="button"
      accessibilityLabel={showPause ? 'Pause brief' : 'Play news briefs'}
      accessibilityHint="Long press to stop">
      <View
        style={[
          styles.button,
          {
            backgroundColor: colors.accentBright,
            shadowColor: colors.ink,
            borderColor: colors.surface,
          },
        ]}>
        <Ionicons name={showPause ? 'pause' : 'play'} size={26} color={colors.onAccent} />
      </View>
      {progress ? (
        <Text style={[styles.progress, { color: colors.textMuted }]}>{progress}</Text>
      ) : null}
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    top: -16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  button: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    shadowOpacity: 0.22,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  progress: {
    marginTop: 3,
    fontSize: 10,
    fontWeight: '700',
  },
});
