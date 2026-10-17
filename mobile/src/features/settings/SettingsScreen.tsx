import { useFocusEffect } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import {
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { fetchTopicsMeta } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useSettingsStore } from '@/data/stores/settingsStore';
import { Screen } from '@/shared/components/Screen';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';

export function SettingsScreen() {
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();
  const token = useAuthStore((s) => s.accessToken);

  useFocusEffect(
    useCallback(() => {
      void usePlayerStore.getState().stop();
    }, []),
  );
  const selectedTopics = useSettingsStore((s) => s.selectedTopics);
  const toggleTopic = useSettingsStore((s) => s.toggleTopic);

  const topicsQuery = useQuery({
    queryKey: ['meta-topics'],
    queryFn: () => fetchTopicsMeta(token),
  });

  const card = {
    backgroundColor: colors.surface,
    borderColor: colors.border,
  };

  return (
    <Screen style={{ paddingTop: insets.top }}>
      <ScrollView contentContainerStyle={styles.content}>
        <Animated.View entering={FadeInDown.duration(motion.duration.base)}>
          <Text style={[styles.heading, { color: colors.ink }]}>Settings</Text>
          <Text style={[styles.sub, { color: colors.textSecondary }]}>
            Tune topics on your wall. Play only reads spoken briefs. Appearance follows your system
            theme ({isDark ? 'Dark' : 'Light'}).
          </Text>
        </Animated.View>

        <Text style={[styles.section, { color: colors.textMuted }]}>Topics</Text>
        <Animated.View
          entering={FadeInDown.delay(60).duration(motion.duration.base)}
          style={[styles.card, card]}>
          {topicsQuery.isLoading ? (
            <ActivityIndicator color={colors.accent} />
          ) : (
            topicsQuery.data?.topics.map((t) => {
              const on = selectedTopics.includes(t.id);
              return (
                <View key={t.id} style={styles.topicRow}>
                  <Text style={[styles.topicLabel, { color: colors.text }]}>{t.label}</Text>
                  <Switch
                    value={on}
                    onValueChange={() => void toggleTopic(t.id)}
                    trackColor={{ true: colors.accent, false: colors.border }}
                    thumbColor={colors.surface}
                  />
                </View>
              );
            })
          )}
        </Animated.View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: spacing.lg, paddingBottom: 40 },
  heading: {
    fontSize: 30,
    fontWeight: '800',
    letterSpacing: -0.6,
  },
  sub: {
    marginTop: 6,
    marginBottom: spacing.lg,
    fontSize: 15,
    lineHeight: 21,
  },
  section: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: spacing.sm,
    marginTop: spacing.md,
  },
  card: {
    borderRadius: 16,
    padding: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
  },
  topicRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  topicLabel: { fontSize: 16, fontWeight: '500' },
});
