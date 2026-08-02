import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, spacing } from "../../constants/theme";

/** Standard screen wrapper — safe-area aware, themed background, consistent
 * horizontal padding so individual screens don't each reinvent it. */
export function Screen({ children, scroll: _scroll, style }: { children: ReactNode; scroll?: boolean; style?: object }) {
  return (
    <SafeAreaView style={[styles.safeArea, style]} edges={["top", "left", "right"]}>
      <View style={styles.content}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    paddingHorizontal: spacing.lg,
  },
});
