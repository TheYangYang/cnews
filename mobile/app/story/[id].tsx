import { Redirect, useLocalSearchParams } from 'expo-router';

/** Legacy deep link → in-tab reader (navbar stays). */
export default function StoryRedirect() {
  const { id } = useLocalSearchParams<{ id: string }>();
  if (!id) return null;
  return <Redirect href={{ pathname: '/(tabs)/story/[id]', params: { id } }} />;
}
