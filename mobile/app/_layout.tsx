import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import {
  ErrorBoundary as RouterErrorBoundary,
  Stack,
  useNavigationContainerRef,
  type ErrorBoundaryProps,
} from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import 'react-native-reanimated';

import { BootstrapGate } from '@/features/bootstrap/BootstrapGate';
import { startAds } from '@/features/ads/nativeAdPool';
import { Sentry, initMonitoring, navigationIntegration } from '@/shared/monitoring/sentry';
import { ThemeProvider, useTheme } from '@/shared/theme/ThemeProvider';

initMonitoring();

/** Expo Router's screen error boundary, reporting the crash to Sentry first. */
export function ErrorBoundary(props: ErrorBoundaryProps) {
  useEffect(() => {
    Sentry.captureException(props.error);
  }, [props.error]);
  return <RouterErrorBoundary {...props} />;
}

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

function RootNavigation() {
  const { colors, isDark } = useTheme();

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <BootstrapGate>
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
            animation: 'fade_from_bottom',
            animationDuration: 240,
          }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="storyline/[id]" options={{ animation: 'fade' }} />
        </Stack>
      </BootstrapGate>
    </>
  );
}

function RootLayout() {
  const navigationRef = useNavigationContainerRef();
  useEffect(() => {
    if (navigationRef) navigationIntegration.registerNavigationContainer(navigationRef);
  }, [navigationRef]);

  useEffect(() => {
    void startAds();
  }, []);

  const [loaded, error] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
  });

  useEffect(() => {
    if (error) throw error;
  }, [error]);

  useEffect(() => {
    if (loaded) void SplashScreen.hideAsync();
  }, [loaded]);

  if (!loaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <RootNavigation />
        </ThemeProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

export default Sentry.wrap(RootLayout);
