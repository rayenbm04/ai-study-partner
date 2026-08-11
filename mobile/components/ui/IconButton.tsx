import { Ionicons } from "@expo/vector-icons";
import { Pressable, useColorScheme, type StyleProp, type ViewStyle } from "react-native";

import { THEME } from "../../lib/theme";
import { cn } from "../../lib/utils";

/** Circular floating icon button — the back arrows, settings gears and
 * history clocks that sit in a soft-shadowed pill throughout the design
 * (nav bars, subject headers, chat header). */
export function IconButton({
  name,
  onPress,
  size = 44,
  style,
  className,
}: {
  name: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  size?: number;
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  return (
    <Pressable
      onPress={onPress}
      className={cn("items-center justify-center rounded-full bg-card shadow-sm shadow-black/10 active:opacity-85", className)}
      style={[{ width: size, height: size }, style]}
    >
      <Ionicons name={name} size={Math.round(size * 0.4)} color={scheme.foreground} />
    </Pressable>
  );
}
