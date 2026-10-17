import type {
  CoverageResponse,
  HomeFeedResponse,
  StorylineDetail,
  StorylineSummary,
  TopicsMetaResponse,
} from '@/data/types/api';

const now = Date.now();
const hoursAgo = (h: number) => new Date(now - h * 3600_000).toISOString();

export const MOCK_TOPICS: TopicsMetaResponse = {
  topics: [
    { id: 'Top', label: 'Top stories' },
    { id: 'Canada', label: 'Canada' },
    { id: 'Local', label: 'Local' },
    { id: 'Politics', label: 'Politics' },
    { id: 'Business', label: 'Business' },
    { id: 'World', label: 'World' },
  ],
};

export const MOCK_FEED: HomeFeedResponse = {
  serverTime: new Date().toISOString(),
  nextCursor: null,
  items: [
    {
      storyId: 'mock-1',
      title: 'Ottawa unveils new housing framework for mid-size cities',
      summary:
        'Federal officials outlined incentives for rental builds outside the largest metros, with provinces asked to align zoning within eighteen months.',
      summaryPreview:
        'Federal officials outlined incentives for rental builds outside the largest metros…',
      imageUrl: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&q=80',
      imageAspect: 0.72,
      outlet: 'CBC',
      topic: 'Canada',
      place: 'Ottawa',
      publishedAt: hoursAgo(2),
      sourceUrl: 'https://www.cbc.ca',
      audioStatus: 'ready',
      audioUrl: '',
      audioDurationMs: 22000,
      clusterId: 'cluster-housing',
      clusterSize: 3,
    },
    {
      storyId: 'mock-2',
      title: 'Bank of Canada holds rate steady as inflation cools',
      summary:
        'Governor notes labour markets are rebalancing while mortgage renewals remain a focus for households through 2027.',
      summaryPreview:
        'Governor notes labour markets are rebalancing while mortgage renewals remain a focus…',
      imageUrl: null,
      outlet: 'Globe and Mail',
      topic: 'Business',
      publishedAt: hoursAgo(3),
      sourceUrl: 'https://www.theglobeandmail.com',
      audioStatus: 'ready',
      audioDurationMs: 18000,
    },
    {
      storyId: 'mock-3',
      title: 'Wildfire smoke prompts air-quality alerts across the Prairies',
      summary:
        'Health officials recommend limiting outdoor activity for sensitive groups as plumes drift east from Alberta.',
      summaryPreview:
        'Health officials recommend limiting outdoor activity for sensitive groups…',
      imageUrl: 'https://images.unsplash.com/photo-1611274440219-aba64e2e3141?w=600&q=80',
      imageAspect: 1.05,
      outlet: 'CTV',
      topic: 'Canada',
      place: 'Calgary',
      publishedAt: hoursAgo(5),
      sourceUrl: 'https://www.ctvnews.ca',
      audioStatus: 'pending',
      clusterId: 'cluster-fire',
      clusterSize: 2,
    },
    {
      storyId: 'mock-4',
      title: 'Toronto transit agency tests overnight maintenance windows',
      summary:
        'Riders will see shorter headways on two lines while crews accelerate signal upgrades through November.',
      summaryPreview:
        'Riders will see shorter headways on two lines while crews accelerate signal upgrades…',
      imageUrl: 'https://images.unsplash.com/photo-1515169067865-5387ec356f68?w=600&q=80',
      imageAspect: 0.85,
      outlet: 'Toronto Star',
      topic: 'Local',
      place: 'Toronto',
      publishedAt: hoursAgo(6),
      sourceUrl: 'https://www.thestar.com',
      audioStatus: 'ready',
      audioDurationMs: 16000,
    },
    {
      storyId: 'mock-5',
      title: 'Quebec tables bill to expand nurse practitioner roles',
      summary:
        'The proposal would let NPs admit patients in select rural hospitals, pending college approval.',
      summaryPreview:
        'The proposal would let NPs admit patients in select rural hospitals…',
      imageUrl: null,
      outlet: 'La Presse',
      topic: 'Politics',
      place: 'Quebec City',
      publishedAt: hoursAgo(8),
      sourceUrl: 'https://www.lapresse.ca',
      audioStatus: 'none',
    },
    {
      storyId: 'mock-6',
      title: 'Vancouver port strike talks resume with federal mediator',
      summary:
        'Both sides say they remain far apart on shift scheduling, but agreed to daily sessions this week.',
      summaryPreview:
        'Both sides say they remain far apart on shift scheduling, but agreed to daily sessions…',
      imageUrl: 'https://images.unsplash.com/photo-1578575437130-527eed3abbcd?w=600&q=80',
      imageAspect: 0.68,
      outlet: 'Global News',
      topic: 'Canada',
      place: 'Vancouver',
      publishedAt: hoursAgo(10),
      sourceUrl: 'https://globalnews.ca',
      audioStatus: 'ready',
      audioDurationMs: 21000,
      threadId: 'thread-port',
    },
    {
      storyId: 'mock-7',
      title: 'Arctic research station reports record summer ice loss',
      summary:
        'Scientists warn downstream weather patterns could shift faster than models projected five years ago.',
      summaryPreview:
        'Scientists warn downstream weather patterns could shift faster than models projected…',
      imageUrl: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&q=80',
      imageAspect: 0.9,
      outlet: 'CBC',
      topic: 'World',
      publishedAt: hoursAgo(12),
      sourceUrl: 'https://www.cbc.ca',
      audioStatus: 'ready',
      audioDurationMs: 24000,
    },
    {
      storyId: 'mock-8',
      title: 'Halifax startup raises seed round for tidal energy sensors',
      summary:
        'The company plans pilot deployments in the Bay of Fundy with utility partners next spring.',
      summaryPreview:
        'The company plans pilot deployments in the Bay of Fundy with utility partners…',
      imageUrl: null,
      outlet: 'AllNovaScotia',
      topic: 'Business',
      place: 'Halifax',
      publishedAt: hoursAgo(14),
      sourceUrl: 'https://www.allnovascotia.com',
      audioStatus: 'ready',
      audioDurationMs: 15000,
    },
  ],
};

