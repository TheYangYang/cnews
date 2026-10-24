import { createAudioPlayer, setAudioModeAsync, type AudioPlayer, type AudioStatus } from 'expo-audio';
import { create } from 'zustand';

import { fetchStoryAudioUrl } from '@/data/api/endpoints';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useAuthStore } from '@/data/stores/authStore';
import { useFeedUiStore } from '@/data/stores/feedUiStore';
import type { StoryCard } from '@/data/types/api';

type QueueItem = {
  storyId: string;
  title: string;
  outlet?: string;
  imageUrl?: string | null;
  audioUrl?: string;
  audioDurationMs?: number;
  audioStatus: StoryCard['audioStatus'];
};

type PlayerContext = 'wall' | 'storylines' | 'reader' | null;

type PlayerState = {
  isPlaying: boolean;
  queue: QueueItem[];
  queueIndex: number;
  context: PlayerContext;
  toastMessage: string | null;
  startWallQueue: (stories: StoryCard[], orderedIds: string[]) => Promise<void>;
  startStorylineQueue: (stories: StoryCard[], orderedIds: string[]) => Promise<void>;
  playReaderStory: (story: StoryCard, opts?: { onFinished?: () => void }) => Promise<void>;
  rebindWallQueueTail: (stories: StoryCard[], orderedIds: string[]) => void;
  togglePause: () => Promise<void>;
  stop: () => Promise<void>;
  clearToast: () => void;
};

/**
 * One AudioPlayer, reused for every brief; the queue lives in JS.
 * (AudioPlaylist has no lock-screen API, and without lock-screen controls Android
 * stops background audio after ~3 minutes.)
 */
let player: AudioPlayer | null = null;
let lockScreenActive = false;
let audioModeReady = false;
/** Bumped by every start/stop so late async work (URL fetches) can tell it is stale. */
let session = 0;
/** Bumped per track so a finish event and the fallback timer can't both advance. */
let track = 0;
let playedThisSession = false;
let pausedByUser = false;
let retriedFreshUrl = false;
let advanceTimer: ReturnType<typeof setTimeout> | null = null;
let loadWatchdog: ReturnType<typeof setTimeout> | null = null;
let readerOnFinished: (() => void) | null = null;

let trackStartedAt = 0;

const LOAD_TIMEOUT_MS = 10_000;
const TRACK_SETTLE_MS = 1_000;
/** Signed audio URLs live ~15 min on the API; refetch well before that. */
const URL_MAX_AGE_MS = 10 * 60_000;
const resolvedAt = new Map<string, number>();

async function ensureBackgroundAudioMode() {
  if (audioModeReady) return;
  await setAudioModeAsync({
    playsInSilentMode: true,
    interruptionMode: 'doNotMix',
    shouldPlayInBackground: true,
  });
  audioModeReady = true;
}

function clearTimers() {
  if (advanceTimer) clearTimeout(advanceTimer);
  if (loadWatchdog) clearTimeout(loadWatchdog);
  advanceTimer = null;
  loadWatchdog = null;
}

function getPlayer(): AudioPlayer {
  if (!player) {
    player = createAudioPlayer(null, { updateInterval: 400 });
    player.addListener('playbackStatusUpdate', onStatus);
  }
  return player;
}

async function fetchFreshUrl(storyId: string): Promise<string | null> {
  const token = useAuthStore.getState().accessToken;
  try {
    const res = await fetchStoryAudioUrl(storyId, token);
    const url = rewriteMediaUrl(res.audioUrl) ?? null;
    if (url) resolvedAt.set(storyId, Date.now());
    return url;
  } catch {
    return null;
  }
}

async function resolveAudioUrl(item: QueueItem): Promise<string | null> {
  const fetchedAt = resolvedAt.get(item.storyId);
  const fresh = fetchedAt !== undefined && Date.now() - fetchedAt < URL_MAX_AGE_MS;
  // A URL that came with the card (no fetch time) is tried once; a load timeout refetches.
  if (item.audioUrl && (fresh || fetchedAt === undefined)) {
    return rewriteMediaUrl(item.audioUrl) ?? null;
  }
  return fetchFreshUrl(item.storyId);
}

