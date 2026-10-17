import { Image } from 'expo-image';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { StoryCard } from '@/data/types/api';
import { getApiBaseUrl } from '@/data/api/config';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { spacing } from '@/shared/theme/spacing';
import { formatRelativeTime } from '@/shared/utils/time';

type Props = {
  story: StoryCard;
  onPress: () => void;
};

function coverUri(story: StoryCard): string {
  const raw = story.imageUrl
    ? (rewriteMediaUrl(story.imageUrl) ?? story.imageUrl)
    : `${getApiBaseUrl().replace(/\/$/, '')}/media/covers/${story.storyId}.jpg`;
  return raw;
}

export function SearchStoryRow({ story, onPress }: Props) {
  const { colors } = useTheme();
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const listening = speakingId === story.storyId;
  const uri = coverUri(story);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        {
          backgroundColor: colors.surface,
          borderColor: listening ? colors.accentBright : colors.border,
          borderWidth: listening ? 2 : StyleSheet.hairlineWidth,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
      accessibilityRole="button"
      accessibilityLabel={`${story.title}, ${story.outlet}`}>
      {uri ? (
        <Image source={{ uri }} style={styles.thumb} contentFit="cover" />
      ) : (
        <View style={[styles.thumb, { backgroundColor: colors.ink }]} />
      )}
      <View style={styles.body}>
        <Text style={[styles.kicker, { color: colors.textMuted }]} numberOfLines={1}>
          {story.outlet}
          {story.place ? ` · ${story.place}` : ''}
          {story.publishedAt ? ` · ${formatRelativeTime(story.publishedAt)}` : ''}
        </Text>
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={2}>
          {story.title}
        </Text>
        {listening ? (
          <Text style={[styles.now, { color: colors.accentBright }]}>Playing brief</Text>
        ) : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: 16,
    marginBottom: spacing.sm,
  },
  thumb: {
    width: 72,
    height: 72,
    borderRadius: 12,
  },
  body: { flex: 1, justifyContent: 'center' },
  kicker: { fontSize: 12, fontWeight: '600', marginBottom: 4 },
  title: { fontSize: 16, fontWeight: '700', lineHeight: 21 },
  now: { marginTop: 4, fontSize: 12, fontWeight: '700' },
});
