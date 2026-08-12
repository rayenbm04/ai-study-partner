import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { TextField } from "../../components/ui/TextField";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";

export default function LoginScreen() {
  const { login } = useAuth();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
      if (err instanceof ApiError && err.status === 423) {
        setError(t("auth.accountLockedError"));
      } else {
        setError(err instanceof ApiError ? err.message : t("auth.loginError"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View className="mt-16 mb-10">
        <Text className="text-3xl font-bold">{t("auth.loginTitle")}</Text>
        <Text className="mt-2 text-muted-foreground">{t("auth.loginSubtitle")}</Text>
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
          className="mt-4"
        />
        {error ? <Text className="mt-3 text-sm text-destructive">{error}</Text> : null}
        <Button onPress={handleSubmit} disabled={isSubmitting || !email || !password} className="mt-6">
          {isSubmitting ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
          <Text>{t("auth.signIn")}</Text>
        </Button>
        <Button variant="ghost" onPress={() => router.push("/(auth)/register")}>
          <Text>{t("auth.createAccount")}</Text>
        </Button>
        <Button variant="ghost" onPress={() => router.push("/(auth)/forgot-password")}>
          <Text>{t("auth.forgotPasswordLink")}</Text>
        </Button>
      </View>
    </Screen>
  );
}
