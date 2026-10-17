import {
  createAudioPlaylist,
  setAudioModeAsync,
  type AudioPlaylist,
} from 'expo-audio';
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

let playlist: AudioPlaylist | null = null;
let subs: { remove: () => void }[] = [];
let advanceTimer: ReturnType<typeof setTimeout> | null = null;
let activeStoryId: string | null = null;
let audioModeReady = false;
let readerOnFinished: (() => void) | null = null;
let pausedByUser = false;

async function ensureBackgroundAudioMode() {
  if (audioModeReady) return;
  await setAudioModeAsync({
    playsInSilentMode: true,
    interruptionMode: 'doNotMix',
    shouldPlayInBackground: true,
  });
  audioModeReady = true;
}

function clearAdvanceTimer() {
  if (advanceTimer) {
    clearTimeout(advanceTimer);
    advanceTimer = null;
  }
}

function unloadPlaylist() {
  clearAdvanceTimer();
  for (const s of subs) {
    try {
      s.remove();
    } catch {
      /* ignore */
    }
  }
  subs = [];
  readerOnFinished = null;
  activeStoryId = null;
  pausedByUser = false;
  if (playlist) {
    try {
      playlist.pause();
    } catch {
      /* ignore */
    }
    try {
      playlist.destroy();
    } catch {
      /* ignore */
    }
    playlist = null;
  }
}

