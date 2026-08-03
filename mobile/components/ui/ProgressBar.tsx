import { StyleSheet, View } from "react-native";

import { radii } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";

/** A row of segments (one per quiz question, one per plan day, etc.) rather
 * than a single continuous bar — matches the step-by-step exercise pattern
 * from the Brilliant reference screens, and reads more clearly as "3 of 8
 * done" than a plain percentage fill would. */
export function ProgressBar({ total, completed }: { total: number; completed: number }) {
  const { colors } = useTheme();
  return (
    <View style={styles.row}>
      {Array.from({ length: total }).map((_, index) => (
        <View
          key={index}
          style={[styles.segment, { backgroundColor: index < completed ? colors.accent : colors.border }]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    gap: 4,
  },
  segment: {
    flex: 1,
    height: 6,
    borderRadius: radii.full,
  },
});
