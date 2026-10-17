import { Easing } from 'react-native-reanimated';

/** Shared motion tokens — short, purposeful, not decorative noise. */
export const motion = {
  duration: {
    fast: 160,
    base: 240,
    slow: 360,
  },
  easing: {
    out: Easing.out(Easing.cubic),
    inOut: Easing.inOut(Easing.cubic),
  },
} as const;
