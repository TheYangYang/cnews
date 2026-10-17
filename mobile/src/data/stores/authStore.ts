import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { postGoogleAuth } from '@/data/api/endpoints';
import type { UserProfile } from '@/data/types/api';

type AuthState = {
  accessToken: string | null;
  expiresAt: string | null;
  user: UserProfile | null;
  signInWithGoogleStub: () => Promise<void>;
  signOut: () => void;
  setUserTopics: (topics: string[]) => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      expiresAt: null,
      user: null,
      signInWithGoogleStub: async () => {
        // Dev bypass accepted by backend: "dev:<email>"
        const res = await postGoogleAuth('dev:demo@cnews.local');
        set({
          accessToken: res.accessToken,
          expiresAt: res.expiresAt,
          user: res.user,
        });
        if (res.user.topics?.length) {
          const { useSettingsStore } = await import('@/data/stores/settingsStore');
          await useSettingsStore.getState().setTopics(res.user.topics);
        }
      },
      signOut: () => set({ accessToken: null, expiresAt: null, user: null }),
      setUserTopics: (topics) => {
        const user = get().user;
        if (!user) return;
        set({ user: { ...user, topics } });
      },
    }),
    {
      name: 'cnews-auth',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({
        accessToken: s.accessToken,
        expiresAt: s.expiresAt,
        user: s.user,
      }),
    },
  ),
);
