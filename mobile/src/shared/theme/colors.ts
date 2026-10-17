/**
 * CrackNews palettes — cool graphite + Atlantic blue.
 * Contrast tuned for WCAG AA body text and large interactive targets.
 */
export type ThemeColors = {
  scheme: 'light' | 'dark';
  background: string;
  surface: string;
  surfaceElevated: string;
  ink: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  textOnImage: string;
  /** Text/icon on filled accent buttons */
  onAccent: string;
  border: string;
  accent: string;
  accentSoft: string;
  accentDeep: string;
  accentBright: string;
  ongoing: string;
  ongoingBg: string;
  closed: string;
  closedBg: string;
  speaking: string;
  tabBar: string;
  tabBarBorder: string;
  shadow: string;
  imageScrim: string;
  readerBg: string;
  readerSheetTop: string;
  readerSheetMid: string;
  readerSheetBottom: string;
  readerText: string;
  readerMuted: string;
  toastBg: string;
  toastText: string;
  skeleton: string;
};

export const lightColors: ThemeColors = {
  scheme: 'light',
  background: '#EEF2F7',
  surface: '#FFFFFF',
  surfaceElevated: '#FFFFFF',
  ink: '#0F1724',
  text: '#0F1724',
  textSecondary: '#3D4A5C',
  textMuted: '#5C6B7E',
  textOnImage: '#FFFFFF',
  onAccent: '#FFFFFF',
  border: '#D0D8E4',
  accent: '#1F5FAF',
  accentSoft: '#DCEAFB',
  accentDeep: '#154A8C',
  accentBright: '#2B7DE0',
  ongoing: '#1F5FAF',
  ongoingBg: '#DCEAFB',
  closed: '#5C6B7E',
  closedBg: '#E4E9F0',
  speaking: '#2B7DE0',
  tabBar: '#F7F9FC',
  tabBarBorder: '#D0D8E4',
  shadow: 'rgba(15, 23, 36, 0.12)',
  imageScrim: 'rgba(15, 23, 36, 0.58)',
  readerBg: '#0B1220',
  readerSheetTop: '#F2F5F9',
  readerSheetMid: '#EBF0F6',
  readerSheetBottom: '#E4EAF2',
  readerText: '#0F1724',
  readerMuted: '#5C6B7E',
  toastBg: '#0F1724',
  toastText: '#FFFFFF',
  skeleton: '#D5DCE6',
};

export const darkColors: ThemeColors = {
  scheme: 'dark',
  background: '#0B1018',
  surface: '#151C28',
  surfaceElevated: '#1C2534',
  ink: '#F0F4FA',
  text: '#F0F4FA',
  textSecondary: '#B8C3D4',
  textMuted: '#8A97AB',
  textOnImage: '#FFFFFF',
  onAccent: '#FFFFFF',
  border: '#2A3548',
  accent: '#4B93E7',
  accentSoft: '#1A2F4D',
  accentDeep: '#8FBAF2',
  accentBright: '#5BA3F5',
  ongoing: '#5BA3F5',
  ongoingBg: '#1A2F4D',
  closed: '#8A97AB',
  closedBg: '#1E2633',
  speaking: '#5BA3F5',
  tabBar: '#101622',
  tabBarBorder: '#2A3548',
  shadow: 'rgba(0, 0, 0, 0.5)',
  imageScrim: 'rgba(8, 12, 20, 0.72)',
  readerBg: '#0B1220',
  readerSheetTop: '#0B1220',
  readerSheetMid: '#121A28',
  readerSheetBottom: '#151C28',
  readerText: 'rgba(255,255,255,0.92)',
  readerMuted: 'rgba(255,255,255,0.55)',
  toastBg: '#F0F4FA',
  toastText: '#0F1724',
  skeleton: '#243041',
};

/** @deprecated Prefer useTheme().colors — kept as light default for rare static imports. */
export const colors = lightColors;
