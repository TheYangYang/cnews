import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import type { StorylineSummary } from '@/data/types/api';
import { getApiBaseUrl } from '@/data/api/config';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { formatRelativeTime } from '@/shared/utils/time';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = {
  item: StorylineSummary;
  onPress: () => void;
};

function coverUri(item: StorylineSummary): string {
  const raw = item.coverImageUrl
    ? (rewriteMediaUrl(item.coverImageUrl) ?? item.coverImageUrl)
    : item.latestStoryId
      ? `${getApiBaseUrl().replace(/\/$/, '')}/media/covers/${item.latestStoryId}.jpg`
      : '';
  return raw;
}

export function StorylineCard({ item, onPress }: Props) {
  const { colors } = useTheme();
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const storyIdToThreadId = usePlaySurfaceStore((s) => s.storyIdToThreadId);
  const isSpeaking =
    !!speakingId &&
    (speakingId === item.latestStoryId ||
      storyIdToThreadId[speakingId] === item.threadId);
  const ongoing = item.status === 'open';
  const scale = useSharedValue(1);
  const uri = coverUri(item);

  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(0.98, { damping: 18, stiffness: 320 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 16, stiffness: 280 });
      }}
      style={[
        styles.card,
        {
          borderColor: isSpeaking ? colors.accentBright : 'transparent',
          borderWidth: isSpeaking ? 2.5 : 0,
        },
        anim,
      ]}
      accessibilityRole="button"
      accessibilityLabel={`${item.title}, ${item.updateCount} updates`}>
      {uri ? (
        <Image source={{ uri }} style={StyleSheet.absoluteFill} contentFit="cover" transition={200} />
      ) : (
        <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.ink }]} />
      )}
      <LinearGradient
        colors={['rgba(20,24,31,0.1)', 'rgba(20,24,31,0.55)', colors.imageScrim]}
        locations={[0.2, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />

      <View style={styles.topRow}>
        <View
          style={[
            styles.status,
            { backgroundColor: ongoing ? colors.accentBright : 'rgba(255,255,255,0.22)' },
          ]}>
          <Text
            style={[
              styles.statusText,
              { color: ongoing ? colors.onAccent : '#fff' },
            ]}>
            {ongoing ? 'Ongoing' : 'Closed'}
          </Text>
        </View>
        {isSpeaking ? (
          <View style={[styles.live, { backgroundColor: colors.accent }]}>
            <View style={styles.liveDot} />
            <Text style={[styles.liveText, { color: colors.onAccent }]}>Listening</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.copy}>
        <Text style={styles.kicker} numberOfLines={1}>
          {[item.latestOutlet, item.place ?? item.topic].filter(Boolean).join(' · ')}
        </Text>
        <Text style={styles.title} numberOfLines={3}>
          {item.title}
        </Text>
        <Text style={styles.meta}>
          {item.updateCount} updates · {formatRelativeTime(item.updatedAt)}
        </Text>
      </View>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    height: 220,
    borderRadius: 18,
    overflow: 'hidden',
    marginBottom: 12,
    backgroundColor: '#14181F',
  },
  topRow: {
    position: 'absolute',
    top: 12,
    left: 12,
    right: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  status: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  live: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#1A1408',
  },
  liveText: { fontSize: 10, fontWeight: '700' },
  copy: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingBottom: 14,
    paddingTop: 40,
    gap: 6,
  },
  kicker: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: 'rgba(255,255,255,0.72)',
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: -0.4,
    lineHeight: 27,
  },
  meta: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.75)',
  },
});
