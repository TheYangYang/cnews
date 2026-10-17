import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  FadeInDown,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';

import type { CoverageOutlet, StoryCard } from '@/data/types/api';
import { getApiBaseUrl } from '@/data/api/config';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { formatRelativeTime } from '@/shared/utils/time';

type Props = {
  story?: StoryCard;
  outlet?: CoverageOutlet;
  /** Full-screen page height (above tab bar) for layout. */
  viewportHeight?: number;
  /** Notify parent when in-app original WebView is open (locks vertical pager). */
  onOriginalOpenChange?: (open: boolean) => void;
};

const CTA_ABOVE_TAB = 48;

function coverUri(storyId: string, imageUrl?: string | null): string {
  if (imageUrl) return rewriteMediaUrl(imageUrl) ?? imageUrl;
  return `${getApiBaseUrl().replace(/\/$/, '')}/media/covers/${storyId}.jpg`;
}

function hostLabel(url?: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

export function ReaderPage({ story, outlet, viewportHeight, onOriginalOpenChange }: Props) {
  const { colors, isDark } = useTheme();
  const { height: windowH } = useWindowDimensions();
  const height = viewportHeight && viewportHeight > 0 ? viewportHeight : windowH;
  const [showWeb, setShowWeb] = useState(false);
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const isPlaying = usePlayerStore((s) => s.isPlaying);
  const togglePause = usePlayerStore((s) => s.togglePause);
  const heroScale = useSharedValue(1.06);
  const resumeAfterWeb = useRef(false);

  const storyId = story?.storyId ?? outlet?.storyId ?? 'unknown';
  const title = story?.title ?? outlet?.framing ?? '';
  const summary = story?.summary ?? outlet?.summary ?? '';
  const imageUrl = coverUri(storyId, story?.imageUrl ?? outlet?.imageUrl);
  const outletName = story?.outlet ?? outlet?.outlet ?? '';
  const sourceUrl = story?.sourceUrl ?? outlet?.sourceUrl;
  const topic = story?.topic;
  const place = story?.place;
  const publishedAt = story?.publishedAt ?? outlet?.publishedAt;
  const listening = speakingId === storyId && isPlaying;
  const host = hostLabel(sourceUrl);
  const heroH = Math.max(height * 0.52, 340);

  useEffect(() => {
    heroScale.value = 1.06;
    heroScale.value = withTiming(1, {
      duration: 1400,
      easing: Easing.out(Easing.cubic),
    });
  }, [storyId, heroScale]);

  const heroAnim = useAnimatedStyle(() => ({
    transform: [{ scale: heroScale.value }],
  }));

  const openOriginal = () => {
    if (!sourceUrl) return;
    const playing = usePlayerStore.getState().isPlaying;
    resumeAfterWeb.current = playing;
    if (playing) void togglePause();
    setShowWeb(true);
    onOriginalOpenChange?.(true);
  };

  const closeOriginal = () => {
    setShowWeb(false);
    onOriginalOpenChange?.(false);
    if (resumeAfterWeb.current) {
      resumeAfterWeb.current = false;
      const state = usePlayerStore.getState();
      if (!state.isPlaying && state.queue.length > 0) {
        void togglePause();
      }
    }
  };

  useEffect(() => {
    return () => {
      if (showWeb) onOriginalOpenChange?.(false);
    };
  }, [showWeb, onOriginalOpenChange]);

  if (showWeb && sourceUrl) {
    return (
      <Animated.View
        entering={FadeIn.duration(motion.duration.base)}
        style={[styles.webWrap, { backgroundColor: colors.readerBg }]}>
        <View style={[styles.webBar, { borderBottomColor: colors.border }]}>
          <Pressable onPress={closeOriginal} style={styles.webBack} hitSlop={10}>
            <Ionicons name="chevron-back" size={22} color="#fff" />
            <Text style={styles.webBackText}>Brief</Text>
          </Pressable>
          <Text style={styles.webHost} numberOfLines={1}>
            {host || outletName || 'Original'}
          </Text>
          <View style={{ width: 72 }} />
        </View>
        <WebView
          source={{ uri: sourceUrl }}
          style={styles.web}
          startInLoadingState
          renderLoading={() => (
            <View style={[styles.webLoading, { backgroundColor: colors.readerBg }]}>
              <ActivityIndicator color={colors.accentBright} />
            </View>
          )}
        />
      </Animated.View>
    );
  }

  const metaBits = [outletName, place, publishedAt ? formatRelativeTime(publishedAt) : null]
    .filter(Boolean)
    .join('  ·  ');

  const sheetFade = isDark
    ? (['transparent', 'rgba(8,12,20,0.55)', colors.readerBg] as const)
    : (['transparent', 'rgba(8,12,20,0.45)', colors.readerSheetTop] as const);

  return (
    <Animated.View
      entering={FadeIn.duration(motion.duration.base)}
      style={[styles.root, { backgroundColor: colors.readerBg }]}>
      <View style={[styles.heroShell, { height: heroH, backgroundColor: colors.readerBg }]}>
        <Animated.View style={[StyleSheet.absoluteFill, heroAnim]}>
          <Image source={{ uri: imageUrl }} style={StyleSheet.absoluteFill} contentFit="cover" />
        </Animated.View>
        <LinearGradient
          colors={['rgba(8,12,20,0.35)', 'transparent', sheetFade[1], sheetFade[2]]}
          locations={[0, 0.28, 0.72, 1]}
          style={StyleSheet.absoluteFill}
        />
        {listening ? (
          <View
            style={[
              styles.listeningBadge,
              {
                backgroundColor: isDark ? 'rgba(12,14,10,0.72)' : 'rgba(20,24,31,0.78)',
                borderColor: 'rgba(240,180,41,0.45)',
              },
            ]}
            pointerEvents="none">
            <View style={[styles.listeningDot, { backgroundColor: colors.accentBright }]} />
            <Text style={styles.listeningText}>Playing brief</Text>
          </View>
        ) : null}
        <Animated.View
          entering={FadeIn.duration(motion.duration.slow)}
          style={styles.heroCopy}>
          {topic ? <Text style={styles.kicker}>{topic}</Text> : null}
          <Text style={styles.title}>{title}</Text>
          {metaBits ? <Text style={styles.meta}>{metaBits}</Text> : null}
        </Animated.View>
      </View>

      <View style={styles.sheet}>
        <LinearGradient
          colors={[colors.readerSheetTop, colors.readerSheetMid, colors.readerSheetBottom]}
          style={StyleSheet.absoluteFill}
        />
        <View
          style={[
            styles.sheetAccent,
            { backgroundColor: isDark ? 'rgba(255,255,255,0.18)' : 'rgba(20,24,31,0.18)' },
          ]}
        />
        <Animated.View
          entering={FadeInDown.delay(100).duration(motion.duration.base)}
          style={styles.sheetInner}>
          <Text style={[styles.briefLabel, { color: colors.readerMuted }]}>Brief</Text>
          <Text style={[styles.summary, { color: colors.readerText }]}>{summary}</Text>
        </Animated.View>

        {sourceUrl ? (
          <Animated.View
            entering={FadeInDown.delay(180).duration(motion.duration.base)}
            style={[styles.ctaWrap, { paddingBottom: CTA_ABOVE_TAB }]}>
            <Pressable
              onPress={openOriginal}
              style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
              accessibilityRole="button"
              accessibilityLabel="Open original article in app">
              <LinearGradient
                colors={[colors.accentBright, colors.accent, colors.accentDeep]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.ctaGrad}>
                <View style={styles.ctaIcon}>
                  <Ionicons name="newspaper-outline" size={18} color={colors.onAccent} />
                </View>
                <View style={styles.ctaCopy}>
                  <Text style={[styles.ctaTitle, { color: colors.onAccent }]}>Read original</Text>
                  <Text style={[styles.ctaSub, { color: 'rgba(26,20,8,0.72)' }]} numberOfLines={1}>
                    {host ? `Open ${host} in app` : 'Open full article in app'}
                  </Text>
                </View>
                <Ionicons name="arrow-forward" size={18} color="rgba(26,20,8,0.85)" />
              </LinearGradient>
            </Pressable>
          </Animated.View>
        ) : null}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  heroShell: {
    width: '100%',
    overflow: 'hidden',
  },
  heroCopy: {
    flex: 1,
    justifyContent: 'flex-end',
    paddingHorizontal: 20,
    paddingBottom: 22,
    gap: 8,
  },
  kicker: {
    alignSelf: 'flex-start',
    fontFamily: 'SpaceMono',
    fontSize: 11,
    letterSpacing: 1.4,
    textTransform: 'uppercase',
    color: 'rgba(255,255,255,0.72)',
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: '#fff',
    lineHeight: 34,
    letterSpacing: -0.6,
  },
  meta: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    color: 'rgba(255,255,255,0.62)',
    letterSpacing: 0.2,
  },
  listeningBadge: {
    position: 'absolute',
    left: 16,
    top: 58,
    zIndex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
  },
  listeningDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  listeningText: {
    fontSize: 11,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.92)',
  },
  sheet: {
    flex: 1,
    paddingTop: 4,
  },
  sheetAccent: {
    alignSelf: 'center',
    width: 42,
    height: 4,
    borderRadius: 2,
    marginBottom: 14,
  },
  sheetInner: {
    flex: 1,
    paddingHorizontal: 20,
  },
  briefLabel: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    letterSpacing: 1.6,
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  summary: {
    fontSize: 18,
    lineHeight: 28,
    letterSpacing: -0.15,
  },
  ctaWrap: {
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  cta: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  ctaPressed: { opacity: 0.92, transform: [{ scale: 0.985 }] },
  ctaGrad: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  ctaIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(26,20,8,0.14)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaCopy: { flex: 1, gap: 2 },
  ctaTitle: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.2,
  },
  ctaSub: {
    fontSize: 12,
    fontWeight: '600',
  },
  webWrap: { flex: 1 },
  webBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 10,
    backgroundColor: '#0B1220',
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  webBack: { flexDirection: 'row', alignItems: 'center', width: 72, gap: 2 },
  webBackText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  webHost: {
    flex: 1,
    textAlign: 'center',
    fontSize: 13,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.65)',
  },
  web: { flex: 1 },
  webLoading: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
