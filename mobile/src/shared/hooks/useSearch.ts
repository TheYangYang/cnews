import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchSearch } from '@/data/api/endpoints';
import { readCachedFeed, upsertFeedStories } from '@/data/db/feedRepository';
import { useAuthStore } from '@/data/stores/authStore';
import type { StoryCard, StorylineSummary } from '@/data/types/api';
import { matchesSearchQuery } from '@/shared/utils/searchMatch';

function filterCached(stories: StoryCard[], q: string): StoryCard[] {
  return stories.filter((s) =>
    matchesSearchQuery([s.title, s.summary, s.outlet, s.topic, s.place], q),
  );
}

export function useSearch() {
  const token = useAuthStore((s) => s.accessToken);
  const [query, setQuery] = useState('');
  const [stories, setStories] = useState<StoryCard[]>([]);
  const [storylines, setStorylines] = useState<StorylineSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  const run = useCallback(
    async (raw: string) => {
      const q = raw.trim();
      const ticket = ++seq.current;
      if (q.length < 2) {
        setStories([]);
        setStorylines([]);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);
      const cached = filterCached(await readCachedFeed(80), q);
      if (ticket !== seq.current) return;
      if (cached.length) setStories(cached);

      try {
        const res = await fetchSearch({ q, limit: 20, token, mode: 'listen' });
        if (ticket !== seq.current) return;
        const byId = new Map<string, StoryCard>();
        for (const s of res.stories) byId.set(s.storyId, s);
        for (const s of cached) {
          if (!byId.has(s.storyId)) byId.set(s.storyId, s);
        }
        const merged = [...byId.values()];
        setStories(merged);
        setStorylines(res.storylines);
        if (res.stories.length) void upsertFeedStories(res.stories);
      } catch {
        if (ticket !== seq.current) return;
        setStorylines([]);
        if (!cached.length) {
          setError('Search is unavailable right now.');
        }
      } finally {
        if (ticket === seq.current) setLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    const t = setTimeout(() => {
      void run(query);
    }, 280);
    return () => clearTimeout(t);
  }, [query, run]);

  return { query, setQuery, stories, storylines, loading, error };
}
