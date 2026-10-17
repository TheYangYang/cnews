import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { StorylineSummary } from '@/data/types/api';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { spacing } from '@/shared/theme/spacing';
import { formatRelativeTime } from '@/shared/utils/time';

type Props = {
  item: StorylineSummary;
  onPress: () => void;
};

export function StorylineRow({ item, onPress }: Props) {
  const { colors } = useTheme();
  const ongoing = item.status === 'open';
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.9 : 1,
        },
      ]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={2}>
          {item.title}
        </Text>
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
      </View>
      <Text style={[styles.meta, { color: colors.textMuted }]}>
        {item.updateCount} updates · {formatRelativeTime(item.updatedAt)}
        {item.topic ? ` · ${item.topic}` : ''}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    padding: spacing.lg,
    borderRadius: 16,
    marginBottom: spacing.sm,
    borderWidth: StyleSheet.hairlineWidth,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: 6,
  },
  title: {
    flex: 1,
    fontSize: 17,
    fontWeight: '700',
    lineHeight: 22,
  },
  tag: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  tagText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.3 },
  meta: {
    fontSize: 13,
  },
});
