import { create } from 'zustand';

import type { WallItem } from '@/data/types/api';

type FeedUiState = {
  /** On-screen *story* cards in left→right, top→bottom order (Play queue). */
  visibleStoryIds: string[];
  /** Full masonry wall stories in left→right, top→bottom order (Play fallback). */
  wallReadingOrderIds: string[];
  speakingStoryId: string | null;
  readerPageIndex: number;
  setVisibleStoryIds: (ids: string[]) => void;
  setWallReadingOrderIds: (ids: string[]) => void;
  setSpeakingStoryId: (id: string | null) => void;
  setReaderPageIndex: (index: number) => void;
};

export const useFeedUiStore = create<FeedUiState>((set) => ({
  visibleStoryIds: [],
  wallReadingOrderIds: [],
  speakingStoryId: null,
  readerPageIndex: 0,
  setVisibleStoryIds: (ids) => set({ visibleStoryIds: ids }),
  setWallReadingOrderIds: (ids) => set({ wallReadingOrderIds: ids }),
  setSpeakingStoryId: (id) => set({ speakingStoryId: id }),
  setReaderPageIndex: (index) => set({ readerPageIndex: index }),
}));

function playId(item: WallItem | undefined): string | null {
  return item?.kind === 'story' ? item.story.storyId : null;
}

/**
 * Home Play order: left → right, top → bottom. Display ads are skipped.
 */
export function visiblePlayOrder(
  left: WallItem[],
  right: WallItem[],
  scrollY: number,
  viewportHeight: number,
  leftOffsets: number[],
  rightOffsets: number[],
): string[] {
  const endY = scrollY + viewportHeight;
  type Entry = { id: string; y: number };
  const readingOrder: Entry[] = [];
  const rows = Math.max(left.length, right.length);

  for (let i = 0; i < rows; i++) {
    const l = playId(left[i]);
    const r = playId(right[i]);
    if (l) readingOrder.push({ id: l, y: leftOffsets[i] ?? i * 180 });
    if (r) readingOrder.push({ id: r, y: rightOffsets[i] ?? i * 180 });
  }

  const visible = readingOrder
    .filter((e) => e.y + 80 >= scrollY && e.y < endY)
    .map((e) => e.id);

  if (visible.length) return visible;

  return readingOrder.slice(0, 6).map((e) => e.id);
}

/** Full wall stories in left→right, top→bottom order (for Play fallback). */
export function masonryReadingOrder(left: WallItem[], right: WallItem[]): string[] {
  const ids: string[] = [];
  const rows = Math.max(left.length, right.length);
  for (let i = 0; i < rows; i++) {
    const l = playId(left[i]);
    const r = playId(right[i]);
    if (l) ids.push(l);
    if (r) ids.push(r);
  }
  return ids;
}
