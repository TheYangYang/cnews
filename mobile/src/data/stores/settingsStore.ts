import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { setPref, getPref } from '@/data/db/database';
import { putUserTopics } from '@/data/api/endpoints';
import { useAuthStore } from '@/data/stores/authStore';

type SettingsState = {
  selectedTopics: string[];
  hydratedFromSqlite: boolean;
  setTopics: (topics: string[]) => Promise<void>;
  toggleTopic: (topicId: string) => Promise<void>;
  hydrateFromSqlite: () => Promise<void>;
};

const DEFAULT_TOPICS = ['Top', 'Canada', 'Local', 'Business', 'Health', 'Politics'];

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      selectedTopics: DEFAULT_TOPICS,
      hydratedFromSqlite: false,
      setTopics: async (topics) => {
        set({ selectedTopics: topics });
        await setPref('topics', JSON.stringify(topics));
        const token = useAuthStore.getState().accessToken;
        if (token) {
          try {
            const user = await putUserTopics(topics, token);
            useAuthStore.getState().setUserTopics(user.topics);
          } catch {
            /* offline — local mirror only */
          }
        }
      },
      toggleTopic: async (topicId) => {
        const current = get().selectedTopics;
        const next = current.includes(topicId)
          ? current.filter((t) => t !== topicId)
          : [...current, topicId];
        await get().setTopics(next.length ? next : DEFAULT_TOPICS);
      },
      hydrateFromSqlite: async () => {
        if (get().hydratedFromSqlite) return;
        const topicsRaw = await getPref('topics');
        const authTopics = useAuthStore.getState().user?.topics;
        let selected = topicsRaw
          ? (JSON.parse(topicsRaw) as string[])
          : authTopics?.length
            ? authTopics
            : DEFAULT_TOPICS;
        // Ensure demo categories stay visible after older installs.
        for (const t of ['Business', 'Health', 'Politics'] as const) {
          if (!selected.includes(t)) selected = [...selected, t];
        }
        set({
          hydratedFromSqlite: true,
          selectedTopics: selected,
        });
        await setPref('topics', JSON.stringify(selected));
      },
    }),
    {
      name: 'cnews-settings-v3',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
