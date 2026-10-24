import { create } from 'zustand';

import { fetchDisplayAds, fetchHomeFeed } from '@/data/api/endpoints';
import { readCachedFeed, upsertFeedStories } from '@/data/db/feedRepository';
import type { DisplayAd, StoryCard, WallItem } from '@/data/types/api';
import { releaseNativeAds, takeNativeAd } from '@/features/ads/nativeAdPool';
import { mixDisplayAds, storiesToWall } from '@/features/home/mixDisplayAds';
import { shuffleCopy } from '@/shared/utils/shuffle';

const PAGE_SIZE = 10;
const MODE = 'listen' as const;

type LoadParams = { topics: string[]; token: string | null };

type FeedState = {
  /** Stories in wall order (shuffled after pull-to-refresh). Shared by Home, reader, and Play. */
  items: StoryCard[];
  wallItems: WallItem[];
  ads: DisplayAd[];
  cursor: string | null;
  /** Topics key of the page on screen; a different key triggers a fresh first page. */
  loadedKey: string | null;
  loading: boolean;
  refreshing: boolean;
  loadingMore: boolean;
  error: unknown;
  ensureLoaded: (params: LoadParams) => void;
  refreshRandom: (params: LoadParams) => Promise<StoryCard[]>;
  loadMore: (params: LoadParams) => Promise<void>;
};

const keyFor = (topics: string[]) => topics.join(',');

const claimNative = takeNativeAd('home');

/** A new first page replaces the wall: free the Google ads the old wall held. */
function mixWall(stories: StoryCard[], ads: DisplayAd[]): WallItem[] {
  const wall = mixDisplayAds(stories, ads, { takeNative: claimNative });
  releaseNativeAds(
    'home',
    wall.flatMap((item) => (item.kind === 'native' ? [item.slotId] : [])),
  );
  return wall;
}

// Bumped on every first-page load so a late loadMore can't append to a newer wall.
let generation = 0;
let inflightKey: string | null = null;
let cacheTried = false;

async function fetchFirstPage({ topics, token }: LoadParams) {
  const [res, adRes] = await Promise.all([
    fetchHomeFeed({ topics, limit: PAGE_SIZE, token, mode: MODE }),
    fetchDisplayAds({ slot: 'home_wall', limit: 6, token }).catch(() => ({ items: [] })),
  ]);
  return { res, ads: adRes.items };
}

export const useFeedStore = create<FeedState>((set, get) => {
  const paintFirstPage = (stories: StoryCard[], ads: DisplayAd[], cursor: string | null, key: string) =>
    set({
      items: stories,
      wallItems: mixWall(stories, ads),
      ads,
      cursor,
      loadedKey: key,
      error: null,
    });

  const paintCache = async (topics: string[]) => {
    if (cacheTried) return;
    cacheTried = true;
    const rows = await readCachedFeed();
    const wanted = new Set(topics);
    const matching = rows.filter((s) => wanted.has(s.topic));
    // Only paint while the network page has not landed yet.
    if (matching.length && !get().items.length) {
      set({ items: matching, wallItems: storiesToWall(matching) });
    }
  };

  return {
    items: [],
    wallItems: [],
    ads: [],
    cursor: null,
    loadedKey: null,
    loading: false,
    refreshing: false,
    loadingMore: false,
    error: null,

    ensureLoaded: (params) => {
      const key = keyFor(params.topics);
      if (get().loadedKey === key || inflightKey === key) return;
      inflightKey = key;
      const gen = ++generation;
      set({ loading: true });
      void paintCache(params.topics);
      void fetchFirstPage(params)
        .then(async ({ res, ads }) => {
          if (gen !== generation) return;
          paintFirstPage(res.items, ads, res.nextCursor ?? null, key);
          await upsertFeedStories(res.items);
        })
        .catch((error: unknown) => {
          if (gen === generation) set({ error });
        })
        .finally(() => {
          if (inflightKey === key) inflightKey = null;
          if (gen === generation) set({ loading: false });
        });
    },

    /** Pull-to-refresh: fresh first page, shuffled, pagination reset, ads re-roll. */
    refreshRandom: async (params) => {
      const key = keyFor(params.topics);
      const gen = ++generation;
      set({ refreshing: true });
      try {
        const { res, ads } = await fetchFirstPage(params);
        if (gen !== generation) return [];
        const next = shuffleCopy(res.items);
        paintFirstPage(next, ads, res.nextCursor ?? null, key);
        if (next.length) await upsertFeedStories(next);
        return next;
      } catch (error) {
        // Keep the current wall on a failed refresh.
        if (gen === generation) set({ error });
        return [];
      } finally {
        if (gen === generation) set({ refreshing: false });
      }
    },

    loadMore: async (params) => {
      const { cursor, loadingMore, ads } = get();
      if (!cursor || loadingMore) return;
      const gen = generation;
      set({ loadingMore: true });
      try {
        const res = await fetchHomeFeed({
          topics: params.topics,
          limit: PAGE_SIZE,
          cursor,
          token: params.token,
          mode: MODE,
        });
        if (gen !== generation) return;
        const seen = new Set(get().items.map((s) => s.storyId));
        const fresh = res.items.filter((s) => !seen.has(s.storyId));
        if (fresh.length) {
          set((state) => ({
            items: [...state.items, ...fresh],
            wallItems: [...state.wallItems, ...mixDisplayAds(fresh, ads, { takeNative: claimNative })],
          }));
          void upsertFeedStories(fresh);
        }
        set({ cursor: res.nextCursor ?? null });
      } catch {
        // Offline or server error: keep the cursor so the next scroll retries.
      } finally {
        set({ loadingMore: false });
      }
    },
  };
});
