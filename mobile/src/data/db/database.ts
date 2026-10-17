import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const PREFIX = 'cnews.pref.';

/**
 * Prefs use AsyncStorage so cold start never depends on native SQLite.
 * Feed cache still tries SQLite when available (see feedRepository).
 */
export async function getPref(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

export async function setPref(key: string, value: string): Promise<void> {
  try {
    await AsyncStorage.setItem(PREFIX + key, value);
  } catch {
    /* ignore */
  }
}

/** Optional native SQLite handle for feed cache — never throws to callers. */
export async function tryGetSqlite(): Promise<import('expo-sqlite').SQLiteDatabase | null> {
  if (Platform.OS === 'web') return null;
  try {
    const SQLite = await import('expo-sqlite');
    const db = await SQLite.openDatabaseAsync('cnews.db');
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS feed_stories (
        story_id TEXT PRIMARY KEY NOT NULL,
        payload TEXT NOT NULL,
        published_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
    return db;
  } catch {
    try {
      const SQLite = await import('expo-sqlite');
      await SQLite.deleteDatabaseAsync('cnews.db');
      const db = await SQLite.openDatabaseAsync('cnews.db');
      await db.execAsync(`
        CREATE TABLE IF NOT EXISTS feed_stories (
          story_id TEXT PRIMARY KEY NOT NULL,
          payload TEXT NOT NULL,
          published_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
      `);
      return db;
    } catch {
      return null;
    }
  }
}
