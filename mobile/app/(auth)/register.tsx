import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";

export default function RegisterScreen() {
  const { register } = useAuth();
  const router = useRouter();
  const [firstname, setFirstname] = useState("");
  const [lastname, setLastname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = firstname && lastname && email && password.length >= 8;

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await register({ email: email.trim(), password, firstname: firstname.trim(), lastname: lastname.trim() });
      // First-time users go through the short setup flow (first subject +
      // daily study time) before landing on the tabs; returning users
      // (login.tsx) skip straight there.
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create your account. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Create your account</Text>
        <Text variant="body" style={styles.subtitle}>
          A few seconds, then straight into your first subject.
        </Text>
      </View>

      <View>
        <View style={styles.row}>
          <TextField label="First name" value={firstname} onChangeText={setFirstname} style={styles.rowField} />
          <TextField label="Last name" value={lastname} onChangeText={setLastname} style={styles.rowField} />
        </View>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
          style={styles.field}
        />
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
          style={styles.field}
        />
        <Text variant="caption" style={styles.hint}>
          At least 8 characters.
        </Text>
        {error ? (
          <Text variant="caption" style={styles.error}>
            {error}
          </Text>
        ) : null}
        <Button
          label="Create account"
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={!canSubmit}
          style={styles.submit}
        />
        <Button label="I already have an account" variant="ghost" onPress={() => router.back()} />
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
  row: {
    flexDirection: "row",
    gap: spacing.md,
  },
  rowField: {
    flex: 1,
  },
  field: {
    marginTop: spacing.lg,
  },
  hint: {
    marginTop: spacing.xs,
  },
  error: {
    marginTop: spacing.md,
  },
  submit: {
    marginTop: spacing.xl,
  },
});
