/** Web has no AdMob SDK; slots are never created there, so these render nothing. */
export function NativeWallAdCard(_props: { slotId: string; width: number }) {
  return null;
}

export function NativeStorylineAdCard(_props: { slotId: string }) {
  return null;
}
