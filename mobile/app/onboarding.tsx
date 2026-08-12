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
import { BooksIcon, GraduationCapIcon } from "phosphor-react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, View } from "react-native";

import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { ProgressBar } from "../components/ui/ProgressBar";
import { Screen } from "../components/ui/Screen";
import { Text } from "../components/ui/text";
import { TextField } from "../components/ui/TextField";
import { ApiError, subjectsApi } from "../lib/api";
import { useLanguage } from "../lib/language-context";
import { THEME } from "../lib/theme";
import { useTheme } from "../lib/theme-context";
import { cn } from "../lib/utils";

export default function OnboardingScreen() {
  const router = useRouter();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
      <View className="mt-6">
        <ProgressBar total={3} completed={step + 1} />
      </View>

      {step === 0 ? (
        <View className="mt-10">
          <View className="mb-6 size-16 items-center justify-center rounded-full bg-primary/15">
            <BooksIcon size={28} color={scheme.primary} weight="fill" />
          </View>
          <Text className="text-3xl font-bold">{t("onboarding.step0Title")}</Text>
          <Text className="mt-2 mb-8 text-muted-foreground">{t("onboarding.step0Subtitle")}</Text>
          <View className="gap-4">
            <Pressable onPress={() => router.push({ pathname: "/subject-pack/new", params: { returnTo: "/onboarding" } })}>
              <Card>
                <CardContent>
                  <Text className="text-lg font-semibold">{t("onboarding.usePack")}</Text>
                  <Text className="mt-1 text-xs text-muted-foreground">{t("onboarding.usePackHint")}</Text>
                </CardContent>
              </Card>
            </Pressable>
            <Pressable onPress={() => setStep(1)}>
              <Card>
                <CardContent>
                  <Text className="text-lg font-semibold">{t("onboarding.addOwn")}</Text>
                  <Text className="mt-1 text-xs text-muted-foreground">{t("onboarding.addOwnHint")}</Text>
                </CardContent>
              </Card>
            </Pressable>
          </View>
        </View>
      ) : step === 1 ? (
        <View className="mt-10">
          <View className="mb-6 size-16 items-center justify-center rounded-full bg-primary/15">
            <GraduationCapIcon size={28} color={scheme.primary} weight="fill" />
          </View>
          <Text className="text-3xl font-bold">{t("onboarding.step1Title")}</Text>
          <Text className="mt-2 mb-8 text-muted-foreground">{t("onboarding.step1Subtitle")}</Text>
          <TextField
            label={t("onboarding.subjectNameLabel")}
            placeholder={t("onboarding.subjectNamePlaceholder")}
            value={subjectName}
            onChangeText={setSubjectName}
            className="mb-6"
          />
          {error ? <Text className="mb-4 text-sm text-destructive">{error}</Text> : null}
          <Button onPress={() => setStep(2)} disabled={!subjectName.trim()} className="mt-6">
            <Text>{t("onboarding.continue")}</Text>
          </Button>
        </View>
      ) : (
        <View className="mt-10">
          <Text className="text-3xl font-bold">{t("onboarding.step2Title")}</Text>
          <Text className="mt-2 mb-8 text-muted-foreground">{t("onboarding.step2Subtitle")}</Text>
          <View className="gap-4">
            {MINUTE_OPTIONS.map(({ minutes, sub }) => {
              const selected = dailyMinutes === minutes;
              return (
                <Pressable key={minutes} onPress={() => setDailyMinutes(minutes)}>
                  <Card className={cn(selected && "bg-primary")}>
                    <CardContent>
                      <Text className={cn("text-lg font-semibold", selected && "text-primary-foreground")}>
                        {t("common.minutes", { minutes })}
                      </Text>
                      <Text className={cn("mt-1 text-xs text-muted-foreground", selected && "text-primary-foreground/75")}>
                        {sub}
                      </Text>
                    </CardContent>
                  </Card>
                </Pressable>
              );
            })}
          </View>
          {error ? <Text className="mt-4 text-sm text-destructive">{error}</Text> : null}
          <Button onPress={handleFinish} disabled={isSubmitting} className="mt-6">
            {isSubmitting ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
            <Text>{t("onboarding.getStarted")}</Text>
          </Button>
        </View>
      )}
    </Screen>
  );
}
