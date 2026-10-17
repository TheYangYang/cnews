import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { SearchStoryRow } from '@/features/search/SearchStoryRow';
import { StorylineRow } from '@/features/storylines/StorylineRow';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { EmptyState } from '@/shared/components/EmptyState';
import { Screen } from '@/shared/components/Screen';
import { useSearch } from '@/shared/hooks/useSearch';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';
import type { StoryCard } from '@/data/types/api';

export function SearchScreen() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const setSurface = usePlaySurfaceStore((s) => s.setSurface);
  const setSearchQueue = usePlaySurfaceStore((s) => s.setSearchQueue);
  const setReaderSource = usePlaySurfaceStore((s) => s.setReaderSource);
  const { query, setQuery, stories, storylines, loading, error } = useSearch();

  useFocusEffect(
    useCallback(() => {
      const prev = usePlaySurfaceStore.getState().surface;
      setSurface('search');
      if (prev === 'home' || prev === 'storylines') {
        void usePlayerStore.getState().stop();
      }
    }, [setSurface]),
  );

  useFocusEffect(
    useCallback(() => {
      setSearchQueue(stories);
    }, [setSearchQueue, stories]),
  );

  const onStoryPress = useCallback(
    (story: StoryCard) => {
      const speaking = useFeedUiStore.getState().speakingStoryId;
      if (speaking && speaking !== story.storyId) {
        void usePlayerStore.getState().stop();
      }
      setReaderSource('search');
      router.push({
        pathname: '/(tabs)/story/[id]',
        params: { id: story.storyId },
      });
    },
    [router, setReaderSource],
  );

  const typed = query.trim().length >= 2;
  const empty = typed && !loading && stories.length === 0 && storylines.length === 0;

  return (
    <Screen style={{ paddingTop: insets.top }}>
      <View style={styles.header}>
        <Animated.Text
          entering={FadeInDown.duration(motion.duration.base)}
          style={[styles.heading, { color: colors.text }]}>
          Search
        </Animated.Text>
        <Text style={[styles.sub, { color: colors.textSecondary }]}>
          Find a brief or storyline. Play reads the matching stories.
        </Text>
        <View
          style={[
            styles.field,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}>
          <Ionicons name="search" size={18} color={colors.textMuted} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Calgary, CBC, wildfire…"
            placeholderTextColor={colors.textMuted}
            autoCorrect={false}
            autoCapitalize="none"
            returnKeyType="search"
            style={[styles.input, { color: colors.text }]}
            accessibilityLabel="Search news"
          />
          {query.length ? (
            <Pressable onPress={() => setQuery('')} hitSlop={8} accessibilityLabel="Clear search">
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.list}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag">
        {!typed ? (
          <EmptyState
            title="Search the briefs"
            message="Try a city, outlet, or word from a headline. Play speaks the results."
          />
        ) : null}

        {typed && loading && stories.length === 0 && storylines.length === 0 ? (
          <ActivityIndicator style={{ marginTop: 32 }} color={colors.accent} />
        ) : null}

        {error && empty ? (
          <EmptyState title="Couldn’t search" message={error} />
        ) : null}

        {empty && !error ? (
          <EmptyState
            title="No matches"
            message={`Nothing for “${query.trim()}”. Try another outlet, place, or word.`}
          />
        ) : null}

        {stories.length ? (
          <Text style={[styles.section, { color: colors.textMuted }]}>Stories</Text>
        ) : null}
        {stories.map((story) => (
          <SearchStoryRow
            key={story.storyId}
            story={story}
            onPress={() => onStoryPress(story)}
          />
        ))}

        {storylines.length ? (
          <Text style={[styles.section, { color: colors.textMuted, marginTop: spacing.lg }]}>
            Storylines
          </Text>
        ) : null}
        {storylines.map((item) => (
          <StorylineRow
            key={item.threadId}
            item={item}
            onPress={() =>
              router.push({
                pathname: '/(tabs)/storyline/[id]',
                params: { id: item.threadId },
              })
            }
          />
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: spacing.lg,
  },
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
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    minHeight: 48,
  },
  input: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 12,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 110,
  },
  section: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: spacing.sm,
  },
});
