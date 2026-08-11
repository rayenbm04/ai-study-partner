import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, useColorScheme, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { TextField } from "../../components/ui/TextField";
import { ApiError, authApi } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";

export default function ResetPasswordScreen() {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
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
      <View className="mt-16 mb-10">
        <Text className="text-3xl font-bold">{t("auth.resetPasswordTitle")}</Text>
        <Text className="mt-2 text-muted-foreground">{t("auth.resetPasswordSubtitle")}</Text>
      </View>

      <View>
        {done ? (
          <Text className="mb-4">{t("auth.resetPasswordSuccess")}</Text>
        ) : (
          <>
            <TextField label={t("auth.resetCode")} value={token} onChangeText={setToken} autoCapitalize="none" />
            <TextField
              label={t("auth.newPassword")}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
              autoComplete="new-password"
              className="mt-4"
            />
            <TextField
              label={t("auth.confirmNewPassword")}
              value={confirmNewPassword}
              onChangeText={setConfirmNewPassword}
              secureTextEntry
              autoComplete="new-password"
              error={confirmNewPassword.length > 0 && !passwordsMatch ? t("auth.passwordMismatchError") : null}
              className="mt-4"
            />
          </>
        )}
        {error ? <Text className="mt-3 text-sm text-destructive">{error}</Text> : null}
        {done ? (
          <Button onPress={() => router.replace("/(auth)/login")} className="mt-6">
            <Text>{t("auth.backToLogin")}</Text>
          </Button>
        ) : (
          <Button onPress={handleSubmit} disabled={isSubmitting || !token || !newPassword || !confirmNewPassword} className="mt-6">
            {isSubmitting ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
            <Text>{t("auth.resetPasswordSubmit")}</Text>
          </Button>
        )}
      </View>
    </Screen>
  );
}
