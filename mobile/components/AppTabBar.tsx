/**
 * Floating pill nav bar — the mockup's bottom nav is a single rounded bar
 * hovering above the content (position:absolute, radius:999, blurred
 * surface) rather than a full-width bar docked to the screen edge. expo-blur
 * isn't a dependency here, so the "glass" look is approximated with a
 * semi-opaque themed surface instead of a real backdrop blur.
 */
import { Ionicons } from "@expo/vector-icons";
import type { BottomTabBarProps } from "expo-router/build/react-navigation/bottom-tabs";
import { Platform, Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fontFamilies, fontSizes, radii } from "../constants/theme";
import { useTheme } from "../lib/theme-context";
import { Text } from "./ui";

const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  index: "home",
  cards: "albums",
  "study-plan": "calendar",
  progress: "stats-chart",
  settings: "settings",
};

export function AppTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.wrap,
        { bottom: Math.max(insets.bottom, 12) + 8 },
        Platform.OS === "web" && styles.wrapWeb,
      ]}
      pointerEvents="box-none"
    >
      <View
        style={[
          styles.bar,
          {
            backgroundColor: isDark ? "rgba(34,31,28,0.92)" : "rgba(255,255,255,0.92)",
            shadowColor: colors.shadowStrong,
          },
        ]}
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
            <Pressable key={route.key} onPress={onPress} style={styles.tab}>
              {isFocused ? <View style={[styles.pill, { backgroundColor: colors.primaryLight }]} /> : null}
              <Ionicons
                name={isFocused ? icon : (`${icon}-outline` as keyof typeof Ionicons.glyphMap)}
                size={20}
                color={isFocused ? colors.accentDark : colors.textMuted}
                style={styles.icon}
              />
              <Text
                style={[
                  styles.label,
                  { color: isFocused ? colors.accentDark : colors.textMuted },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 16,
    right: 16,
  },
  // Matches Screen's WEB_MAX_WIDTH (480) minus its 16px side margins — the
  // tab bar floats over the whole browser viewport (it's rendered by the
  // Tabs navigator, outside any single screen's centered column), so it
  // needs its own centering to line up with the content underneath it.
  //
  // `alignSelf: "center"` does NOT center an absolutely-positioned element —
  // that's a flex-participation property and this element has been taken
  // out of flex flow, so it was a no-op and the bar just hugged the left
  // edge of the full browser width. left:0 + right:0 + a fixed (not "100%")
  // width + auto horizontal margins is the actual CSS trick for centering
  // an absolutely-positioned box.
  wrapWeb: {
    left: 0,
    right: 0,
    width: 448,
    marginHorizontal: "auto",
  },
  bar: {
    flexDirection: "row",
    alignItems: "center",
    height: 70,
    borderRadius: radii.full,
    paddingHorizontal: 8,
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 1,
    shadowRadius: 32,
    elevation: 6,
  },
  tab: {
    flex: 1,
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
  },
  pill: {
    position: "absolute",
    top: 6,
    bottom: 6,
    left: 10,
    right: 10,
    borderRadius: radii.full,
  },
  icon: {
    zIndex: 1,
  },
  label: {
    fontFamily: fontFamilies.semibold,
    fontSize: fontSizes.xs - 1,
    zIndex: 1,
  },
});
