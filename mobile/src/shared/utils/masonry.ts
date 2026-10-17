import type { WallItem } from '@/data/types/api';
import { wallItemAspect } from '@/features/home/mixDisplayAds';

const GAP = 4;
const PAD = 3;

export function estimateCardHeight(card: WallItem, columnWidth: number): number {
  return columnWidth / wallItemAspect(card) + GAP;
}

export function splitIntoMasonryColumns(
  items: WallItem[],
  columnWidth: number,
): { left: WallItem[]; right: WallItem[] } {
  const left: WallItem[] = [];
  const right: WallItem[] = [];
  let leftH = 0;
  let rightH = 0;
  for (const item of items) {
    const h = estimateCardHeight(item, columnWidth);
    if (leftH <= rightH) {
      left.push(item);
      leftH += h;
    } else {
      right.push(item);
      rightH += h;
    }
  }
  return { left, right };
}

export function columnWidthForScreen(screenWidth: number): number {
  return (screenWidth - PAD * 2 - GAP) / 2;
}

export { GAP, PAD };
