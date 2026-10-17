import AsyncStorage from '@react-native-async-storage/async-storage';

/** Drop stale mock/API feed rows that can show broken offline cards. */
export async function clearFeedCache(): Promise<void> {
  try {
    await AsyncStorage.removeItem('cnews.feed.cache.v1');
  } catch {
    /* ignore */
  }
}
