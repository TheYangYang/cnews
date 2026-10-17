import { create } from 'zustand';

import type { StoryCard } from '@/data/types/api';

export type PlaySurface = 'home' | 'storylines' | 'reader';

type PlaySurfaceState = {
  surface: PlaySurface;
  storylineStories: StoryCard[];
  storylineOrderedIds: string[];
  /** Feed story ids from the open reader page onward (for Play in reader). */
  readerOrderedIds: string[];
  /** storyId → threadId for list highlighting while Play advances. */
  storyIdToThreadId: Record<string, string>;
  setSurface: (surface: PlaySurface) => void;
  setStorylineQueue: (
    stories: StoryCard[],
    opts?: { orderedIds?: string[]; storyIdToThreadId?: Record<string, string> },
  ) => void;
  setReaderQueue: (orderedIds: string[]) => void;
  clearStorylineQueue: () => void;
  clearReaderQueue: () => void;
};

export const usePlaySurfaceStore = create<PlaySurfaceState>((set) => ({
  surface: 'home',
  storylineStories: [],
  storylineOrderedIds: [],
  readerOrderedIds: [],
  storyIdToThreadId: {},
  setSurface: (surface) => set({ surface }),
  setStorylineQueue: (stories, opts) =>
    set({
      storylineStories: stories,
      storylineOrderedIds: opts?.orderedIds ?? stories.map((s) => s.storyId),
      storyIdToThreadId: opts?.storyIdToThreadId ?? {},
    }),
  setReaderQueue: (orderedIds) => set({ readerOrderedIds: orderedIds }),
  clearStorylineQueue: () =>
    set({ storylineStories: [], storylineOrderedIds: [], storyIdToThreadId: {} }),
  clearReaderQueue: () => set({ readerOrderedIds: [] }),
}));
