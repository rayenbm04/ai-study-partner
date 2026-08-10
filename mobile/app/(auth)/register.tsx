import { useRouter } from "expo-router";
import { useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import { Button, DatePickerField, Screen, SchoolPickerField, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError } from "../../lib/api";
import type { School } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

// Mirrors the backend's RegisterRequest pseudo pattern (app/api/v1/schemas/auth.py):
// no whitespace, no '@', 3-50 chars.
const PSEUDO_PATTERN = /^[^\s@]{3,50}$/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function isValidDateOfBirth(value: string): boolean {
  if (!DATE_PATTERN.test(value)) return false;
  const parsed = new Date(value + "T00:00:00Z");
  if (Number.isNaN(parsed.getTime())) return false;
  const today = new Date();
  if (parsed.getTime() > today.getTime()) return false;
  const ageYears = (today.getTime() - parsed.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
  return ageYears >= 3 && ageYears <= 120;
}

export default function RegisterScreen() {
  const { register } = useAuth();
  const { colors } = useTheme();
  const { t } = useLanguage();
  const router = useRouter();
  const [firstname, setFirstname] = useState("");
  const [lastname, setLastname] = useState("");
  const [email, setEmail] = useState("");
  const [pseudo, setPseudo] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [school, setSchool] = useState<School | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const pseudoValid = PSEUDO_PATTERN.test(pseudo.trim());
  const dateOfBirthValid = isValidDateOfBirth(dateOfBirth.trim());
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  // Deliberately loose: only checks fields are filled in, not that they're
  // valid. The button used to stay disabled (and silently unclickable) the
  // moment e.g. autofill dropped an email into the pseudo field — the user
  // had no way to find out why. Pressing now always runs handleSubmit, which
  // reports the *specific* problem instead of just refusing to respond.
  const canSubmit =
    !!firstname &&
    !!lastname &&
    !!email &&
    !!pseudo &&
    !!dateOfBirth &&
    password.length > 0 &&
    !!confirmPassword;

  async function handleSubmit() {
    setError(null);
    if (!pseudoValid) {
      setError(t("auth.pseudoError"));
      return;
    }
    if (!dateOfBirthValid) {
      setError(t("auth.dateOfBirthError"));
      return;
    }
    if (password.length < 8) {
      setError(t("auth.passwordTooShortError"));
      return;
    }
    if (!passwordsMatch) {
      setError(t("auth.passwordMismatchError"));
      return;
    }
    setIsSubmitting(true);
    try {
      await register({
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
        firstname: firstname.trim(),
        lastname: lastname.trim(),
        pseudo: pseudo.trim(),
        date_of_birth: dateOfBirth.trim(),
        school_id: school?.id ?? null,
      });
      // First-time users go through the short setup flow (first subject +
      // daily study time) before landing on the tabs; returning users
      // (login.tsx) skip straight there.
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.registerError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Text variant="display">{t("auth.registerTitle")}</Text>
        <Text variant="body" style={styles.subtitle}>
          {t("auth.registerSubtitle")}
        </Text>
      </View>

      <View>
        <View style={styles.row}>
          <TextField label={t("auth.firstName")} value={firstname} onChangeText={setFirstname} style={styles.rowField} />
          <TextField label={t("auth.lastName")} value={lastname} onChangeText={setLastname} style={styles.rowField} />
        </View>
        <TextField
          label={t("auth.email")}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
          style={styles.field}
        />
        <TextField
          label={t("auth.pseudo")}
          value={pseudo}
          onChangeText={setPseudo}
          autoCapitalize="none"
          autoComplete="username"
          error={pseudo.length > 0 && !pseudoValid ? t("auth.pseudoError") : null}
          style={styles.field}
        />
        {!(pseudo.length > 0 && !pseudoValid) ? (
          <Text variant="caption" style={styles.hint}>
            {t("auth.pseudoHint")}
          </Text>
        ) : null}
        <DatePickerField
          label={t("auth.dateOfBirth")}
          value={dateOfBirth}
          onChange={setDateOfBirth}
          placeholder={t("auth.dateOfBirthPlaceholder")}
          error={dateOfBirth.length > 0 && !dateOfBirthValid ? t("auth.dateOfBirthError") : null}
          style={styles.field}
        />
        <SchoolPickerField
          label={t("auth.schoolName")}
          value={school}
          onChange={setSchool}
          placeholder={t("auth.schoolName")}
          style={styles.field}
        />
        <TextField
          label={t("auth.password")}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="new-password"
          style={styles.field}
        />
        <Text variant="caption" style={styles.hint}>
          {t("auth.passwordHint")}
        </Text>
        <TextField
          label={t("auth.confirmPassword")}
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
          autoComplete="new-password"
          error={confirmPassword.length > 0 && !passwordsMatch ? t("auth.passwordMismatchError") : null}
          style={styles.field}
        />
        {error ? (
          <Text variant="caption" style={[styles.error, { color: colors.error }]}>
            {error}
          </Text>
        ) : null}
        <Button
          label={t("auth.createAccountSubmit")}
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={!canSubmit}
          style={styles.submit}
        />
        <Button label={t("auth.haveAccount")} variant="ghost" onPress={() => router.back()} />
      </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: spacing.xxxl,
  },
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
    marginLeft: spacing.sm,
  },
  error: {
    marginTop: spacing.md,
  },
  submit: {
    marginTop: spacing.xl,
  },
});
