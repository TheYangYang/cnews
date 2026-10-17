import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { StyleSheet, type StyleProp, type ViewStyle } from 'react-native';

import { useTheme } from '@/shared/theme/ThemeProvider';
import { motion } from '@/shared/theme/motion';

type Props = {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  /** Skip enter animation (e.g. home wall already animated). */
  static?: boolean;
};

/** Themed screen shell with a light fade for tab / route transitions. */
export function Screen({ children, style, static: noAnim }: Props) {
  const { colors } = useTheme();

  if (noAnim) {
    return (
      <Animated.View style={[styles.root, { backgroundColor: colors.background }, style]}>
        {children}
      </Animated.View>
    );
  }

  return (
    <Animated.View
      entering={FadeIn.duration(motion.duration.base).easing(motion.easing.out)}
      exiting={FadeOut.duration(motion.duration.fast)}
      style={[styles.root, { backgroundColor: colors.background }, style]}>
      {children}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
