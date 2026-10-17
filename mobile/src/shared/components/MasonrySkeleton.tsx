import { useWindowDimensions, View, StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { useEffect } from 'react';

import { useTheme } from '@/shared/theme/ThemeProvider';
import { columnWidthForScreen } from '@/shared/utils/masonry';

const heights = [140, 200, 120, 180, 160, 130];

export function MasonrySkeleton() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const colW = columnWidthForScreen(width);
  const opacity = useSharedValue(0.45);

  useEffect(() => {
    opacity.value = withRepeat(withTiming(0.85, { duration: 900 }), -1, true);
  }, [opacity]);

  const pulse = useAnimatedStyle(() => ({ opacity: opacity.value }));

  const leftHeights = heights.filter((_, i) => i % 2 === 0);
  const rightHeights = heights.filter((_, i) => i % 2 === 1);

  return (
    <View style={styles.row}>
      <View style={styles.col}>
        {leftHeights.map((h, i) => (
          <Animated.View
            key={`l-${i}`}
            style={[
              styles.block,
              { width: colW, height: h, backgroundColor: colors.skeleton },
              pulse,
            ]}
          />
        ))}
      </View>
      <View style={styles.col}>
        {rightHeights.map((h, i) => (
          <Animated.View
            key={`r-${i}`}
            style={[
              styles.block,
              { width: colW, height: h, backgroundColor: colors.skeleton },
              pulse,
            ]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 8,
    paddingTop: 4,
  },
  col: { flex: 1, gap: 6 },
  block: {
    borderRadius: 14,
  },
});
