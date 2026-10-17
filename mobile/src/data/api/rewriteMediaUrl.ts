import { getApiBaseUrl } from '@/data/api/config';

/**
 * Audio URLs from the API may use 127.0.0.1. Rewrite to the configured API host
 * so physical devices (Expo Go) can fetch media on the LAN.
 */
export function rewriteMediaUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined;
  try {
    const api = new URL(getApiBaseUrl());
    const media = new URL(url);
    if (
      media.hostname === '127.0.0.1' ||
      media.hostname === 'localhost' ||
      media.hostname === '0.0.0.0'
    ) {
      media.protocol = api.protocol;
      media.hostname = api.hostname;
      if (api.port) media.port = api.port;
    }
    return media.toString();
  } catch {
    return url;
  }
}
