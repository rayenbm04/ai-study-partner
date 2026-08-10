import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function LoginScreen() {
  const { login } = useAuth();
  const { colors } = useTheme();
  const { t } = useLanguage();
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
      setError(err instanceof ApiError ? err.message : t("auth.loginError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">{t("auth.loginTitle")}</Text>
        <Text variant="body" style={styles.subtitle}>
          {t("auth.loginSubtitle")}
        </Text>
      </View>

      <View>
        <TextField
          label={t("auth.email")}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
        />
        <TextField
          label={t("auth.password")}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="password"
          style={styles.field}
        />
        {error ? (
          <Text variant="caption" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        ) : null}
        <Button
          label={t("auth.signIn")}
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={!email || !password}
          style={styles.submit}
        />
        <Button label={t("auth.createAccount")} variant="ghost" onPress={() => router.push("/(auth)/register")} />
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
