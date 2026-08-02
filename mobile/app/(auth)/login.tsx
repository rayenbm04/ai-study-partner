import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";

export default function LoginScreen() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      // AuthGate in the root layout handles the redirect to (tabs) once
      // `user` updates — no explicit router.replace needed here.
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't sign in. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Welcome back</Text>
        <Text variant="body" style={styles.subtitle}>
          Sign in to pick up where you left off.
        </Text>
      </View>

      <View style={styles.form}>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
        />
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="password"
          style={styles.field}
        />
        {error ? (
          <Text variant="caption" style={styles.error}>
            {error}
          </Text>
        ) : null}
        <Button
          label="Sign in"
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={!email || !password}
          style={styles.submit}
        />
        <Button label="Create an account" variant="ghost" onPress={() => router.push("/(auth)/register")} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.xxxl,
    marginBottom: spacing.xxl,
  },
  subtitle: {
    marginTop: spacing.sm,
  },
  form: {
    gap: 0,
  },
  field: {
    marginTop: spacing.lg,
  },
  submit: {
    marginTop: spacing.xl,
  },
  error: {
    marginTop: spacing.md,
  },
});
