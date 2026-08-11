/**
 * Floating pill nav bar — the mockup's bottom nav is a single rounded bar
 * hovering above the content (position:absolute, radius:999, blurred
 * surface) rather than a full-width bar docked to the screen edge. expo-blur
 * isn't a dependency here, so the "glass" look is approximated with a
 * semi-opaque themed surface instead of a real backdrop blur.
 */
import { Ionicons } from "@expo/vector-icons";
import type { BottomTabBarProps } from "expo-router/build/react-navigation/bottom-tabs";
import { Platform, Pressable, useColorScheme, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { THEME } from "../lib/theme";
import { cn } from "../lib/utils";
import { Text } from "./ui/text";

const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  index: "home",
  cards: "albums",
  "study-plan": "calendar",
  progress: "stats-chart",
  settings: "settings",
};

export function AppTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const isDark = useColorScheme() === "dark";
  const scheme = isDark ? THEME.dark : THEME.light;
  const insets = useSafeAreaInsets();

  return (
    <View
      className={cn("absolute right-4 left-4", Platform.OS === "web" && "right-0 left-0 mx-auto w-112")}
      style={{ bottom: Math.max(insets.bottom, 12) + 8 }}
      pointerEvents="box-none"
    >
      <View
        className="h-17.5 flex-row items-center rounded-full px-2 shadow-xl shadow-black/20"
        style={{ backgroundColor: isDark ? "rgba(28,25,31,0.92)" : "rgba(255,255,255,0.92)" }}
      >
        {state.routes.map((route, index) => {
          const { options } = descriptors[route.key];
          const label = (options.title ?? route.name) as string;
          const isFocused = state.index === index;
          const icon = ICONS[route.name] ?? "ellipse";

          const onPress = () => {
            const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
            if (!isFocused && !event.defaultPrevented) navigation.navigate(route.name);
          };

          return (
            <Pressable key={route.key} onPress={onPress} className="h-full flex-1 items-center justify-center gap-1">
              {isFocused ? <View className="absolute top-1.5 right-2.5 bottom-1.5 left-2.5 rounded-full bg-primary/15" /> : null}
              <Ionicons
                name={isFocused ? icon : (`${icon}-outline` as keyof typeof Ionicons.glyphMap)}
                size={20}
                color={isFocused ? scheme.primary : scheme.mutedForeground}
                className="z-10"
              />
              <Text className="z-10 text-[11px] font-semibold" style={{ color: isFocused ? scheme.primary : scheme.mutedForeground }}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
