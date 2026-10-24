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

const FEED_SCHEMA = `
  CREATE TABLE IF NOT EXISTS feed_stories (
    story_id TEXT PRIMARY KEY NOT NULL,
    payload TEXT NOT NULL,
    published_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_feed_stories_published ON feed_stories(published_at);
`;

let sqlite: Promise<import('expo-sqlite').SQLiteDatabase | null> | null = null;

async function openSqlite(): Promise<import('expo-sqlite').SQLiteDatabase | null> {
  const SQLite = await import('expo-sqlite');
  try {
    const db = await SQLite.openDatabaseAsync('cnews.db');
    await db.execAsync(FEED_SCHEMA);
    return db;
  } catch {
    // Corrupt cache file: it only holds cached cards, so start it over.
    try {
      await SQLite.deleteDatabaseAsync('cnews.db');
      const db = await SQLite.openDatabaseAsync('cnews.db');
      await db.execAsync(FEED_SCHEMA);
      return db;
    } catch {
      return null;
    }
  }
}

/** Optional native SQLite handle for feed cache — opened once, never throws to callers. */
export function tryGetSqlite(): Promise<import('expo-sqlite').SQLiteDatabase | null> {
  if (Platform.OS === 'web') return Promise.resolve(null);
  if (!sqlite) {
    sqlite = openSqlite().catch(() => null);
  }
  return sqlite;
}
