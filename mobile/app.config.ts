import type { ConfigContext, ExpoConfig } from 'expo/config';

/**
 * app.json holds the config; this only injects the AdMob app IDs per build.
 * Google's sample app IDs serve test ads, so dev and preview builds need no
 * AdMob account. Set ADMOB_IOS_APP_ID / ADMOB_ANDROID_APP_ID in the eas.json
 * production profile (AdMob → Apps → App settings → App ID).
 */
const ADMOB_TEST_IOS_APP_ID = 'ca-app-pub-3940256099942544~1458002511';
const ADMOB_TEST_ANDROID_APP_ID = 'ca-app-pub-3940256099942544~3347511713';

export default ({ config }: ConfigContext): ExpoConfig => {
  const admob = [
    'react-native-google-mobile-ads',
    {
      iosAppId: process.env.ADMOB_IOS_APP_ID || ADMOB_TEST_IOS_APP_ID,
      androidAppId: process.env.ADMOB_ANDROID_APP_ID || ADMOB_TEST_ANDROID_APP_ID,
      // Non-personalized ads only: no tracking prompt, so no
      // userTrackingUsageDescription is set (the prompt can never appear).
      delayAppMeasurementInit: true,
    },
  ] as [string, Record<string, unknown>];
  const plugins = (config.plugins ?? []).map((plugin) =>
    plugin === 'react-native-google-mobile-ads' ? admob : plugin,
  );
  return { ...(config as ExpoConfig), plugins };
};
