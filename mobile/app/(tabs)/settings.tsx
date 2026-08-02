import { StyleSheet, View } from "react-native";

import { Button, Card, Screen, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { useAuth } from "../../lib/auth-context";

export default function SettingsScreen() {
  const { user, logout } = useAuth();

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Settings</Text>
      </View>

      <Card style={styles.card}>
        <Text variant="title">
          {user?.firstname} {user?.lastname}
        </Text>
        <Text variant="caption">{user?.email}</Text>
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
  card: {
    marginBottom: spacing.xl,
  },
  signOut: {
    marginTop: "auto",
    marginBottom: spacing.lg,
  },
});
