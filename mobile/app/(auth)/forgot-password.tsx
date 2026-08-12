import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { TextField } from "../../components/ui/TextField";
import { ApiError, authApi } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";

export default function ForgotPasswordScreen() {
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
      <View className="mt-16 mb-10">
        <Text className="text-3xl font-bold">{t("auth.forgotPasswordTitle")}</Text>
        <Text className="mt-2 text-muted-foreground">{t("auth.forgotPasswordSubtitle")}</Text>
      </View>

      <View>
        {sent ? (
          <Text className="mb-4">{t("auth.forgotPasswordSent")}</Text>
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
        {error ? <Text className="mt-3 text-sm text-destructive">{error}</Text> : null}
        {sent ? (
          <Button onPress={() => router.push("/(auth)/reset-password")} className="mt-6">
            <Text>{t("auth.resetPasswordTitle")}</Text>
          </Button>
        ) : (
          <Button onPress={handleSubmit} disabled={isSubmitting || !email} className="mt-6">
            {isSubmitting ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
            <Text>{t("auth.forgotPasswordSubmit")}</Text>
          </Button>
        )}
        <Button variant="ghost" onPress={() => router.back()}>
          <Text>{t("auth.backToLogin")}</Text>
        </Button>
      </View>
    </Screen>
  );
}
