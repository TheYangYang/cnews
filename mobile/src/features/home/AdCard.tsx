import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import type { DisplayAd } from '@/data/types/api';
import { rewriteMediaUrl } from '@/data/api/rewriteMediaUrl';
import { useTheme } from '@/shared/theme/ThemeProvider';
import { wallItemAspect } from '@/features/home/mixDisplayAds';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = {
  ad: DisplayAd;
  width: number;
  onPress: () => void;
};

export function AdCard({ ad, width, onPress }: Props) {
  const { colors } = useTheme();
  const aspect = wallItemAspect({ kind: 'ad', ad });
  const height = width / aspect;
  const scale = useSharedValue(1);
  const image = ad.imageUrl ? (rewriteMediaUrl(ad.imageUrl) ?? ad.imageUrl) : null;

  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(0.975, { damping: 18, stiffness: 320 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 16, stiffness: 280 });
      }}
      style={[styles.card, { width, height, backgroundColor: colors.ink }, anim]}
      accessibilityRole="link"
      accessibilityLabel={`Ad, ${ad.advertiser}, ${ad.title}`}>
      {image ? (
        <Image
          source={{ uri: image }}
          style={StyleSheet.absoluteFill}
          contentFit="cover"
          transition={200}
          recyclingKey={ad.adId}
        />
      ) : null}
      <LinearGradient
        colors={['rgba(20,24,31,0.04)', 'rgba(20,24,31,0.4)', colors.imageScrim]}
        locations={[0.28, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View style={[styles.badge, { backgroundColor: 'rgba(20,24,31,0.72)' }]}>
        <Text style={styles.badgeText}>Ad</Text>
      </View>
      <View style={styles.copy}>
        <Text style={styles.title} numberOfLines={3}>
          {ad.title}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {ad.advertiser}
        </Text>
      </View>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 8,
    overflow: 'hidden',
    marginBottom: 4,
  },
  badge: {
    position: 'absolute',
    top: 8,
    left: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.92)',
    letterSpacing: 0.2,
  },
  copy: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 11,
    paddingBottom: 11,
    paddingTop: 36,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 18.5,
    letterSpacing: -0.25,
  },
  meta: {
    marginTop: 5,
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.78)',
  },
});
