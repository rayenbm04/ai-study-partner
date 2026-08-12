import { useFonts, NotoSerif_400Regular, NotoSerif_500Medium, NotoSerif_600SemiBold, NotoSerif_700Bold } from "@expo-google-fonts/noto-serif";
import { PortalHost } from "@rn-primitives/portal";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import "../global.css";
import { AuthProvider, useAuth } from "../lib/auth-context";
import { LanguageProvider } from "../lib/language-context";
import { ThemeProvider, useTheme } from "../lib/theme-context";

/**
 * Auth gating via Stack.Protected (guard props), not a useEffect +
 * router.replace. That older pattern renders whichever screen the router
 * picks first, THEN redirects once the effect runs a tick later — so an
 * unauthenticated user's browser would still mount (tabs)/index for one
 * frame, firing its data-fetching effects with no access token yet and
 * blowing up with "Not authenticated." Stack.Protected instead prevents a
 * guarded screen from mounting at all until its guard is true, which
 * closes that race condition at the source rather than racing to redirect
 * away from it.
 */
function RootNavigator() {
  const { user, isLoading } = useAuth();
  const { colors, isDark } = useTheme();

  // Nothing to route to yet — still checking secure storage for an
  // existing session. Deliberately render nothing rather than guessing.
  if (isLoading) return null;

  return (
    <>
      <StatusBar style={isDark ? "light" : "dark"} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
        <Stack.Protected guard={!user}>
          <Stack.Screen name="(auth)" />
        </Stack.Protected>
        <Stack.Protected guard={!!user}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="onboarding" />
          <Stack.Screen name="coach/[subjectId]" options={{ presentation: "modal" }} />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    NotoSerif_400Regular,
    NotoSerif_500Medium,
    NotoSerif_600SemiBold,
    NotoSerif_700Bold,
  });

  if (!fontsLoaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <LanguageProvider>
          <ThemeProvider>
            <AuthProvider>
              <RootNavigator />
            </AuthProvider>
          </ThemeProvider>
        </LanguageProvider>
      </SafeAreaProvider>
      <PortalHost />
    </GestureHandlerRootView>
  );
}
