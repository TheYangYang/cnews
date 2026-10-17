import { apiRequest } from '@/data/api/client';
import {
  MOCK_COVERAGE,
  MOCK_FEED,
  MOCK_STORYLINE_DETAILS,
  MOCK_STORYLINES,
  MOCK_TOPICS,
  getMockStoryById,
} from '@/data/seed/mockData';
import type {
  CoverageResponse,
  DisplayAdsResponse,
  GoogleAuthResponse,
  HomeFeedResponse,
  StoryDetailResponse,
  StorylineDetail,
  StorylineSummary,
  StorylineStatus,
  TopicsMetaResponse,
  UserProfile,
  AudioUrlResponse,
} from '@/data/types/api';
import { ApiError } from '@/data/api/client';

function useMockFallback<T>(fn: () => Promise<T>, fallback: () => T): Promise<T> {
  return fn().catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 0) {
      return fallback();
    }
    throw err;
  });
}

export async function fetchHomeFeed(params: {
  topics?: string[];
  limit?: number;
  cursor?: string | null;
  newerThan?: string | null;
  token?: string | null;
  mode?: 'any' | 'listen';
}): Promise<HomeFeedResponse> {
  const qs = new URLSearchParams();
  if (params.topics?.length) qs.set('topics', params.topics.join(','));
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.cursor) qs.set('cursor', params.cursor);
  if (params.newerThan) qs.set('newerThan', params.newerThan);
  if (params.mode) qs.set('mode', params.mode);
  const query = qs.toString();
  return useMockFallback(
    () =>
      apiRequest<HomeFeedResponse>(`/v1/home/feed${query ? `?${query}` : ''}`, {
        token: params.token,
      }),
    () => MOCK_FEED,
  );
}

export async function fetchDisplayAds(params?: {
  slot?: string;
  limit?: number;
  token?: string | null;
}): Promise<DisplayAdsResponse> {
  const qs = new URLSearchParams();
  qs.set('slot', params?.slot ?? 'home_wall');
  if (params?.limit) qs.set('limit', String(params.limit));
  return useMockFallback(
    () =>
      apiRequest<DisplayAdsResponse>(`/v1/ads/display?${qs.toString()}`, {
        token: params?.token,
      }),
    () => ({ items: [] }),
  );
}

export async function fetchStory(
  storyId: string,
  token?: string | null,
): Promise<StoryDetailResponse> {
  return useMockFallback(
    () => apiRequest<StoryDetailResponse>(`/v1/stories/${storyId}`, { token }),
    () => {
      const story = getMockStoryById(storyId);
      if (!story) throw new ApiError(404, 'Story not found', 'not_found');
      return {
        story,
        compareClusterId: story.clusterId ?? null,
        threadId: story.threadId ?? null,
      };
    },
  );
}

export async function fetchStoryAudioUrl(
  storyId: string,
  token?: string | null,
): Promise<AudioUrlResponse> {
  return useMockFallback(
    () => apiRequest<AudioUrlResponse>(`/v1/stories/${storyId}/audio-url`, { token }),
    () => ({
      audioUrl: '',
      expiresAt: new Date(Date.now() + 3600_000).toISOString(),
    }),
  );
}

export async function fetchCoverage(
  clusterId: string,
  token?: string | null,
): Promise<CoverageResponse> {
  return useMockFallback(
    () => apiRequest<CoverageResponse>(`/v1/coverage/${clusterId}`, { token }),
    () => {
      const cluster = MOCK_COVERAGE[clusterId];
      if (!cluster) throw new ApiError(404, 'Coverage not found', 'not_found');
      return cluster;
    },
  );
}

export async function fetchStorylines(params: {
  status?: StorylineStatus | 'all';
  topics?: string[];
  limit?: number;
  cursor?: string | null;
  token?: string | null;
}): Promise<{ items: StorylineSummary[]; nextCursor?: string | null }> {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status === 'all' ? 'all' : params.status);
  if (params.topics?.length) qs.set('topics', params.topics.join(','));
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.cursor) qs.set('cursor', params.cursor);
  const query = qs.toString();
  return useMockFallback(
    () =>
      apiRequest<{ items: StorylineSummary[]; nextCursor?: string | null }>(
        `/v1/storylines${query ? `?${query}` : ''}`,
        { token: params.token },
      ),
    () => {
      let items = MOCK_STORYLINES;
      if (params.status && params.status !== 'all') {
        items = items.filter((s) => s.status === params.status);
      }
      const limit = params.limit ?? 10;
      let start = 0;
      if (params.cursor) {
        const idx = items.findIndex((s) => s.threadId === params.cursor);
        start = idx >= 0 ? idx + 1 : 0;
      }
      const page = items.slice(start, start + limit);
      const nextCursor =
        start + limit < items.length ? page[page.length - 1]?.threadId ?? null : null;
      return { items: page, nextCursor };
    },
  );
}

export async function fetchStorylineDetail(
  threadId: string,
  token?: string | null,
): Promise<StorylineDetail> {
  return useMockFallback(
    () => apiRequest<StorylineDetail>(`/v1/storylines/${threadId}`, { token }),
    () => {
      const detail = MOCK_STORYLINE_DETAILS[threadId];
      if (!detail) throw new ApiError(404, 'Storyline not found', 'not_found');
      return detail;
    },
  );
}

export async function fetchTopicsMeta(token?: string | null): Promise<TopicsMetaResponse> {
  return useMockFallback(
    () => apiRequest<TopicsMetaResponse>('/v1/meta/topics', { token }),
    () => MOCK_TOPICS,
  );
}

export async function postGoogleAuth(idToken: string): Promise<GoogleAuthResponse> {
  try {
    return await apiRequest<GoogleAuthResponse>('/v1/auth/google', {
      method: 'POST',
      body: { idToken },
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 0) {
      return {
        accessToken: 'mock-jwt',
        expiresAt: new Date(Date.now() + 86400_000).toISOString(),
        user: {
          userId: 'mock-user',
          email: 'demo@cnews.ca',
          displayName: 'Demo User',
          avatarUrl: undefined,
          topics: ['Top', 'Canada', 'Local'],
        },
      };
    }
    throw err;
  }
}

export async function putUserTopics(
  topics: string[],
  token: string,
): Promise<UserProfile> {
  try {
    return await apiRequest<UserProfile>('/v1/me/topics', {
      method: 'PUT',
      body: { topics },
      token,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 0) {
      return {
        userId: 'mock-user',
        email: 'demo@cnews.ca',
        displayName: 'Demo User',
        topics,
      };
    }
    throw err;
  }
}