function toQueueItems(stories: StoryCard[], orderedIds: string[]): QueueItem[] {
  const byId = new Map(stories.map((s) => [s.storyId, s]));
  const seen = new Set<string>();
  const queue: QueueItem[] = [];
  const pushReady = (s: StoryCard) => {
    if (seen.has(s.storyId) || s.audioStatus !== 'ready') return;
    seen.add(s.storyId);
    queue.push({
      storyId: s.storyId,
      title: s.title,
      outlet: s.outlet,
      imageUrl: s.imageUrl,
      audioUrl: s.audioUrl,
      audioDurationMs: s.audioDurationMs,
      audioStatus: s.audioStatus,
    });
  };
  for (const id of orderedIds) {
    const s = byId.get(id);
    if (s) pushReady(s);
  }
  for (const s of stories) pushReady(s);
  return queue;
}

function showOnLockScreen(item: QueueItem) {
  const p = getPlayer();
  const metadata = {
    title: item.title,
    artist: item.outlet ?? 'CrackNews',
    albumTitle: 'CrackNews',
    artworkUrl: rewriteMediaUrl(item.imageUrl) ?? undefined,
  };
  try {
    if (lockScreenActive) {
      p.updateLockScreenMetadata(metadata);
    } else {
      p.setActiveForLockScreen(true, metadata, { showSeekForward: false, showSeekBackward: false });
      lockScreenActive = true;
    }
  } catch {
    /* lock screen is best-effort (e.g. Expo Go) */
  }
}

function armAdvanceTimer(durationMs?: number) {
  if (advanceTimer) clearTimeout(advanceTimer);
  advanceTimer = null;
  if (!durationMs || durationMs < 400) return;
  // Fallback in case a platform drops the finish event.
  const elapsedMs = player ? Math.max(0, player.currentTime * 1000) : 0;
  const wait = Math.max(400, durationMs - elapsedMs + 400);
  const t = track;
  advanceTimer = setTimeout(() => {
    if (pausedByUser || t !== track) return;
    void advance(t);
  }, wait);
}

function prefetchNext(index: number, s: number) {
  const next = usePlayerStore.getState().queue[index + 1];
  if (!next || resolvedAt.has(next.storyId) || next.audioUrl) return;
  void fetchFreshUrl(next.storyId).then((url) => {
    if (!url || s !== session) return;
    usePlayerStore.setState((state) => ({
      queue: state.queue.map((q) => (q.storyId === next.storyId ? { ...q, audioUrl: url } : q)),
    }));
  });
}

async function playIndex(index: number, s: number): Promise<void> {
  const state = usePlayerStore.getState();
  const item = state.queue[index];
  if (!item) {
    await finish(s);
    return;
  }
  const url = await resolveAudioUrl(item);
  if (s !== session) return;
  if (!url) {
    await playIndex(index + 1, s);
    return;
  }

  const t = ++track;
  retriedFreshUrl = false;
  clearTimers();
  pausedByUser = false;
  const p = getPlayer();
  trackStartedAt = Date.now();
  p.replace({ uri: url });
  p.play();
  playedThisSession = true;
  useFeedUiStore.getState().setSpeakingStoryId(item.storyId);
  usePlayerStore.setState({ queueIndex: index, isPlaying: true });
  showOnLockScreen(item);
  armAdvanceTimer(item.audioDurationMs);
  armLoadWatchdog(index, s, t, item);
  prefetchNext(index, s);
}

function armLoadWatchdog(index: number, s: number, t: number, item: QueueItem) {
  loadWatchdog = setTimeout(() => {
    if (s !== session || t !== track || player?.isLoaded) return;
    // A stale signed URL is the usual cause: refetch once, then skip the brief.
    if (!retriedFreshUrl) {
      retriedFreshUrl = true;
      void fetchFreshUrl(item.storyId).then((url) => {
        if (!url || s !== session || t !== track) {
          void advance(t);
          return;
        }
        getPlayer().replace({ uri: url });
        getPlayer().play();
        loadWatchdog = setTimeout(() => {
          if (s === session && t === track && !player?.isLoaded) void advance(t);
        }, LOAD_TIMEOUT_MS);
      });
      return;
    }
    void advance(t);
  }, LOAD_TIMEOUT_MS);
}

async function advance(t: number) {
  if (t !== track) return;
  track++; // claim this transition
  const { queueIndex } = usePlayerStore.getState();
  await playIndex(queueIndex + 1, session);
}

