import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import type { StoryCard } from '@/data/types/api';
import { getApiBaseUrl } from '@/data/api/config';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { formatRelativeTime } from '@/shared/utils/time';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = {
  story: StoryCard;
  width: number;
  minHeight?: number;
  onPress: () => void;
};

function coverUri(story: StoryCard): string {
  const raw = story.imageUrl
    ? (rewriteMediaUrl(story.imageUrl) ?? story.imageUrl)
    : `${getApiBaseUrl().replace(/\/$/, '')}/media/covers/${story.storyId}.jpg`;
  try {
    const u = new URL(raw);
    u.search = '';
    return u.toString();
  } catch {
    return raw;
  }
}

export function FeedCard({ story, width, minHeight, onPress }: Props) {
  const { colors } = useTheme();
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const isSpeaking = speakingId === story.storyId;
  const aspect = story.imageAspect && story.imageAspect > 0.45 ? story.imageAspect : 0.72;
  const height = Math.max(width / aspect, minHeight ?? 0);
  const multi =
    (story.clusterSize && story.clusterSize >= 2) || Boolean(story.clusterId);
  const scale = useSharedValue(1);

  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(0.975, { damping: 18, stiffness: 320 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 16, stiffness: 280 });
      }}
      style={[
        styles.card,
        {
          width,
          height,
          backgroundColor: colors.ink,
          borderColor: isSpeaking ? colors.accentBright : 'transparent',
          borderWidth: isSpeaking ? 2.5 : 0,
        },
        anim,
      ]}
      accessibilityRole="button"
      accessibilityLabel={`${story.title}, ${story.outlet}`}>
      <Image
        source={{ uri: coverUri(story) }}
        style={StyleSheet.absoluteFill}
        contentFit="cover"
        transition={200}
        recyclingKey={story.storyId}
      />
      <LinearGradient
        colors={['rgba(20,24,31,0.04)', 'rgba(20,24,31,0.4)', colors.imageScrim]}
        locations={[0.28, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.copy}>
        <Text style={styles.title} numberOfLines={3}>
          {story.title}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {story.outlet} · {formatRelativeTime(story.publishedAt)}
          {multi ? ' · Sources' : ''}
        </Text>
      </View>
      {isSpeaking ? (
        <View style={[styles.liveBadge, { backgroundColor: colors.accent }]}>
          <View style={styles.liveDot} />
          <Text style={[styles.liveText, { color: colors.onAccent }]}>Listening</Text>
        </View>
      ) : null}
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: 4,
  },
  copy: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 11,
    paddingBottom: 11,
    paddingTop: 36,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 18.5,
    letterSpacing: -0.25,
  },
  meta: {
    marginTop: 5,
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.78)',
  },
  liveBadge: {
    position: 'absolute',
    top: 8,
    left: 8,
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
  liveText: {
    fontSize: 10,
    fontWeight: '700',
  },
});