export const MOCK_COVERAGE: Record<string, CoverageResponse> = {
  'cluster-housing': {
    clusterId: 'cluster-housing',
    title: 'Mid-size city housing framework',
    outlets: [
      {
        storyId: 'mock-1',
        outlet: 'CBC',
        framing: 'Ottawa frames the plan as a bridge between provinces and developers.',
        summary:
          'Federal officials outlined incentives for rental builds outside the largest metros, with provinces asked to align zoning within eighteen months.',
        imageUrl: MOCK_FEED.items[0].imageUrl,
        audioStatus: 'ready',
        publishedAt: hoursAgo(2),
        sourceUrl: 'https://www.cbc.ca',
      },
      {
        storyId: 'mock-1-global',
        outlet: 'Global News',
        framing: 'Global emphasizes mayors who worry about infrastructure lagging growth.',
        summary:
          'Several mid-size mayors said transit and water capacity must be funded alongside density bonuses.',
        audioStatus: 'ready',
        publishedAt: hoursAgo(2.5),
        sourceUrl: 'https://globalnews.ca',
      },
      {
        storyId: 'mock-1-gm',
        outlet: 'Globe and Mail',
        framing: 'The Globe focuses on investor appetite for purpose-built rentals.',
        summary:
          'Analysts expect institutional capital to shift toward six-storey wood builds if tax credits land in the budget.',
        audioStatus: 'pending',
        publishedAt: hoursAgo(3),
        sourceUrl: 'https://www.theglobeandmail.com',
      },
    ],
  },
  'cluster-fire': {
    clusterId: 'cluster-fire',
    title: 'Prairie wildfire smoke',
    outlets: [
      {
        storyId: 'mock-3',
        outlet: 'CTV',
        framing: 'CTV highlights school recess cancellations in Calgary.',
        summary:
          'Health officials recommend limiting outdoor activity for sensitive groups as plumes drift east from Alberta.',
        imageUrl: MOCK_FEED.items[2].imageUrl,
        audioStatus: 'pending',
        publishedAt: hoursAgo(5),
        sourceUrl: 'https://www.ctvnews.ca',
      },
      {
        storyId: 'mock-3-cbc',
        outlet: 'CBC',
        framing: 'CBC notes Indigenous communities pre-positioning clean-air centres.',
        summary:
          'Northern communities are stocking HEPA filters and coordinating elder wellness checks as smoke persists.',
        audioStatus: 'ready',
        publishedAt: hoursAgo(5.5),
        sourceUrl: 'https://www.cbc.ca',
      },
    ],
  },
};

