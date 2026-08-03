import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, type StyleProp, type ViewStyle } from "react-native";

import { radii } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";

/** Circular floating icon button — the back arrows, settings gears and
 * history clocks that sit in a soft-shadowed white pill throughout the
 * design (nav bars, subject headers, chat header). */
export function IconButton({
  name,
  onPress,
  size = 44,
  style,
}: {
  name: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  size?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          width: size,
          height: size,
          borderRadius: radii.full,
          backgroundColor: colors.surface,
          shadowColor: colors.shadow,
        },
        pressed && styles.pressed,
        style,
      ]}
    >
      <Ionicons name={name} size={Math.round(size * 0.4)} color={colors.textPrimary} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 1,
    shadowRadius: 16,
    elevation: 3,
  },
  pressed: {
    opacity: 0.85,
  },
});
