import Constants, { ExecutionEnvironment } from 'expo-constants';
import { Platform } from 'react-native';
import type { NativeAd } from 'react-native-google-mobile-ads';

/**
 * Google AdMob native ads, non-personalized only (no tracking prompt).
 *
 * Ads are loaded ahead into a small pool and a wall/list slot is only created for
 * an ad that already loaded, so there are never empty ad boxes and card heights
 * stay exact. First-party ads from /v1/ads/display still win when there are any
 * (see mixDisplayAds).
 */

type Gma = typeof import('react-native-google-mobile-ads');
type Surface = 'home' | 'storylines';

// Expo Go has no AdMob native module; loading the library there would crash.
export const adsSupported =
  Platform.OS !== 'web' && Constants.executionEnvironment !== ExecutionEnvironment.StoreClient;
// eslint-disable-next-line @typescript-eslint/no-require-imports
export const gma: Gma | null = adsSupported ? require('react-native-google-mobile-ads') : null;

const POOL_SIZE = 2;
/** Google: a loaded native ad must be shown within an hour. */
const MAX_AGE_MS = 55 * 60_000;
const RETRY_AFTER_MS = 60_000;

const ready: { ad: NativeAd; loadedAt: number }[] = [];
const placed = new Map<string, { ad: NativeAd; surface: Surface }>();
let inflight = 0;
let seq = 0;
let started = false;
let retryTimer: ReturnType<typeof setTimeout> | null = null;

function unitId(sdk: Gma): string {
  // Test ads in dev builds, and whenever a real unit ID is not configured.
  if (__DEV__) return sdk.TestIds.NATIVE;
  const real =
    Platform.OS === 'ios'
      ? process.env.EXPO_PUBLIC_ADMOB_NATIVE_IOS
      : process.env.EXPO_PUBLIC_ADMOB_NATIVE_ANDROID;
  return real || sdk.TestIds.NATIVE;
}

function refill() {
  const sdk = gma;
  if (!sdk || !started) return;
  while (ready.length + inflight < POOL_SIZE) {
    inflight++;
    sdk.NativeAd.createForAdRequest(unitId(sdk), {
      requestNonPersonalizedAdsOnly: true,
      aspectRatio: sdk.NativeMediaAspectRatio.ANY,
      startVideoMuted: true,
    })
      .then((ad) => {
        ready.push({ ad, loadedAt: Date.now() });
      })
      .catch(() => {
        // No fill or offline: try again later instead of hammering the network.
        if (!retryTimer) {
          retryTimer = setTimeout(() => {
            retryTimer = null;
            refill();
          }, RETRY_AFTER_MS);
        }
      })
      .finally(() => {
        inflight--;
      });
  }
}

/** Call once at app start. No-op in Expo Go and on web. */
export async function startAds(): Promise<void> {
  const sdk = gma;
  if (!sdk || started) return;
  try {
    await sdk.default().setRequestConfiguration({
      maxAdContentRating: sdk.MaxAdContentRating.PG,
    });
    await sdk.default().initialize();
    started = true;
    refill();
  } catch {
    /* ads are optional; the app works without them */
  }
}

/** Returns a claimer for mixDisplayAds: hands out a loaded ad's slot id, or null. */
export function takeNativeAd(surface: Surface): () => string | null {
  return () => {
    let entry = ready.shift();
    while (entry && Date.now() - entry.loadedAt > MAX_AGE_MS) {
      entry.ad.destroy();
      entry = ready.shift();
    }
    refill();
    if (!entry) return null;
    const slotId = `${surface}-${++seq}`;
    placed.set(slotId, { ad: entry.ad, surface });
    return slotId;
  };
}

export function getNativeAd(slotId: string): NativeAd | undefined {
  return placed.get(slotId)?.ad;
}

/** Destroy ads on a surface that are no longer in its list (e.g. after a refresh). */
export function releaseNativeAds(surface: Surface, keep: Iterable<string>): void {
  const kept = new Set(keep);
  for (const [slotId, entry] of placed) {
    if (entry.surface === surface && !kept.has(slotId)) {
      entry.ad.destroy();
      placed.delete(slotId);
    }
  }
}
