import * as Sentry from '@sentry/react-native';
import Constants from 'expo-constants';

/**
 * Crash reporting. Off unless EXPO_PUBLIC_SENTRY_DSN is set, and off in dev builds
 * (Metro already shows the red box) unless EXPO_PUBLIC_SENTRY_IN_DEV=true.
 */
const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
const enabled = !!dsn && (!__DEV__ || process.env.EXPO_PUBLIC_SENTRY_IN_DEV === 'true');

export const navigationIntegration = Sentry.reactNavigationIntegration({
  enableTimeToInitialDisplay: true,
});

export function initMonitoring() {
  Sentry.init({
    dsn,
    enabled,
    environment: process.env.EXPO_PUBLIC_APP_ENV ?? (__DEV__ ? 'development' : 'production'),
    release: `ca.cracknews.app@${Constants.expoConfig?.version ?? '0.0.0'}`,
    // Guest app: never attach IPs or other personal data.
    sendDefaultPii: false,
    tracesSampleRate: 0.1,
    integrations: [navigationIntegration],
  });
}

export { Sentry };
