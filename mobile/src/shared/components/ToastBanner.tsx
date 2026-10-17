import { useEffect } from 'react';
import { StyleSheet, Text } from 'react-native';
import Animated, { FadeInDown, FadeOutUp } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';

type Props = {
  message: string | null;
  onClear: () => void;
};

export function ToastBanner({ message, onClear }: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClear, 2800);
    return () => clearTimeout(t);
  }, [message, onClear]);

  if (!message) return null;

  return (
    <Animated.View
      entering={FadeInDown.duration(motion.duration.base)}
      exiting={FadeOutUp.duration(motion.duration.fast)}
      style={[
        styles.toast,
        { bottom: insets.bottom + 88, backgroundColor: colors.toastBg },
      ]}
      accessibilityLiveRegion="polite">
      <Text style={[styles.text, { color: colors.toastText }]}>{message}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    alignSelf: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999,
    zIndex: 100,
  },
  text: {
    fontSize: 14,
    fontWeight: '500',
  },
});
