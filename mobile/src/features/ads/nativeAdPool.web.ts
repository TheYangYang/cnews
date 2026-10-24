/** Web has no AdMob SDK: no native ads, same API. */
export const adsSupported = false;
export const gma = null;

export async function startAds(): Promise<void> {}

export function takeNativeAd(_surface: 'home' | 'storylines'): () => string | null {
  return () => null;
}

export function getNativeAd(_slotId: string): undefined {
  return undefined;
}

export function releaseNativeAds(_surface: 'home' | 'storylines', _keep: Iterable<string>): void {}
