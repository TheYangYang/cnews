import { useQuery } from '@tanstack/react-query';
import { Pressable, ScrollView, StyleSheet, Text, View, ActivityIndicator } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { fetchStorylineDetail } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';
import { formatRelativeTime } from '@/shared/utils/time';
import { usePlayerStore } from '@/data/stores/playerStore';
import type { StorylineUpdate } from '@/data/types/api';
import { Screen } from '@/shared/components/Screen';

type Props = { threadId: string };

function TimelineItem({
  update,
  isLast,
  index,
}: {
  update: StorylineUpdate;
  isLast: boolean;
  index: number;
}) {
  const { colors } = useTheme();
  const playReader = usePlayerStore((s) => s.playReaderStory);
  const when = update.at ?? update.publishedAt ?? new Date().toISOString();
  const text = update.summary ?? update.brief ?? update.title ?? '';

  const play = () => {
    void playReader({
      storyId: update.storyId,
      title: update.title ?? text,
      summary: text,
      summaryPreview: text,
      imageUrl: update.imageUrl ?? null,
      outlet: update.outlet,
      topic: '',
      publishedAt: when,
      sourceUrl: update.sourceUrl ?? '',
      audioStatus: update.audioStatus,
      audioUrl: update.audioUrl,
    });
  };

  return (
    <Animated.View
      entering={FadeInDown.delay(Math.min(index, 8) * 50).duration(motion.duration.base)}
      style={styles.itemRow}>
      <View style={styles.lineCol}>
        <View style={[styles.dot, { backgroundColor: colors.accent }]} />
        {!isLast ? <View style={[styles.line, { backgroundColor: colors.border }]} /> : null}
      </View>
      <View style={styles.itemBody}>
        <Text style={[styles.itemMeta, { color: colors.textMuted }]}>
          {formatRelativeTime(when)} · {update.outlet}
        </Text>
        <Text style={[styles.itemBrief, { color: colors.text }]}>{text}</Text>
        {update.audioStatus === 'ready' ? (
          <Pressable onPress={play} style={styles.playBtn}>
            <Ionicons name="play" size={14} color={colors.accent} />
            <Text style={[styles.playBtnText, { color: colors.accent }]}>Play</Text>
          </Pressable>
        ) : null}
      </View>
    </Animated.View>
  );
}

export function StorylineDetailScreen({ threadId }: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const token = useAuthStore((s) => s.accessToken);

  const query = useQuery({
    queryKey: ['storyline', threadId],
    queryFn: () => fetchStorylineDetail(threadId, token),
  });

  const detail = query.data;
  const ongoing = detail?.status === 'open';

  return (
    <Screen style={{ paddingTop: insets.top }}>
      <Pressable onPress={() => router.back()} style={styles.back} hitSlop={12}>
        <Ionicons name="chevron-back" size={24} color={colors.text} />
      </Pressable>
      {query.isLoading || !detail ? (
        <ActivityIndicator color={colors.accent} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          <Animated.View
            entering={FadeInDown.duration(motion.duration.base)}
            style={styles.titleRow}>
            <Text style={[styles.title, { color: colors.text }]}>{detail.title}</Text>
            <View
              style={[
                styles.tag,
                { backgroundColor: ongoing ? colors.ongoingBg : colors.closedBg },
              ]}>
              <Text
                style={[
                  styles.tagText,
                  { color: ongoing ? colors.ongoing : colors.closed },
                ]}>
                {ongoing ? 'Ongoing' : 'Closed'}
              </Text>
            </View>
          </Animated.View>
          {detail.updates.map((u, i) => (
            <TimelineItem
              key={u.storyId + String(u.publishedAt ?? u.at ?? i)}
              update={u}
              isLast={i === detail.updates.length - 1}
              index={i}
            />
          ))}
        </ScrollView>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  back: { paddingHorizontal: spacing.lg, paddingBottom: spacing.sm },
  content: { paddingHorizontal: spacing.lg, paddingBottom: 40 },
  titleRow: { gap: spacing.sm, marginBottom: spacing.lg },
  title: {
    fontSize: 26,
    fontWeight: '800',
    lineHeight: 32,
  },
  tag: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  tagText: { fontSize: 12, fontWeight: '700' },
  itemRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.lg },
  lineCol: { width: 12, alignItems: 'center' },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
  },
  line: {
    flex: 1,
    width: 2,
    marginTop: 4,
  },
  itemBody: { flex: 1 },
  itemMeta: { fontSize: 12, marginBottom: 4 },
  itemBrief: { fontSize: 16, lineHeight: 23 },
  playBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
  },
  playBtnText: { fontWeight: '600', fontSize: 14 },
});