async function resolveAudioUrl(storyId: string, existing?: string): Promise<string | null> {
  if (existing) return rewriteMediaUrl(existing) ?? null;
  const token = useAuthStore.getState().accessToken;
  try {
    const res = await fetchStoryAudioUrl(storyId, token);
    return rewriteMediaUrl(res.audioUrl) ?? null;
  } catch {
    return null;
  }
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

async function withUrls(items: QueueItem[]): Promise<QueueItem[]> {
  const resolved = await Promise.all(
    items.map(async (item) => {
      const audioUrl = (await resolveAudioUrl(item.storyId, item.audioUrl)) ?? undefined;
      return { ...item, audioUrl };
    }),
  );
  return resolved.filter((item) => !!item.audioUrl);
}

function applyTrack(index: number, queue: QueueItem[], set: Set) {
  const item = queue[index];
  if (!item) return;
  activeStoryId = item.storyId;
  useFeedUiStore.getState().setSpeakingStoryId(item.storyId);
  set({ queueIndex: index, isPlaying: true });
  armAdvanceTimer(index, item.audioDurationMs);
}

function armAdvanceTimer(index: number, durationMs?: number) {
  clearAdvanceTimer();
  if (!durationMs || durationMs < 400) return;
  const elapsedMs = playlist ? Math.max(0, playlist.currentTime * 1000) : 0;
  const wait = Math.max(400, durationMs - elapsedMs + 400);
  advanceTimer = setTimeout(() => {
    if (pausedByUser || !playlist) return;
    if (playlist.currentIndex !== index) return;
    if (index >= playlist.trackCount - 1) {
      void usePlayerStore.getState().stop().then(() => readerOnFinished?.());
      return;
    }
    try {
      playlist.next();
    } catch {
      /* trackChanged listener updates the highlight */
    }
  }, wait);
}

type Get = () => PlayerState;
type Set = (
  partial: Partial<PlayerState> | ((state: PlayerState) => Partial<PlayerState>),
) => void;

async function playQueue(
  items: QueueItem[],
  context: Exclude<PlayerContext, null>,
  set: Set,
  get: Get,
) {
  unloadPlaylist();
  await ensureBackgroundAudioMode();

  const queue = await withUrls(items);
  if (!queue.length) {
    set({ toastMessage: 'No spoken briefs ready yet', isPlaying: false, queue: [], context: null });
    return;
  }

  playlist = createAudioPlaylist({
    sources: queue.map((item) => item.audioUrl as string),
    updateInterval: 400,
    loop: 'none',
  });

  set({ queue, queueIndex: 0, context, isPlaying: true });
  applyTrack(0, queue, set);

  subs.push(
    playlist.addListener('trackChanged', ({ currentIndex }) => {
      if (get().context !== context) return;
      applyTrack(currentIndex, get().queue, set);
    }),
  );
  subs.push(
    playlist.addListener('playlistStatusUpdate', (status) => {
      if (get().context !== context) return;
      if (typeof status.currentIndex === 'number' && status.currentIndex !== get().queueIndex) {
        applyTrack(status.currentIndex, get().queue, set);
      }
      if (status.didJustFinish) {
        clearAdvanceTimer();
        void get().stop().then(() => readerOnFinished?.());
      }
    }),
  );

  playlist.play();
}

export const usePlayerStore = create<PlayerState>((set, get) => ({
  isPlaying: false,
  queue: [],
  queueIndex: 0,
  context: null,
  toastMessage: null,

  clearToast: () => set({ toastMessage: null }),

  stop: async () => {
    unloadPlaylist();
    useFeedUiStore.getState().setSpeakingStoryId(null);
    set({ isPlaying: false, queue: [], queueIndex: 0, context: null });
  },

  togglePause: async () => {
    if (!playlist) {
      set({ isPlaying: false });
      return;
    }
    if (playlist.playing) {
      pausedByUser = true;
      clearAdvanceTimer();
      playlist.pause();
      set({ isPlaying: false });
    } else {
      pausedByUser = false;
      playlist.play();
      set({ isPlaying: true });
      const { queueIndex, queue } = get();
      armAdvanceTimer(queueIndex, queue[queueIndex]?.audioDurationMs);
    }
  },

  playReaderStory: async (story, opts) => {
    if (story.audioStatus !== 'ready') {
      set({ toastMessage: 'No spoken brief for this story yet' });
      return;
    }
    if (playlist && activeStoryId === story.storyId) {
      set({ context: 'reader' });
      readerOnFinished = opts?.onFinished ?? null;
      return;
    }
    readerOnFinished = opts?.onFinished ?? null;
    await playQueue(
      [
        {
          storyId: story.storyId,
          title: story.title,
          outlet: story.outlet,
          imageUrl: story.imageUrl,
          audioUrl: story.audioUrl,
          audioDurationMs: story.audioDurationMs,
          audioStatus: story.audioStatus,
        },
      ],
      'reader',
      set,
      get,
    );
  },

  startWallQueue: async (stories, orderedIds) => {
    readerOnFinished = null;
    await playQueue(toQueueItems(stories, orderedIds), 'wall', set, get);
  },

  startStorylineQueue: async (stories, orderedIds) => {
    readerOnFinished = null;
    await playQueue(toQueueItems(stories, orderedIds), 'storylines', set, get);
  },

  rebindWallQueueTail: (stories, orderedIds) => {
    const state = get();
    if (state.context !== 'wall' || !state.queue.length || !playlist) return;

    const speakingId =
      useFeedUiStore.getState().speakingStoryId ??
      state.queue[state.queueIndex]?.storyId ??
      activeStoryId;
    if (!speakingId) return;

    const current =
      state.queue.find((q) => q.storyId === speakingId) ?? state.queue[state.queueIndex];
    if (!current) return;

    const rest = toQueueItems(stories, orderedIds).filter((s) => s.storyId !== current.storyId);
    const next = [current, ...rest];
    set({ queue: next, queueIndex: 0 });

    const currentIndex = playlist.currentIndex;
    void (async () => {
      if (!playlist) return;
      while (playlist.trackCount > currentIndex + 1) {
        playlist.remove(playlist.trackCount - 1);
      }
      const ready = await withUrls(rest);
      for (const item of ready) {
        if (item.audioUrl) playlist.add({ uri: item.audioUrl });
      }
      set({
        queue: [current, ...ready],
        queueIndex: 0,
      });
    })();
  },
}));
