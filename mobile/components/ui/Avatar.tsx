import { StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";

import { fontFamilies, radii } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";
import { Text } from "./Text";

/** Circular tint-background initial badge — used for the user's initial and
 * for each subject's leading dot on the home/subjects list. */
export function Avatar({ label, size = 46, style }: { label: string; size?: number; style?: StyleProp<ViewStyle> }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.base,
        { width: size, height: size, borderRadius: radii.full, backgroundColor: colors.primaryLight },
        style,
      ]}
    >
      <Text style={{ fontFamily: fontFamilies.display, fontSize: size * 0.38, color: colors.accentDark }}>
        {label.slice(0, 1).toUpperCase()}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
  },
});
