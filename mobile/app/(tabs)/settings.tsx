import { useRouter } from "expo-router";
import { useState } from "react";
import { Switch, StyleSheet, View } from "react-native";

import { Avatar, Button, Card, Screen, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { accountApi } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { confirmDestructiveAction } from "../../lib/confirm";
import { useTheme } from "../../lib/theme-context";

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { colors, isDark, setDark } = useTheme();
  const router = useRouter();
  const [isResetting, setIsResetting] = useState(false);

  async function handleResetAccount() {
    const confirmed = await confirmDestructiveAction(
      "Reset your account?",
      "This permanently deletes every subject, document, quiz, flashcard, and progress record. Your login stays active. This can't be undone.",
      "Reset"
    );
    if (!confirmed) return;
    setIsResetting(true);
    try {
      await accountApi.resetAccount();
      router.replace("/(tabs)");
    } finally {
      setIsResetting(false);
    }
  }

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

      <Text variant="label" style={[styles.sectionLabel, { color: colors.error }]}>
        Danger zone
      </Text>
      <Card>
        <Text variant="body" style={{ color: colors.textSecondary, marginBottom: spacing.md }}>
          Permanently delete every subject, document, quiz, flashcard, and progress record. Your
          login stays active.
        </Text>
        <Button label="Reset account" variant="secondary" onPress={handleResetAccount} loading={isResetting} />
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
