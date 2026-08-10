import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError, authApi } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function ForgotPasswordScreen() {
  const { colors } = useTheme();
  const { t } = useLanguage();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.loginError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">{t("auth.forgotPasswordTitle")}</Text>
        <Text variant="body" style={styles.subtitle}>
          {t("auth.forgotPasswordSubtitle")}
        </Text>
      </View>

      <View>
        {sent ? (
          <Text variant="body" style={styles.sent}>
            {t("auth.forgotPasswordSent")}
          </Text>
        ) : (
          <TextField
            label={t("auth.email")}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
          />
        )}
        {error ? (
          <Text variant="caption" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        ) : null}
        {sent ? (
          <Button
            label={t("auth.resetPasswordTitle")}
            onPress={() => router.push("/(auth)/reset-password")}
            style={styles.submit}
          />
        ) : (
          <Button
            label={t("auth.forgotPasswordSubmit")}
            onPress={handleSubmit}
            loading={isSubmitting}
            disabled={!email}
            style={styles.submit}
          />
        )}
        <Button label={t("auth.backToLogin")} variant="ghost" onPress={() => router.back()} />
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
  sent: {
    marginBottom: spacing.md,
  },
  error: {
    marginTop: spacing.md,
  },
  submit: {
    marginTop: spacing.xl,
  },
});
