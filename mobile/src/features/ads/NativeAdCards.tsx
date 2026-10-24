import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';

import { NATIVE_AD_ASPECT } from '@/features/home/mixDisplayAds';
import { getNativeAd, gma } from '@/features/ads/nativeAdPool';
import { useTheme } from '@/shared/theme/ThemeProvider';

/**
 * Google native ads drawn like the app's own ad cards. Google's rules: the "Ad"
 * label must show, the headline is required, and the SDK places the AdChoices
 * icon (top right by default, so the badge sits top left). Taps on registered
 * assets and the media are handled by the SDK.
 */

/** Home masonry card: fixed shape so wall heights stay exact. */
export function NativeWallAdCard({ slotId, width }: { slotId: string; width: number }) {
  const { colors } = useTheme();
  const ad = getNativeAd(slotId);
  const height = width / NATIVE_AD_ASPECT;
  if (!gma || !ad) {
    // Released after a refresh but still on screen for a frame: keep the space.
    return <View style={{ width, height, marginBottom: 4 }} />;
  }
  const { NativeAdView, NativeAsset, NativeAssetType, NativeMediaView } = gma;
  return (
    <NativeAdView
      nativeAd={ad}
      style={[wall.card, { width, height, backgroundColor: colors.ink }]}>
      <View style={StyleSheet.absoluteFill}>
        <NativeMediaView style={wall.media} resizeMode="cover" />
      </View>
      <LinearGradient
        pointerEvents="none"
        colors={['rgba(20,24,31,0.04)', 'rgba(20,24,31,0.4)', colors.imageScrim]}
        locations={[0.28, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View pointerEvents="none" style={wall.badge}>
        <Text style={wall.badgeText}>Ad</Text>
      </View>
      <View style={wall.copy} pointerEvents="box-none">
        <NativeAsset assetType={NativeAssetType.HEADLINE}>
          <Text style={wall.title} numberOfLines={3}>
            {ad.headline}
          </Text>
        </NativeAsset>
        {ad.advertiser ? (
          <NativeAsset assetType={NativeAssetType.ADVERTISER}>
            <Text style={wall.meta} numberOfLines={1}>
              {ad.advertiser}
            </Text>
          </NativeAsset>
        ) : null}
      </View>
    </NativeAdView>
  );
}

/** Storylines list card: full width, same height as StorylineAdCard. */
export function NativeStorylineAdCard({ slotId }: { slotId: string }) {
  const ad = getNativeAd(slotId);
  if (!gma || !ad) return <View style={{ height: list.card.height, marginBottom: 12 }} />;
  const { NativeAdView, NativeAsset, NativeAssetType, NativeMediaView } = gma;
  return (
    <NativeAdView nativeAd={ad} style={list.card}>
      <View style={StyleSheet.absoluteFill}>
        <NativeMediaView style={wall.media} resizeMode="cover" />
      </View>
      <LinearGradient
        pointerEvents="none"
        colors={['rgba(20,24,31,0.1)', 'rgba(20,24,31,0.55)', 'rgba(8,12,20,0.92)']}
        locations={[0.2, 0.55, 1]}
        style={StyleSheet.absoluteFill}
      />
      <View pointerEvents="none" style={list.badge}>
        <Text style={list.badgeText}>Ad</Text>
      </View>
      <View style={list.copy} pointerEvents="box-none">
        {ad.advertiser ? (
          <NativeAsset assetType={NativeAssetType.ADVERTISER}>
            <Text style={list.kicker} numberOfLines={1}>
              {ad.advertiser}
            </Text>
          </NativeAsset>
        ) : null}
        <NativeAsset assetType={NativeAssetType.HEADLINE}>
          <Text style={list.title} numberOfLines={2}>
            {ad.headline}
          </Text>
        </NativeAsset>
        <View style={list.footer} pointerEvents="box-none">
          <Text style={list.meta}>Sponsored</Text>
          {ad.callToAction ? (
            <NativeAsset assetType={NativeAssetType.CALL_TO_ACTION}>
              <Text style={list.cta}>{ad.callToAction}</Text>
            </NativeAsset>
          ) : null}
        </View>
      </View>
    </NativeAdView>
  );
}

const wall = StyleSheet.create({
  card: { borderRadius: 8, overflow: 'hidden', marginBottom: 4 },
  // Both dimensions set, so the media view's own aspect ratio cannot change the card.
  media: { width: '100%', height: '100%' },
  badge: {
    position: 'absolute',
    top: 8,
    left: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(20,24,31,0.72)',
  },
  badgeText: { fontSize: 10, fontWeight: '700', color: 'rgba(255,255,255,0.92)', letterSpacing: 0.2 },
  copy: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 11, paddingBottom: 11 },
  title: { fontSize: 14, fontWeight: '700', color: '#FFFFFF', lineHeight: 18.5, letterSpacing: -0.25 },
  meta: { marginTop: 5, fontSize: 11, fontWeight: '600', color: 'rgba(255,255,255,0.78)' },
});

const list = StyleSheet.create({
  card: { height: 220, borderRadius: 18, overflow: 'hidden', marginBottom: 12, backgroundColor: '#14181F' },
  badge: {
    position: 'absolute',
    top: 12,
    left: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: 'rgba(20,24,31,0.72)',
  },
  badgeText: { fontSize: 11, fontWeight: '800', letterSpacing: 0.3, color: 'rgba(255,255,255,0.92)' },
  copy: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 16, paddingBottom: 14, gap: 6 },
  kicker: {
    fontFamily: 'SpaceMono',
    fontSize: 11,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: 'rgba(255,255,255,0.72)',
  },
  title: { fontSize: 20, fontWeight: '800', color: '#fff', letterSpacing: -0.4, lineHeight: 25 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  meta: { fontSize: 12, fontWeight: '600', color: 'rgba(255,255,255,0.75)' },
  cta: {
    overflow: 'hidden',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    fontSize: 13,
    fontWeight: '700',
    color: '#14181F',
    backgroundColor: '#FFFFFF',
  },
});
