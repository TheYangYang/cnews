import { useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCallback, useState } from 'react';
import Animated, {
  FadeIn,
  FadeInDown,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import { useAuthStore } from '@/data/stores/authStore';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';
import { spacing } from '@/shared/theme/spacing';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export function LoginScreen() {
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const user = useAuthStore((s) => s.user);
  const signIn = useAuthStore((s) => s.signInWithGoogleStub);
  const signOut = useAuthStore((s) => s.signOut);
  const [busy, setBusy] = useState(false);
  const btnScale = useSharedValue(1);

  useFocusEffect(
    useCallback(() => {
      void usePlayerStore.getState().stop();
    }, []),
  );

  const onSignIn = async () => {
    setBusy(true);
    try {
      await signIn();
    } finally {
      setBusy(false);
    }
  };

  const btnAnim = useAnimatedStyle(() => ({
    transform: [{ scale: btnScale.value }],
  }));

  const wash = isDark
    ? ([colors.background, '#122038', colors.background] as const)
    : ([colors.background, '#D9E7F8', colors.background] as const);

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <LinearGradient
        colors={[...wash]}
        locations={[0, 0.42, 1]}
        start={{ x: 0.1, y: 0 }}
        end={{ x: 0.9, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      {/* Soft orbit accent — atmosphere, not chrome */}
      <Animated.View
        entering={FadeIn.duration(motion.duration.slow)}
        pointerEvents="none"
        style={[
          styles.orb,
          {
            top: insets.top + height * 0.08,
            backgroundColor: isDark ? 'rgba(75,147,231,0.14)' : 'rgba(43,125,224,0.12)',
          },
        ]}
      />

      <View
        style={[
          styles.content,
          {
            paddingTop: insets.top + 28,
            paddingBottom: insets.bottom + 110,
          },
        ]}>
        <Animated.View entering={FadeInDown.duration(motion.duration.base)}>
          <Text style={[styles.brand, { color: colors.ink }]}>CrackNews</Text>
          <Text style={[styles.tagline, { color: colors.textSecondary }]}>
            Canadian briefs for your wall and your ears.
          </Text>
        </Animated.View>

        <View style={styles.spacer} />

        {user ? (
          <Animated.View
            entering={FadeInDown.delay(60).duration(motion.duration.base)}
            style={styles.signedIn}>
            <View style={[styles.avatar, { backgroundColor: colors.accentSoft }]}>
              <Text style={[styles.avatarLetter, { color: colors.accentDeep }]}>
                {(user.displayName || user.email || '?').slice(0, 1).toUpperCase()}
              </Text>
            </View>
            <Text style={[styles.name, { color: colors.text }]}>{user.displayName}</Text>
            <Text style={[styles.email, { color: colors.textMuted }]}>{user.email}</Text>
            <Text style={[styles.syncNote, { color: colors.textSecondary }]}>
              Topics sync to this account across devices.
            </Text>
            <Pressable
              onPress={signOut}
              style={({ pressed }) => [
                styles.signOutBtn,
                {
                  borderColor: colors.border,
                  backgroundColor: colors.surface,
                  opacity: pressed ? 0.88 : 1,
                },
              ]}>
              <Text style={[styles.signOutText, { color: colors.text }]}>Sign out</Text>
            </Pressable>
          </Animated.View>
        ) : (
          <Animated.View
            entering={FadeInDown.delay(80).duration(motion.duration.base)}
            style={styles.guestBlock}>
            <Text style={[styles.guest, { color: colors.textSecondary }]}>
              Browse as a guest anytime. Sign in when you want topics to follow you.
            </Text>

            <AnimatedPressable
              onPress={() => void onSignIn()}
              disabled={busy}
              onPressIn={() => {
                btnScale.value = withSpring(0.97, { damping: 16, stiffness: 320 });
              }}
              onPressOut={() => {
                btnScale.value = withSpring(1, { damping: 14, stiffness: 260 });
              }}
              style={[
                styles.googleBtn,
                btnAnim,
                {
                  backgroundColor: colors.accentBright,
                  shadowColor: colors.accentDeep,
                },
              ]}
              accessibilityRole="button"
              accessibilityLabel="Continue with Google">
              {busy ? (
                <ActivityIndicator color={colors.onAccent} />
              ) : (
                <>
                  <View style={[styles.googleIconWrap, { backgroundColor: colors.onAccent }]}>
                    <Ionicons name="logo-google" size={16} color={colors.accentDeep} />
                  </View>
                  <Text style={[styles.googleText, { color: colors.onAccent }]}>
                    Continue with Google
                  </Text>
                </>
              )}
            </AnimatedPressable>

            <Text style={[styles.devHint, { color: colors.textMuted }]}>
              Dev builds use a local Google stub.
            </Text>
          </Animated.View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  orb: {
    position: 'absolute',
    right: -80,
    width: 260,
    height: 260,
    borderRadius: 130,
  },
  content: {
    flex: 1,
    paddingHorizontal: spacing.lg + 4,
  },
  brand: {
    fontSize: 42,
    fontWeight: '800',
    letterSpacing: -1.4,
    lineHeight: 46,
  },
  tagline: {
    marginTop: 10,
    fontSize: 17,
    lineHeight: 24,
    maxWidth: 300,
    fontWeight: '500',
  },
  spacer: { flex: 1, minHeight: 48 },
  guestBlock: {
    gap: 16,
    paddingBottom: 8,
  },
  guest: {
    fontSize: 15,
    lineHeight: 22,
    maxWidth: 340,
  },
  googleBtn: {
    borderRadius: 16,
    minHeight: 54,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    shadowOpacity: 0.22,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  googleIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  googleText: { fontWeight: '700', fontSize: 16, letterSpacing: -0.2 },
  devHint: { fontSize: 12, fontWeight: '500' },
  signedIn: {
    gap: 8,
    paddingBottom: 8,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  avatarLetter: { fontSize: 26, fontWeight: '800' },
  name: { fontSize: 24, fontWeight: '800', letterSpacing: -0.4 },
  email: { fontSize: 15, fontWeight: '500' },
  syncNote: {
    marginTop: 6,
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 20,
    maxWidth: 300,
  },
  signOutBtn: {
    alignSelf: 'flex-start',
    marginTop: 4,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
  },
  signOutText: { fontWeight: '700', fontSize: 15 },
});
