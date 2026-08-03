import { Switch, StyleSheet, View } from "react-native";

import { Avatar, Button, Card, Screen, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { useAuth } from "../../lib/auth-context";
import { useTheme } from "../../lib/theme-context";

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { colors, isDark, setDark } = useTheme();

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Settings</Text>
      </View>

      <Card style={styles.profileCard}>
        <Avatar label={user?.firstname ?? "?"} size={56} />
        <View style={styles.profileText}>
          <Text variant="subtitle">
            {user?.firstname} {user?.lastname}
          </Text>
          <Text variant="caption" style={{ marginTop: 4 }}>
            {user?.email}
          </Text>
        </View>
      </Card>

      <Text variant="label" style={styles.sectionLabel}>
        Appearance
      </Text>
      <Card style={styles.rowsCard}>
        <View style={styles.row}>
          <Text variant="body" style={styles.rowLabel}>
            Dark mode
          </Text>
          <Switch
            value={isDark}
            onValueChange={setDark}
            trackColor={{ false: colors.border, true: colors.accent }}
            thumbColor="#FFFFFF"
          />
        </View>
      </Card>

      <Button label="Sign out" variant="secondary" onPress={logout} style={styles.signOut} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  profileCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  profileText: {
    flex: 1,
  },
  sectionLabel: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    marginLeft: spacing.sm,
  },
  rowsCard: {
    padding: 0,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rowLabel: {
    flex: 1,
  },
  signOut: {
    marginTop: "auto",
    marginBottom: 110,
  },
});
