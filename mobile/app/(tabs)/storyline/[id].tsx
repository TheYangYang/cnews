import { useLocalSearchParams } from 'expo-router';

import { StorylineReaderScreen } from '@/features/storylines/StorylineReaderScreen';

export default function StorylineTabRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <StorylineReaderScreen threadId={String(id)} />;
}