async function finish(s: number) {
  if (s !== session) return;
  const empty = !playedThisSession;
  const onFinished = readerOnFinished;
  await usePlayerStore.getState().stop();
  if (empty) {
    usePlayerStore.setState({ toastMessage: 'No spoken briefs ready yet' });
  } else {
    onFinished?.();
  }
}

function onStatus(status: AudioStatus) {
  // Events from the brief we just replaced can land after replace(); ignore them.
  if (Date.now() - trackStartedAt < TRACK_SETTLE_MS) return;
  if (status.didJustFinish) {
    void advance(track);
    return;
  }
  if (!status.isLoaded) return;
  if (loadWatchdog) {
    clearTimeout(loadWatchdog);
    loadWatchdog = null;
  }
  // Keep the Play button in sync with lock-screen / headset play-pause.
  const state = usePlayerStore.getState();
  if (state.queue.length && status.playing !== state.isPlaying && !status.isBuffering) {
    pausedByUser = !status.playing;
    usePlayerStore.setState({ isPlaying: status.playing });
    if (status.playing) armAdvanceTimer(state.queue[state.queueIndex]?.audioDurationMs);
    else if (advanceTimer) clearTimeout(advanceTimer);
  }
}

async function playQueue(items: QueueItem[], context: Exclude<PlayerContext, null>) {
  const s = ++session;
  clearTimers();
  playedThisSession = false;
  player?.pause();
  await ensureBackgroundAudioMode();
  if (s !== session) return;

  if (!items.length) {
    useFeedUiStore.getState().setSpeakingStoryId(null);
    usePlayerStore.setState({
      toastMessage: 'No spoken briefs ready yet',
      isPlaying: false,
      queue: [],
      queueIndex: 0,
      context: null,
    });
    return;
  }
  usePlayerStore.setState({ queue: items, queueIndex: 0, context, isPlaying: true });
  await playIndex(0, s);
}

export const usePlayerStore = create<PlayerState>((set, get) => ({
  isPlaying: false,
  queue: [],
  queueIndex: 0,
  context: null,
  toastMessage: null,

  clearToast: () => set({ toastMessage: null }),

  stop: async () => {
    session++;
    track++;
    clearTimers();
    readerOnFinished = null;
    pausedByUser = false;
    if (player) {
      try {
        player.pause();
        if (lockScreenActive) player.clearLockScreenControls();
      } catch {
        /* ignore */
      }
      lockScreenActive = false;
    }
    useFeedUiStore.getState().setSpeakingStoryId(null);
    set({ isPlaying: false, queue: [], queueIndex: 0, context: null });
  },

  togglePause: async () => {
    const { queue, queueIndex, isPlaying } = get();
    if (!player || !queue.length) {
      set({ isPlaying: false });
      return;
    }
    if (isPlaying) {
      pausedByUser = true;
      if (advanceTimer) clearTimeout(advanceTimer);
      player.pause();
      set({ isPlaying: false });
    } else {
      pausedByUser = false;
      player.play();
      set({ isPlaying: true });
      armAdvanceTimer(queue[queueIndex]?.audioDurationMs);
    }
  },

  playReaderStory: async (story, opts) => {
    if (story.audioStatus !== 'ready') {
      set({ toastMessage: 'No spoken brief for this story yet' });
      return;
    }
    const { queue, queueIndex } = get();
    if (queue[queueIndex]?.storyId === story.storyId && queue.length) {
      set({ context: 'reader' });
      readerOnFinished = opts?.onFinished ?? null;
      return;
    }
    readerOnFinished = opts?.onFinished ?? null;
    await playQueue(toQueueItems([story], [story.storyId]), 'reader');
  },

  startWallQueue: async (stories, orderedIds) => {
    readerOnFinished = null;
    await playQueue(toQueueItems(stories, orderedIds), 'wall');
  },

  startStorylineQueue: async (stories, orderedIds) => {
    readerOnFinished = null;
    await playQueue(toQueueItems(stories, orderedIds), 'storylines');
  },

  /** Pull-to-refresh while listening: keep the current brief, rebind what follows. */
  rebindWallQueueTail: (stories, orderedIds) => {
    const state = get();
    if (state.context !== 'wall' || !state.queue.length) return;
    const current = state.queue[state.queueIndex];
    if (!current) return;
    const rest = toQueueItems(stories, orderedIds).filter((s) => s.storyId !== current.storyId);
    set({ queue: [current, ...rest], queueIndex: 0 });
    prefetchNext(0, session);
  },
}));
