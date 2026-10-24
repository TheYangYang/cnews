import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined;

export function getApiBaseUrl(): string {
  const base =
    process.env.EXPO_PUBLIC_API_BASE_URL || extra?.apiBaseUrl || 'http://127.0.0.1:5080';
  return base.replace(/\/+$/, '');
}

/**
 * Offline demo data (seed/mockData) when the API is unreachable. Dev builds only:
 * a production user must never see fake stories or a mock sign-in.
 * Set EXPO_PUBLIC_USE_MOCKS=false to test real offline behavior in dev.
 */
export const MOCKS_ENABLED = __DEV__ && process.env.EXPO_PUBLIC_USE_MOCKS !== 'false';
