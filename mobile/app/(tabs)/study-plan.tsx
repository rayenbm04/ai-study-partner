/**
 * Study Plan tab — generate a plan across selected subjects and view the
 * result. There's no "list my study plans" endpoint on the backend yet
 * (the architecture doc's Planning Engine contract only specifies
 * generate/get-one/update-item), so a generated plan is only kept in this
 * screen's local state — it won't still be here after an app restart.
 * Adding a `GET /study-plans` (list mine) endpoint is the natural backend
 * follow-up to make this persist properly.
 */
import { useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, FlatList, Pressable, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Screen } from "../../components/ui/Screen";
import { Tag } from "../../components/ui/Tag";
import { Text } from "../../components/ui/text";
import { ApiError, studyPlansApi, subjectsApi } from "../../lib/api";
import type { StudyPlan, Subject } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

const MINUTE_OPTIONS = [15, 30, 45, 60];

export default function StudyPlanScreen() {
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  const { t, tn } = useLanguage();
  const params = useLocalSearchParams<{ defaultDailyMinutes?: string }>();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectIds, setSelectedSubjectIds] = useState<string[]>([]);
  const [dailyMinutes, setDailyMinutes] = useState(
    params.defaultDailyMinutes ? Number(params.defaultDailyMinutes) : 30
  );
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  useFocusEffect(
    useCallback(() => {
      subjectsApi.listSubjects().then(setSubjects);
    }, [])
  );

  function toggleSubject(id: string) {
    setSelectedSubjectIds((current) =>
      current.includes(id) ? current.filter((s) => s !== id) : [...current, id]
    );
  }

  async function handleGenerate() {
    setError(null);
    setIsGenerating(true);
    try {
      const newPlan = await studyPlansApi.generateStudyPlan({
        name: "My study plan",
        subject_ids: selectedSubjectIds,
        daily_minutes_available: dailyMinutes,
      });
      setPlan(newPlan);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("studyPlan.generateError"));
    } finally {
      setIsGenerating(false);
    }
  }

  if (plan) {
    return (
      <Screen>
        <View className="mt-6 mb-6">
          <Text className="text-3xl font-bold">{plan.name}</Text>
          <Text className="mt-1 text-muted-foreground">{tn("studyPlan.sessionsScheduled", plan.items.length)}</Text>
        </View>
        <FlatList
          data={plan.items}
          keyExtractor={(item) => item.id}
          contentContainerClassName="gap-3 pb-32"
          renderItem={({ item }) => (
            <Card>
              <CardContent className="gap-1">
                <View className="flex-row items-center justify-between">
                  <Text className="text-sm font-medium text-muted-foreground">{item.scheduled_date}</Text>
                  <Tag label={t(`activityType.${item.activity_type}`)} tone="accent" />
                </View>
                <Text>{t("common.minutes", { minutes: item.duration_minutes })}</Text>
              </CardContent>
            </Card>
          )}
        />
        <Button variant="secondary" onPress={() => setPlan(null)} className="mb-28">
          <Text>{t("studyPlan.generateNewPlan")}</Text>
        </Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <View className="mt-6 mb-6">
        <Text className="text-3xl font-bold">{t("studyPlan.title")}</Text>
        <Text className="mt-1 text-muted-foreground">{t("studyPlan.subtitle")}</Text>
      </View>

      <Text className="mt-6 mb-2 text-sm font-medium text-muted-foreground">{t("common.subjects")}</Text>
      <View className="flex-row flex-wrap gap-2">
        {subjects.map((subject) => {
          const selected = selectedSubjectIds.includes(subject.id);
          return (
            <Pressable
              key={subject.id}
              onPress={() => toggleSubject(subject.id)}
              className={cn(
                "rounded-full px-5 py-3 shadow-sm shadow-black/5",
                selected ? "bg-primary" : "bg-card"
              )}
            >
              <Text className={selected ? "text-primary-foreground" : "text-foreground"}>{subject.name}</Text>
            </Pressable>
          );
        })}
      </View>

      <Text className="mt-6 mb-2 text-sm font-medium text-muted-foreground">{t("studyPlan.dailyStudyTime")}</Text>
      <View className="flex-row flex-wrap gap-2">
        {MINUTE_OPTIONS.map((minutes) => {
          const selected = dailyMinutes === minutes;
          return (
            <Pressable
              key={minutes}
              onPress={() => setDailyMinutes(minutes)}
              className={cn(
                "rounded-full px-5 py-3 shadow-sm shadow-black/5",
                selected ? "bg-primary" : "bg-card"
              )}
            >
              <Text className={selected ? "text-primary-foreground" : "text-foreground"}>
                {t("common.minutes", { minutes })}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {error ? <Text className="mt-6 text-sm text-destructive">{error}</Text> : null}

      <Button onPress={handleGenerate} disabled={selectedSubjectIds.length === 0 || isGenerating} className="mt-8 mb-28">
        {isGenerating ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
        <Text>{t("studyPlan.generatePlan")}</Text>
      </Button>
    </Screen>
  );
}
