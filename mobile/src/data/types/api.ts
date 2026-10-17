export type AudioStatus = 'pending' | 'ready' | 'failed' | 'unavailable' | 'none';

export interface StoryCard {
  storyId: string;
  title: string;
  summary: string;
  summaryPreview: string;
  imageUrl: string | null;
  imageAspect?: number;
  outlet: string;
  topic: string;
  place?: string;
  publishedAt: string;
  sourceUrl: string;
  audioStatus: AudioStatus;
  audioUrl?: string;
  audioDurationMs?: number;
  clusterId?: string | null;
  threadId?: string | null;
  /** Client hint for multi-outlet badge when known */
  clusterSize?: number;
}

export interface HomeFeedResponse {
  items: StoryCard[];
  nextCursor?: string | null;
  serverTime: string;
}

export interface SearchResponse {
  stories: StoryCard[];
  storylines: StorylineSummary[];
  serverTime: string;
}

export interface DisplayAd {
  adId: string;
  advertiser: string;
  title: string;
  clickUrl: string;
  imageUrl?: string | null;
  imageAspect?: number;
}

export interface DisplayAdsResponse {
  items: DisplayAd[];
}

export type WallItem =
  | { kind: 'story'; story: StoryCard }
  | { kind: 'ad'; ad: DisplayAd };

export interface StoryDetailResponse {
  story: StoryCard;
  compareClusterId?: string | null;
  threadId?: string | null;
}

export interface AudioUrlResponse {
  audioUrl: string;
  expiresAt: string;
}

export interface CoverageOutlet {
  storyId: string;
  outlet: string;
  framing: string;
  summary: string;
  imageUrl?: string | null;
  audioStatus: AudioStatus;
  audioUrl?: string;
  sourceUrl?: string;
  publishedAt?: string;
}

export interface CoverageResponse {
  clusterId: string;
  title: string;
  outlets: CoverageOutlet[];
}

export type StorylineStatus = 'open' | 'closed';

export interface StorylineSummary {
  threadId: string;
  title: string;
  status: StorylineStatus;
  updatedAt: string;
  updateCount: number;
  topic?: string;
  place?: string;
  coverImageUrl?: string | null;
  latestOutlet?: string | null;
  latestStoryId?: string | null;
}

export interface StorylineUpdate {
  storyId: string;
  /** API field */
  at?: string;
  /** Alias used by older mock seed */
  publishedAt?: string;
  outlet: string;
  summary?: string;
  brief?: string;
  title?: string;
  audioStatus: AudioStatus;
  audioUrl?: string;
  imageUrl?: string | null;
  sourceUrl?: string;
}

export interface StorylineDetail {
  threadId: string;
  title: string;
  status: StorylineStatus;
  topic?: string;
  place?: string;
  updatedAt?: string;
  updates: StorylineUpdate[];
}

export interface TopicMeta {
  id: string;
  label: string;
}

export interface TopicsMetaResponse {
  topics: TopicMeta[];
}

export interface UserProfile {
  userId: string;
  email: string;
  displayName: string;
  avatarUrl?: string;
  topics: string[];
}

export interface GoogleAuthResponse {
  accessToken: string;
  expiresAt: string;
  user: UserProfile;
}

export interface ApiErrorBody {
  error?: { code?: string; message?: string };
}
