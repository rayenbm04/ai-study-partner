import type { Icon as PhosphorIcon } from "phosphor-react-native";
import { Pressable, type StyleProp, type ViewStyle } from "react-native";

import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

/** Circular floating icon button — the back arrows, settings gears and
 * history clocks that sit in a soft-shadowed pill throughout the design
 * (nav bars, subject headers, chat header). */
export function IconButton({
  icon: Icon,
  onPress,
  size = 44,
  style,
  className,
}: {
  icon: PhosphorIcon;
  onPress: () => void;
  size?: number;
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  return (
    <Pressable
      onPress={onPress}
      className={cn("items-center justify-center rounded-full bg-card shadow-sm shadow-black/10 active:opacity-85", className)}
      style={[{ width: size, height: size }, style]}
    >
      <Icon size={Math.round(size * 0.4)} color={scheme.foreground} />
    </Pressable>
  );
}
