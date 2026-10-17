import type { StoryCard, StorylineDetail, StorylineUpdate } from '@/data/types/api';

export function updateToStoryCard(
  update: StorylineUpdate,
  detail: Pick<StorylineDetail, 'title' | 'topic' | 'place'>,
): StoryCard {
  const when = update.at ?? update.publishedAt ?? new Date().toISOString();
  const summary = update.summary ?? update.brief ?? '';
  return {
    storyId: update.storyId,
    title: update.title ?? detail.title,
    summary,
    summaryPreview: summary.slice(0, 120),
    imageUrl: update.imageUrl ?? null,
    outlet: update.outlet,
    topic: detail.topic ?? '',
    place: detail.place,
    publishedAt: when,
    sourceUrl: update.sourceUrl ?? '',
    audioStatus: update.audioStatus,
    audioUrl: update.audioUrl,
  };
}

export function updatesToCards(detail: StorylineDetail): StoryCard[] {
  return detail.updates.map((u) => updateToStoryCard(u, detail));
}
