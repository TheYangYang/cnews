import { useEffect, useState } from 'react';
import { Image, StyleSheet } from 'react-native';
import Animated, {
  FadeIn,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { fetchHomeFeed } from '@/data/api/endpoints';
import { upsertFeedStories } from '@/data/db/feedRepository';
import { useAuthStore } from '@/data/stores/authStore';
import { useSettingsStore } from '@/data/stores/settingsStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';

type Props = {
  children: React.ReactNode;
};

/**
 * X-style preload: pure black + centered mark only.
 * Prefetch runs in the background; no copy, no spinner.
 */
export function BootstrapGate({ children }: Props) {
  const { colors } = useTheme();
  const [ready, setReady] = useState(false);
  const pulse = useSharedValue(1);

  useEffect(() => {
    pulse.value = withRepeat(withTiming(0.94, { duration: 650 }), -1, true);
  }, [pulse]);

  useEffect(() => {
    let cancelled = false;
    const started = Date.now();

    void (async () => {
      await useSettingsStore.getState().hydrateFromSqlite().catch(() => undefined);

      const remain = Math.max(0, 260 - (Date.now() - started));
      await new Promise((r) => setTimeout(r, remain));
      if (!cancelled) setReady(true);

      const topics = useSettingsStore.getState().selectedTopics;
      const token = useAuthStore.getState().accessToken;
      void fetchHomeFeed({ topics, limit: 10, token, mode: 'any' })
        .then((feed) => upsertFeedStories(feed.items))
        .catch(() => undefined);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const markStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
    opacity: 0.7 + pulse.value * 0.3,
  }));

  if (ready) {
    return (
      <Animated.View
        entering={FadeIn.duration(motion.duration.fast)}
        style={{ flex: 1, backgroundColor: colors.background }}>
        {children}
      </Animated.View>
    );
  }

  return (
    <Animated.View
      exiting={FadeOut.duration(120)}
      style={styles.root}
      accessibilityLabel="CrackNews">
      <Animated.View style={markStyle}>
        <Image
          source={require('../../../assets/images/splash-icon.png')}
          style={styles.mark}
          resizeMode="contain"
        />
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000000',
  },
  mark: {
    width: 68,
    height: 68,
  },
});
