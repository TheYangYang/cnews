import { useLocalSearchParams } from 'expo-router';

import { StoryReaderScreen } from '@/features/reader/StoryReaderScreen';

export default function StoryRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const storyId = String(id ?? '');
  // Remount when id changes — Expo reuses this route and would keep the old pager index.
  return <StoryReaderScreen key={storyId} storyId={storyId} />;
}
