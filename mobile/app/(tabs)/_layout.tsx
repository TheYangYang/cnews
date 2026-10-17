import { Tabs } from 'expo-router';
import { Platform, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { PlayTabButton } from '@/features/player/PlayTabButton';
import { ToastBanner } from '@/shared/components/ToastBanner';
import { usePlayerStore } from '@/data/stores/playerStore';
import { useAuthStore } from '@/data/stores/authStore';
import { useTheme } from '@/shared/theme/ThemeProvider';

export default function TabLayout() {
  const toast = usePlayerStore((s) => s.toastMessage);
  const clearToast = usePlayerStore((s) => s.clearToast);
  const user = useAuthStore((s) => s.user);
  const { colors } = useTheme();

  return (
    <>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarStyle: {
            backgroundColor: colors.tabBar,
            borderTopColor: colors.tabBarBorder,
            height: Platform.OS === 'ios' ? 90 : 70,
            paddingTop: 6,
          },
          tabBarLabelStyle: styles.tabLabel,
          animation: 'fade',
          sceneStyle: { backgroundColor: colors.background },
        }}>
        <Tabs.Screen
          name="index"
          options={{
            title: 'Home',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="home-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="storylines"
          options={{
            title: 'Storylines',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="git-branch-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="play"
          options={{
            title: '',
            tabBarIcon: () => null,
            tabBarButton: () => <PlayTabButton />,
          }}
          listeners={{
            tabPress: (e) => {
              e.preventDefault();
            },
          }}
        />
        <Tabs.Screen
          name="settings"
          options={{
            title: 'Settings',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="options-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="login"
          options={{
            title: user ? 'Account' : 'Login',
            tabBarIcon: ({ color, size }) => (
              <Ionicons
                name={user ? 'person-circle' : 'person-circle-outline'}
                size={size}
                color={color}
              />
            ),
          }}
        />
        <Tabs.Screen
          name="story/[id]"
          options={{
            href: null,
            title: 'Story',
            animation: 'fade',
          }}
        />
        <Tabs.Screen
          name="storyline/[id]"
          options={{
            href: null,
            title: 'Storyline',
            animation: 'fade',
          }}
        />
      </Tabs>
      <ToastBanner message={toast} onClear={clearToast} />
    </>
  );
}

const styles = StyleSheet.create({
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
  },
});
