import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined;

export function getApiBaseUrl(): string {
  return (
    process.env.EXPO_PUBLIC_API_BASE_URL ??
    extra?.apiBaseUrl ??
    'http://127.0.0.1:5080'
  );
}
