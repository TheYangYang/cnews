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

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = {
  ad: DisplayAd;
  onPress: () => void;
};

export function StorylineAdCard({ ad, onPress }: Props) {
  const { colors } = useTheme();
  const scale = useSharedValue(1);
  const uri = ad.imageUrl ? (rewriteMediaUrl(ad.imageUrl) ?? ad.imageUrl) : null;

  const anim = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => {
        scale.value = withSpring(0.98, { damping: 18, stiffness: 320 });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 16, stiffness: 280 });
      }}
      style={anim}
      accessibilityRole="link"
      accessibilityLabel={`Ad, ${ad.advertiser}, ${ad.title}`}>
      <View style={styles.card}>
        {uri ? (
          <Image
            source={{ uri }}
            style={StyleSheet.absoluteFill}
            contentFit="cover"
            transition={200}
            recyclingKey={ad.adId}
          />
        ) : (
          <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.ink }]} />
        )}
        <LinearGradient
          colors={['rgba(20,24,31,0.1)', 'rgba(20,24,31,0.55)', colors.imageScrim]}
          locations={[0.2, 0.55, 1]}
          style={StyleSheet.absoluteFill}
        />
        <View style={styles.topRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Ad</Text>
          </View>
        </View>
        <View style={styles.copy}>
          <Text style={styles.kicker} numberOfLines={1}>
            {ad.advertiser}
          </Text>
          <Text style={styles.title} numberOfLines={3}>
            {ad.title}
          </Text>
          <Text style={styles.meta}>Sponsored</Text>
        </View>
      </View>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    height: 220,
    borderRadius: 18,
    overflow: 'hidden',
    marginBottom: 12,
    backgroundColor: '#14181F',
  },
  topRow: {
    position: 'absolute',
    top: 12,
    left: 12,
    right: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: 'rgba(20,24,31,0.72)',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.3,
    color: 'rgba(255,255,255,0.92)',
  },
  copy: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingBottom: 14,
    paddingTop: 40,
    gap: 6,
  },
  kicker: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: 'rgba(255,255,255,0.72)',
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: -0.4,
    lineHeight: 27,
  },
  meta: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.75)',
  },
});
