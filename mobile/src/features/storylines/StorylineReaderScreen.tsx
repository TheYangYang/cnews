import { useFocusEffect, useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { WebView } from 'react-native-webview';

import { fetchStorylineDetail } from '@/data/api/endpoints';
import { getApiBaseUrl } from '@/data/api/config';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { updatesToCards } from '@/features/storylines/storylineUtils';
import { useAuthStore } from '@/data/stores/authStore';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import { usePlaySurfaceStore } from '@/data/stores/playSurfaceStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';
import { formatTimelineStamp } from '@/shared/utils/time';
import type { StorylineUpdate } from '@/data/types/api';

type Props = { threadId: string };

const NODE = 36;

function coverOf(update: StorylineUpdate): string | null {
  if (update.imageUrl) return rewriteMediaUrl(update.imageUrl) ?? update.imageUrl;
  if (update.storyId) {
    return `${getApiBaseUrl().replace(/\/$/, '')}/media/covers/${update.storyId}.jpg`;
  }
  return null;
}

function hostOf(url?: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

/**
 * In-tab storyline: timeline of outlet summaries (+ original in-app).
 * Audio is controlled only by the Play tab — opening this screen never starts playback.
 */
export function StorylineReaderScreen({ threadId }: Props) {
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const token = useAuthStore((s) => s.accessToken);
  const speakingId = useFeedUiStore((s) => s.speakingStoryId);
  const setSurface = usePlaySurfaceStore((s) => s.setSurface);
  const setStorylineQueue = usePlaySurfaceStore((s) => s.setStorylineQueue);
  const [webUrl, setWebUrl] = useState<string | null>(null);
  const [webLabel, setWebLabel] = useState('');
  /** Resume Play after closing Original (same as home reader). */
  const resumeAfterWeb = useRef(false);

  const query = useQuery({
    queryKey: ['storyline', threadId],
    queryFn: () => fetchStorylineDetail(threadId, token),
  });

  useFocusEffect(
    useCallback(() => {
      setSurface('storylines');
      return () => {
        void usePlayerStore.getState().stop();
      };
    }, [setSurface]),
  );

  useEffect(() => {
    if (!query.data) return;
    const cards = updatesToCards(query.data);
    const map: Record<string, string> = {};
    for (const u of query.data.updates) map[u.storyId] = query.data.threadId;
    setStorylineQueue(cards, { storyIdToThreadId: map });
  }, [query.data, setStorylineQueue]);

  const openOriginal = useCallback((url: string, label: string) => {
    const playing = usePlayerStore.getState().isPlaying;
    resumeAfterWeb.current = playing;
    if (playing) void usePlayerStore.getState().togglePause();
    setWebLabel(label);
    setWebUrl(url);
  }, []);

  const closeOriginal = useCallback(() => {
    setWebUrl(null);
    if (!resumeAfterWeb.current) return;
    resumeAfterWeb.current = false;
    const state = usePlayerStore.getState();
    if (!state.isPlaying && state.queue.length > 0) {
      void state.togglePause();
    }
  }, []);

  const goBack = useCallback(() => {
    if (webUrl) {
      closeOriginal();
      return;
    }
    if (router.canGoBack()) router.back();
    else router.replace('/(tabs)/storylines');
  }, [router, webUrl, closeOriginal]);

  const detail = query.data;
  const hero = detail?.updates.length
    ? coverOf(detail.updates[detail.updates.length - 1]!)
    : null;

  if (query.isLoading) {
    return (
      <View style={[styles.loading, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (!detail) {
    return (
      <View style={[styles.loading, { backgroundColor: colors.background }]}>
        <Text style={{ color: colors.textMuted }}>Storyline unavailable</Text>
        <Pressable onPress={goBack}>
          <Text style={{ color: colors.accent, fontWeight: '600' }}>Back</Text>
        </Pressable>
      </View>
    );
  }

  if (webUrl) {
    return (
      <Animated.View
        entering={FadeIn.duration(motion.duration.fast)}
        style={[styles.root, { backgroundColor: colors.readerBg, paddingTop: insets.top }]}>
        <View style={[styles.webBar, { borderBottomColor: colors.border }]}>
          <Pressable onPress={closeOriginal} style={styles.webBack} hitSlop={10}>
            <Ionicons name="chevron-back" size={22} color="#fff" />
            <Text style={styles.webBackText}>Timeline</Text>
          </Pressable>
          <Text style={styles.webHost} numberOfLines={1}>
            {webLabel || 'Original'}
          </Text>
          <View style={{ width: 88 }} />
        </View>
        <WebView
          source={{ uri: webUrl }}
          style={{ flex: 1 }}
          startInLoadingState
          renderLoading={() => (
            <View style={[styles.loading, { backgroundColor: colors.readerBg }]}>
              <ActivityIndicator color={colors.accentBright} />
            </View>
          )}
        />
      </Animated.View>
    );
  }

  const ongoing = detail.status === 'open';

  return (
    <Animated.View
      entering={FadeIn.duration(motion.duration.base)}
      style={[styles.root, { backgroundColor: colors.background }]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: 110 }}>
        <View style={{ height: Math.min(width * 0.62, 280) }}>
          {hero ? (
            <Image source={{ uri: hero }} style={StyleSheet.absoluteFill} />
          ) : (
            <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.ink }]} />
          )}
          <LinearGradient
            colors={['rgba(0,0,0,0.35)', 'transparent', colors.background]}
            locations={[0, 0.45, 1]}
            style={StyleSheet.absoluteFill}
          />
          <View style={[styles.heroTop, { paddingTop: insets.top + 8 }]}>
            <Pressable
              onPress={goBack}
              style={[styles.backBtn, { backgroundColor: 'rgba(0,0,0,0.45)' }]}
              accessibilityLabel="Back to storylines">
              <Ionicons name="chevron-back" size={22} color="#fff" />
            </Pressable>
          </View>
          <View style={styles.heroCopy}>
            <View
              style={[
                styles.status,
                { backgroundColor: ongoing ? colors.accentBright : 'rgba(255,255,255,0.22)' },
              ]}>
              <Text style={{ color: ongoing ? colors.onAccent : '#fff', fontWeight: '800', fontSize: 11 }}>
                {ongoing ? 'Ongoing' : 'Closed'}
              </Text>
            </View>
            <Text style={styles.heroTitle}>{detail.title}</Text>
            <Text style={styles.heroMeta}>
              {[detail.place ?? detail.topic, `${detail.updates.length} outlets`]
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </View>
        </View>

        <View style={styles.sectionPad}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
            Outlet timeline
          </Text>
          <Text style={[styles.sectionHint, { color: colors.textSecondary }]}>
            Each outlet’s brief as the story evolved. Use Play to hear them in order.
          </Text>

          {/* Spine through node centers: stem under card + bridge through the gap */}
          <View style={styles.track}>
            {detail.updates.map((update, i) => {
              const when = update.at ?? update.publishedAt ?? '';
              const stamp = when ? formatTimelineStamp(when) : 'Update';
              const summary = update.summary ?? update.brief ?? '';
              const listening = speakingId === update.storyId;
              const cover = coverOf(update);
              const host = hostOf(update.sourceUrl);
              const isLast = i === detail.updates.length - 1;
              const stepIcons = ['file-tray-full', 'mail', 'bulb'] as const;
              const iconName = listening ? 'volume-high' : stepIcons[i % stepIcons.length]!;

              return (
                <View key={`${update.storyId}-${i}`}>
                  <Animated.View
                    entering={FadeInDown.delay(Math.min(i, 8) * 45).duration(motion.duration.base)}
                    style={styles.item}>
                    <View style={styles.row}>
                      <View style={styles.nodeCol}>
                        <View
                          style={[
                            styles.node,
                            {
                              backgroundColor: listening ? colors.accentBright : colors.accent,
                            },
                          ]}>
                          <Ionicons name={iconName} size={15} color={colors.onAccent} />
                        </View>
                        {/* Line under this node beside the card */}
                        {!isLast ? (
                          <View
                            pointerEvents="none"
                            style={[styles.stem, { backgroundColor: colors.border }]}
                          />
                        ) : null}
                      </View>

                      <View style={styles.contentCol}>
                        <Text style={[styles.stamp, { color: colors.textMuted }]}>{stamp}</Text>
                        <Text style={[styles.header, { color: colors.text }]}>
                          {update.outlet}
                          {listening ? ' · Listening' : ''}
                        </Text>

                        <View
                          style={[
                            styles.card,
                            {
                              backgroundColor: colors.surface,
                              borderColor: listening ? colors.accentBright : colors.border,
                              borderWidth: listening ? 2 : StyleSheet.hairlineWidth,
                            },
                          ]}>
                          <View style={styles.cardHead}>
                            {cover ? (
                              <Image source={{ uri: cover }} style={styles.thumb} />
                            ) : (
                              <View style={[styles.thumb, { backgroundColor: colors.skeleton }]} />
                            )}
                            <View style={{ flex: 1 }}>
                              {update.title ? (
                                <Text
                                  style={[styles.updateTitle, { color: colors.text }]}
                                  numberOfLines={2}>
                                  {update.title}
                                </Text>
                              ) : (
                                <Text style={[styles.updateTitle, { color: colors.text }]}>
                                  {update.outlet} brief
                                </Text>
                              )}
                            </View>
                          </View>

                          <Text style={[styles.summary, { color: colors.textSecondary }]}>
                            {summary}
                          </Text>

                          {update.sourceUrl ? (
                            <Pressable
                              onPress={() =>
                                openOriginal(update.sourceUrl!, host || update.outlet)
                              }
                              style={[styles.originalBtn, { backgroundColor: colors.accentSoft }]}
                              accessibilityRole="button"
                              accessibilityLabel={`Read original from ${update.outlet}`}>
                              <Ionicons name="globe-outline" size={16} color={colors.accentDeep} />
                              <Text style={[styles.originalText, { color: colors.accentDeep }]}>
                                Original{host ? ` · ${host}` : ''}
                              </Text>
                              <Ionicons name="chevron-forward" size={14} color={colors.accentDeep} />
                            </Pressable>
                          ) : null}
                        </View>
                      </View>
                    </View>
                  </Animated.View>
                  {/* Bridge the gap so the line meets the next icon (no dead space) */}
                  {!isLast ? (
                    <View style={styles.gapBridge} pointerEvents="none">
                      <View style={[styles.gapLine, { backgroundColor: colors.border }]} />
                    </View>
                  ) : null}
                </View>
              );
            })}
          </View>
        </View>
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  heroTop: {
    paddingHorizontal: 12,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCopy: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 18,
    gap: 8,
  },
  status: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
  },
  heroTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: -0.5,
    lineHeight: 33,
  },
  heroMeta: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    color: 'rgba(255,255,255,0.72)',
    letterSpacing: 0.3,
  },
  sectionPad: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  sectionHint: {
    marginTop: 6,
    marginBottom: spacing.lg,
    fontSize: 14,
    lineHeight: 20,
  },
  track: {
    position: 'relative',
    paddingTop: 2,
  },
  item: {
    zIndex: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  nodeCol: {
    width: NODE,
    alignItems: 'center',
    alignSelf: 'stretch',
  },
  node: {
    width: NODE,
    height: NODE,
    borderRadius: NODE / 2,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
    elevation: 2,
  },
  stem: {
    flex: 1,
    width: 2,
    borderRadius: 1,
    minHeight: 4,
  },
  gapBridge: {
    width: NODE,
    height: 28,
    alignItems: 'center',
  },
  gapLine: {
    flex: 1,
    width: 2,
    borderRadius: 1,
  },
  contentCol: {
    flex: 1,
    paddingLeft: 14,
    paddingTop: 1,
  },
  stamp: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 18,
    marginBottom: 4,
  },
  header: {
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: -0.25,
    lineHeight: 22,
    marginBottom: 10,
  },
  card: {
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 14,
    gap: 8,
  },
  cardHead: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
  },
  thumb: {
    width: 44,
    height: 44,
    borderRadius: 10,
  },
  updateTitle: {
    fontSize: 15,
    fontWeight: '700',
    lineHeight: 20,
  },
  summary: {
    fontSize: 15,
    lineHeight: 22,
  },
  originalBtn: {
    marginTop: 4,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderRadius: 12,
  },
  originalText: {
    fontSize: 13,
    fontWeight: '700',
  },
  webBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 10,
    backgroundColor: '#0B1220',
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  webBack: { flexDirection: 'row', alignItems: 'center', width: 88, gap: 2 },
  webBackText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  webHost: {
    flex: 1,
    textAlign: 'center',
    fontSize: 13,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.65)',
  },
});
