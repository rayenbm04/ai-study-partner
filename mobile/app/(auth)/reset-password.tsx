import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError, authApi } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function ResetPasswordScreen() {
  const { colors } = useTheme();
  const { t } = useLanguage();
  const router = useRouter();
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const passwordsMatch = newPassword.length > 0 && newPassword === confirmNewPassword;

  async function handleSubmit() {
    setError(null);
    if (newPassword.length < 8) {
      setError(t("auth.passwordTooShortError"));
      return;
    }
    if (!passwordsMatch) {
      setError(t("auth.passwordMismatchError"));
      return;
    }
    setIsSubmitting(true);
    try {
      await authApi.resetPassword({
        token: token.trim(),
        new_password: newPassword,
        confirm_new_password: confirmNewPassword,
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.loginError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">{t("auth.resetPasswordTitle")}</Text>
        <Text variant="body" style={styles.subtitle}>
          {t("auth.resetPasswordSubtitle")}
        </Text>
      </View>

      <View>
        {done ? (
          <Text variant="body" style={styles.sent}>
            {t("auth.resetPasswordSuccess")}
          </Text>
        ) : (
          <>
            <TextField label={t("auth.resetCode")} value={token} onChangeText={setToken} autoCapitalize="none" />
            <TextField
              label={t("auth.newPassword")}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
              autoComplete="new-password"
              style={styles.field}
            />
            <TextField
              label={t("auth.confirmNewPassword")}
              value={confirmNewPassword}
              onChangeText={setConfirmNewPassword}
              secureTextEntry
              autoComplete="new-password"
              error={confirmNewPassword.length > 0 && !passwordsMatch ? t("auth.passwordMismatchError") : null}
              style={styles.field}
            />
          </>
        )}
        {error ? (
          <Text variant="caption" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        ) : null}
        {done ? (
          <Button label={t("auth.backToLogin")} onPress={() => router.replace("/(auth)/login")} style={styles.submit} />
        ) : (
          <Button
            label={t("auth.resetPasswordSubmit")}
            onPress={handleSubmit}
            loading={isSubmitting}
            disabled={!token || !newPassword || !confirmNewPassword}
            style={styles.submit}
          />
        )}
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
  field: {
    marginTop: spacing.lg,
  },
  error: {
    marginTop: spacing.md,
  },
  submit: {
    marginTop: spacing.xl,
  },
});
