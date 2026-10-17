import AsyncStorage from '@react-native-async-storage/async-storage';

const PREFIX = 'cnews.pref.';

export async function getPref(key: string): Promise<string | null> {
  return AsyncStorage.getItem(PREFIX + key);
}

export async function setPref(key: string, value: string): Promise<void> {
  await AsyncStorage.setItem(PREFIX + key, value);
}

export async function tryGetSqlite(): Promise<null> {
  return null;
}
