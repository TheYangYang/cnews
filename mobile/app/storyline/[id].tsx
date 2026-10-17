import { Redirect, useLocalSearchParams } from 'expo-router';

/** Legacy stack route → in-tab reader (navbar stays). */
export default function StorylineRedirect() {
  const { id } = useLocalSearchParams<{ id: string }>();
  if (!id) return null;
  return <Redirect href={{ pathname: '/(tabs)/storyline/[id]', params: { id } }} />;
}
