/**
 * First-run setup: choose how to populate your subjects (a curriculum pack
 * vs. typing your own), then ask how much time you have to study daily.
 * Not a chat-guided flow (see design decision) — this maps directly onto
 * real backend calls rather than collecting "goal"/"level" answers the API
 * has nowhere to store.
 *
 * The pack path hands off to /subject-pack/new, which pushes on top of this
 * screen and, on success, replaces back here with a `packApplied` param —
 * read below to skip straight to the daily-minutes step instead of
 * re-showing the "pack vs manual" choice.
 *
 * The daily-minutes choice isn't persisted anywhere yet (there's no user
 * preferences endpoint on the backend) — it's carried forward as a param
 * into the Study Plan tab so it pre-fills the first plan-generation form
 * instead of being silently dropped. A real "default daily minutes" user
 * setting would be a small, separate backend addition later.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Card, ProgressBar, Screen, Text, TextField } from "../components/ui";
import { radii, spacing } from "../constants/theme";
import { ApiError, subjectsApi } from "../lib/api";
import { useLanguage } from "../lib/language-context";
import { useTheme } from "../lib/theme-context";

export default function OnboardingScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const { t } = useLanguage();
  const MINUTE_OPTIONS = [
    { minutes: 15, sub: t("onboarding.minutes15Sub") },
    { minutes: 30, sub: t("onboarding.minutes30Sub") },
    { minutes: 45, sub: t("onboarding.minutes45Sub") },
    { minutes: 60, sub: t("onboarding.minutes60Sub") },
  ];
  const { packApplied } = useLocalSearchParams<{ packApplied?: string }>();
  const [step, setStep] = useState<0 | 1 | 2>(packApplied ? 2 : 0);
  const [subjectName, setSubjectName] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState<number | null>(30);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (packApplied) setStep(2);
  }, [packApplied]);

  async function handleFinish() {
    setError(null);
    setIsSubmitting(true);
    try {
      // Only the "add my own" path collects a subject name — the pack path
      // (packApplied param) already created its subjects via /subject-packs/apply.
      if (subjectName.trim()) {
        await subjectsApi.createSubject({ name: subjectName.trim() });
      }
      router.replace({ pathname: "/(tabs)/study-plan", params: { defaultDailyMinutes: String(dailyMinutes) } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("onboarding.createSubjectError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.progress}>
        <ProgressBar total={3} completed={step + 1} />
      </View>

      {step === 0 ? (
        <View style={styles.body}>
          <View style={[styles.iconCircle, { backgroundColor: colors.primaryLight }]}>
            <Ionicons name="library" size={28} color={colors.accentDark} />
          </View>
          <Text variant="display">{t("onboarding.step0Title")}</Text>
          <Text variant="body" style={styles.subtitle}>
            {t("onboarding.step0Subtitle")}
          </Text>
          <View style={styles.options}>
            <Card
              onPress={() => router.push({ pathname: "/subject-pack/new", params: { returnTo: "/onboarding" } })}
              style={styles.choiceCard}
            >
              <Text variant="title">{t("onboarding.usePack")}</Text>
              <Text variant="caption">{t("onboarding.usePackHint")}</Text>
            </Card>
            <Card onPress={() => setStep(1)} style={styles.choiceCard}>
              <Text variant="title">{t("onboarding.addOwn")}</Text>
              <Text variant="caption">{t("onboarding.addOwnHint")}</Text>
            </Card>
          </View>
        </View>
      ) : step === 1 ? (
        <View style={styles.body}>
          <View style={[styles.iconCircle, { backgroundColor: colors.primaryLight }]}>
            <Ionicons name="school" size={28} color={colors.accentDark} />
          </View>
          <Text variant="display">{t("onboarding.step1Title")}</Text>
          <Text variant="body" style={styles.subtitle}>
            {t("onboarding.step1Subtitle")}
          </Text>
          <TextField
            label={t("onboarding.subjectNameLabel")}
            placeholder={t("onboarding.subjectNamePlaceholder")}
            value={subjectName}
            onChangeText={setSubjectName}
            style={styles.field}
          />
          {error ? (
            <Text variant="caption" style={[styles.error, { color: colors.error }]}>
              {error}
            </Text>
          ) : null}
          <Button
            label={t("onboarding.continue")}
            onPress={() => setStep(2)}
            disabled={!subjectName.trim()}
            style={styles.action}
          />
        </View>
      ) : (
        <View style={styles.body}>
          <Text variant="display">{t("onboarding.step2Title")}</Text>
          <Text variant="body" style={styles.subtitle}>
            {t("onboarding.step2Subtitle")}
          </Text>
          <View style={styles.options}>
            {MINUTE_OPTIONS.map(({ minutes, sub }) => {
              const selected = dailyMinutes === minutes;
              return (
                <Card
                  key={minutes}
                  onPress={() => setDailyMinutes(minutes)}
                  style={[
                    styles.option,
                    selected && { backgroundColor: colors.primary },
                  ]}
                >
                  <Text variant="title" style={selected ? { color: colors.textOnPrimary } : undefined}>
                    {t("common.minutes", { minutes })}
                  </Text>
                  <Text variant="caption" style={selected ? { color: colors.textOnPrimary, opacity: 0.75 } : undefined}>
                    {sub}
                  </Text>
                </Card>
              );
            })}
          </View>
          {error ? (
            <Text variant="caption" style={[styles.error, { color: colors.error }]}>
              {error}
            </Text>
          ) : null}
          <Button label={t("onboarding.getStarted")} onPress={handleFinish} loading={isSubmitting} style={styles.action} />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  progress: {
    marginTop: spacing.lg,
  },
  body: {
    marginTop: spacing.xxl,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  subtitle: {
    marginTop: spacing.sm,
    marginBottom: spacing.xl,
  },
  field: {
    marginBottom: spacing.lg,
  },
  options: {
    gap: spacing.md,
  },
  option: {
    width: "100%",
  },
  choiceCard: {
    width: "100%",
  },
  action: {
    marginTop: spacing.xl,
  },
  error: {
    marginBottom: spacing.md,
  },
});
