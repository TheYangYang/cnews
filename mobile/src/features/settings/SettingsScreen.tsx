import { useFocusEffect } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import {
  Alert,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { fetchTopicsMeta } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useSettingsStore } from '@/data/stores/settingsStore';
import { SUPPORT_LINKS, reportContentMailto } from '@/shared/config/support';
import { Screen } from '@/shared/components/Screen';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';

// App Store review treats an external tip link as bypassing in-app purchase; Android/web keep it.
const SHOW_SUPPORT = Platform.OS !== 'ios';

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

        {SHOW_SUPPORT ? (
          <Animated.View
            entering={FadeInDown.delay(60).duration(motion.duration.base)}
            style={[
              styles.support,
              { backgroundColor: colors.accentSoft, borderColor: colors.border },
            ]}>
            <Text style={[styles.supportTitle, { color: colors.ink }]}>Keep CrackNews independent</Text>
            <Text style={[styles.supportBody, { color: colors.textSecondary }]}>
              Briefs stay free. A coffee helps cover ingest and speech.
            </Text>
            <Pressable
              onPress={() => void WebBrowser.openBrowserAsync(SUPPORT_LINKS.buyMeACoffee)}
              style={[styles.supportBtn, { backgroundColor: colors.accentBright }]}
              accessibilityRole="link"
              accessibilityLabel="Buy us a coffee">
              <Ionicons name="cafe" size={16} color={colors.onAccent} />
              <Text style={[styles.supportBtnText, { color: colors.onAccent }]}>Buy us a coffee</Text>
            </Pressable>
          </Animated.View>
        ) : null}

        <Text style={[styles.section, { color: colors.textMuted }]}>Topics</Text>
        <Animated.View
          entering={FadeInDown.delay(120).duration(motion.duration.base)}
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

        <Text style={[styles.section, { color: colors.textMuted }]}>Content</Text>
        <Animated.View
          entering={FadeInDown.delay(180).duration(motion.duration.base)}
          style={[styles.card, card]}>
          <Pressable
            onPress={openReport}
            style={styles.linkRow}
            accessibilityRole="link"
            accessibilityLabel="Report content or request removal">
            <Ionicons name="flag-outline" size={18} color={colors.textSecondary} />
            <View style={{ flex: 1 }}>
              <Text style={[styles.topicLabel, { color: colors.text }]}>Report content</Text>
              <Text style={[styles.linkHint, { color: colors.textMuted }]}>
                Wrong brief, or a publisher asking for removal
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Text style={[styles.linkHint, { color: colors.textMuted }]}>
            Briefs are written by AI from each outlet&apos;s published story. Tap Original on any
            story to read the source.
          </Text>
        </Animated.View>
      </ScrollView>
    </Screen>
  );
}

async function openReport() {
  const url = reportContentMailto();
  try {
    await Linking.openURL(url);
  } catch {
    // No mail app configured: show the address so it can be copied.
    Alert.alert('Report content', `Email us at ${SUPPORT_LINKS.contactEmail}`);
  }
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: spacing.lg, paddingBottom: 110 },
  heading: {
    fontSize: 30,
    fontWeight: '800',
    letterSpacing: -0.6,
  },
  sub: {
    marginTop: 6,
    marginBottom: spacing.md,
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
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: 4 },
  linkHint: { fontSize: 13, lineHeight: 18, marginTop: 2 },
  support: {
    borderRadius: 16,
    padding: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  supportTitle: { fontSize: 17, fontWeight: '700' },
  supportBody: { fontSize: 14, lineHeight: 20 },
  supportBtn: {
    marginTop: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 12,
  },
  supportBtnText: { fontSize: 15, fontWeight: '700' },
});
