import type { ReactNode } from "react";
import { Platform, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { spacing } from "../../constants/theme";

const WEB_MAX_WIDTH = 480;

/** Standard screen wrapper — safe-area aware, themed background, consistent
 * horizontal padding so individual screens don't each reinvent it.
 *
 * Background comes from the shared mauve/base-nova palette (global.css's
 * --background/--muted, same tokens the web app uses) via NativeWind
 * classes, not the old theme-context colors — this is the one piece of the
 * old kit every screen depends on, migrated first so the new palette
 * applies everywhere immediately, ahead of each screen's own component
 * migration.
 *
 * On web this is a phone-width app, not a full-bleed web page — full browser
 * width just stretches every card/button into something that never looked
 * like this in the design. So on web only, the screen sits in a centered
 * fixed-width column with a neutral gutter on either side; native is
 * untouched (there's no "gutter" concept on an actual phone). */
export function Screen({ children, scroll: _scroll, style }: { children: ReactNode; scroll?: boolean; style?: object }) {
  if (Platform.OS === "web") {
    return (
      <View className="bg-muted" style={styles.webGutter}>
        <View className="bg-background" style={styles.webColumn}>
          <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
            <View style={[styles.content, style]}>{children}</View>
          </SafeAreaView>
        </View>
      </View>
    );
  }

  return (
    <SafeAreaView className="bg-background" style={[styles.safeArea, style]} edges={["top", "left", "right"]}>
      <View style={styles.content}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: spacing.lg,
  },
  webGutter: {
    flex: 1,
    alignItems: "center",
    // @ts-expect-error -- web-only CSS property, harmless no-op on native
    minHeight: "100vh",
  },
  webColumn: {
    flex: 1,
    width: "100%",
    maxWidth: WEB_MAX_WIDTH,
    boxShadow: "0 0 60px rgba(0,0,0,0.08)",
  },
});