export const MOCK_STORYLINES: StorylineSummary[] = [
  {
    threadId: 'thread-port',
    title: 'West Coast port labour dispute',
    status: 'open',
    updatedAt: hoursAgo(4),
    updateCount: 12,
    topic: 'Canada',
    place: 'Vancouver',
    coverImageUrl: MOCK_FEED.items[5]?.imageUrl,
    latestOutlet: 'Global News',
    latestStoryId: 'mock-6',
  },
  {
    threadId: 'thread-election',
    title: 'Provincial election polling shifts',
    status: 'open',
    updatedAt: hoursAgo(20),
    updateCount: 8,
    topic: 'Politics',
    coverImageUrl: MOCK_FEED.items[3]?.imageUrl,
    latestOutlet: 'CBC',
    latestStoryId: 'e2',
  },
  {
    threadId: 'thread-olympics',
    title: '2030 Winter Games bid post-mortem',
    status: 'closed',
    updatedAt: hoursAgo(72),
    updateCount: 15,
    topic: 'Canada',
    place: 'BC',
    coverImageUrl: MOCK_FEED.items[1]?.imageUrl,
    latestOutlet: 'CBC',
    latestStoryId: 'o1',
  },
];

export const MOCK_STORYLINE_DETAILS: Record<string, StorylineDetail> = {
  'thread-port': {
    threadId: 'thread-port',
    title: 'West Coast port labour dispute',
    status: 'open',
    topic: 'Canada',
    place: 'Vancouver',
    updates: [
      {
        storyId: 'mock-6',
        publishedAt: hoursAgo(4),
        outlet: 'Global News',
        brief: 'Talks resume with a federal mediator; daily sessions scheduled through Friday.',
        audioStatus: 'ready',
      },
      {
        storyId: 'u2',
        publishedAt: hoursAgo(16),
        outlet: 'CBC',
        brief: 'Retailers warn of holiday inventory delays if a full shutdown returns.',
        audioStatus: 'ready',
      },
      {
        storyId: 'u3',
        publishedAt: hoursAgo(28),
        outlet: 'Globe and Mail',
        brief: 'Union members vote to reject the latest shift-scheduling proposal.',
        audioStatus: 'none',
      },
    ],
  },
  'thread-election': {
    threadId: 'thread-election',
    title: 'Provincial election polling shifts',
    status: 'open',
    topic: 'Politics',
    updates: [
      {
        storyId: 'e1',
        publishedAt: hoursAgo(20),
        outlet: 'Toronto Star',
        brief: 'New poll shows tightening race in suburban ridings outside the capital.',
        audioStatus: 'ready',
      },
      {
        storyId: 'e2',
        publishedAt: hoursAgo(36),
        outlet: 'CBC',
        brief: 'Leaders spar over health spending in the lone televised debate.',
        audioStatus: 'ready',
      },
    ],
  },
  'thread-olympics': {
    threadId: 'thread-olympics',
    title: '2030 Winter Games bid post-mortem',
    status: 'closed',
    topic: 'Canada',
    place: 'BC',
    updates: [
      {
        storyId: 'o1',
        publishedAt: hoursAgo(72),
        outlet: 'CBC',
        brief: 'Bid committee releases final cost report; province ends further pursuit.',
        audioStatus: 'ready',
      },
    ],
  },
};

export function getMockStoryById(storyId: string) {
  return MOCK_FEED.items.find((s) => s.storyId === storyId);
}
