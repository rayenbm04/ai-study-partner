import type { ReactNode } from "react";
import { Pressable, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";

import { radii, spacing } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";

export function Card({
  children,
  onPress,
  style,
}: {
  children: ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          shadowColor: colors.shadow,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
  if (!onPress) return content;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [pressed && styles.pressed]}>
      {content}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radii.xl,
    padding: spacing.lg,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 1,
    shadowRadius: 24,
    elevation: 3,
  },
  pressed: {
    opacity: 0.9,
    transform: [{ scale: 0.995 }],
  },
});
