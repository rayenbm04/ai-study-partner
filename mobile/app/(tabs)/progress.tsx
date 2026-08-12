/**
 * Progress tab — an aggregate view across every subject: overall stats up
 * top, then one section per subject with a radar of its chapters (the
 * concept tree's top-level nodes), a mastery bar per chapter, and any
 * active weak spots with a "Review now" shortcut straight into the Coach
 * with that concept as the opening question.
 *
 * Everything here comes from real endpoints (GET /analytics/overview,
 * GET /subjects/{id}/progress, GET /subjects/{id}/weak-concepts) — no
 * streaks/badges/estimated-minutes invented for a card that needs filling.
 */
import { StackIcon, WarningCircleIcon } from "phosphor-react-native";
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, ScrollView, View } from "react-native";

import { RadarChart } from "../../components/RadarChart";
import { AnimatedNumber } from "../../components/ui/AnimatedNumber";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { RingProgress } from "../../components/ui/RingProgress";
import { Screen } from "../../components/ui/Screen";
import { Tag } from "../../components/ui/Tag";
import { Text } from "../../components/ui/text";
import { analyticsApi, progressApi, subjectsApi } from "../../lib/api";
import type { ConceptMastery, OverviewAnalytics, Subject, WeakConcept } from "../../lib/api";
import { flattenConceptNames, masteryColor } from "../../lib/progress-utils";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";

type SubjectProgress = {
  subject: Subject;
  tree: ConceptMastery[];
  weakConcepts: WeakConcept[];
};

export default function ProgressScreen() {
  const router = useRouter();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  const { t } = useLanguage();
  const REASON_LABEL: Record<WeakConcept["reason"], string> = {
    repeated_errors: t("weakConceptReason.repeatedErrors"),
    slow_response: t("weakConceptReason.slowResponse"),
    decay: t("weakConceptReason.decay"),
  };
  const [isLoading, setIsLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [sections, setSections] = useState<SubjectProgress[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      (async () => {
        const [subjects, overviewData] = await Promise.all([subjectsApi.listSubjects(), analyticsApi.getOverview()]);
        if (cancelled) return;
        setOverview(overviewData);

        const perSubject = await Promise.all(
          subjects.map(async (subject) => {
            const [tree, weak] = await Promise.all([
              progressApi.getProgress(subject.id),
              progressApi.getWeakConcepts(subject.id),
            ]);
            return { subject, tree, weakConcepts: weak.filter((w) => w.status === "active") };
          })
        );
        if (!cancelled) setSections(perSubject);
      })().finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [])
  );

  if (isLoading) {
    return (
      <Screen>
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
        </View>
      </Screen>
    );
  }

  const subjectStats = overview?.subjects ?? [];
  const masteryValues = subjectStats.map((s) => s.average_mastery).filter((v): v is number => v !== null);
  const overallMastery = masteryValues.length > 0 ? Math.round(masteryValues.reduce((a, b) => a + b, 0) / masteryValues.length) : null;
  const dueToday = overview?.total_flashcards_due ?? 0;
  const weakSpotsTotal = subjectStats.reduce((sum, s) => sum + s.weak_concept_count, 0);

  function reviewConcept(subjectId: string, conceptName: string) {
    router.push({ pathname: "/coach/[subjectId]", params: { subjectId, prompt: `Explain ${conceptName}` } });
  }

  return (
    <Screen>
      <ScrollView contentContainerClassName="pt-2 pb-32">
        <Text className="mb-6 text-3xl font-bold">{t("progress.header")}</Text>

        {sections.length === 0 ? (
          <Card>
            <CardContent>
              <Text>{t("progress.emptyBody")}</Text>
              <Button variant="secondary" onPress={() => router.push("/subject/new")} className="mt-6">
                <Text>{t("home.newSubject")}</Text>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <View className="mb-6 flex-row gap-2">
              <Card className="flex-1">
                <CardContent className="items-center p-4">
                  <RingProgress percentage={overallMastery ?? 0} size={64} strokeWidth={7} color={scheme.primary} trackColor={scheme.border}>
                    <Text className="absolute text-[13px] font-semibold">
                      {overallMastery !== null ? `${overallMastery}%` : "—"}
                    </Text>
                  </RingProgress>
                  <Text className="mt-2 text-center text-xs text-muted-foreground">{t("progress.overallMastery")}</Text>
                </CardContent>
              </Card>
              <Card className="flex-1">
                <CardContent className="items-center p-4">
                  <View className="size-11 items-center justify-center rounded-full bg-primary/15">
                    <StackIcon size={22} color={scheme.primary} weight="fill" />
                  </View>
                  <Text className="mt-2 text-xl font-bold">
                    <AnimatedNumber value={dueToday} />
                  </Text>
                  <Text className="mt-2 text-center text-xs text-muted-foreground">{t("progress.dueToday")}</Text>
                </CardContent>
              </Card>
              <Card className="flex-1">
                <CardContent className="items-center p-4">
                  <View className="size-11 items-center justify-center rounded-full bg-destructive/10">
                    <WarningCircleIcon size={22} color={scheme.destructive} weight="fill" />
                  </View>
                  <Text className="mt-2 text-xl font-bold">
                    <AnimatedNumber value={weakSpotsTotal} />
                  </Text>
                  <Text className="mt-2 text-center text-xs text-muted-foreground">{t("progress.weakSpots")}</Text>
                </CardContent>
              </Card>
            </View>

            {sections.map(({ subject, tree, weakConcepts }) => {
              const stats = subjectStats.find((s) => s.subject_id === subject.id);
              const namesById = flattenConceptNames(tree);
              const radarData = tree.slice(0, 8).map((c) => ({ label: c.name, value: c.mastery_score ?? 0 }));

              return (
                <Card key={subject.id} className="mb-4">
                  <CardContent>
                    <View className="flex-row items-center gap-3">
                      <Avatar alt={subject.name} className="size-10">
                        <AvatarFallback>
                          <Text className="font-semibold">{subject.name.slice(0, 2).toUpperCase()}</Text>
                        </AvatarFallback>
                      </Avatar>
                      <Text className="flex-1 text-base font-semibold">{subject.name}</Text>
                      <Text className="text-lg font-semibold text-primary">
                        {stats?.average_mastery !== null && stats?.average_mastery !== undefined
                          ? `${Math.round(stats.average_mastery)}%`
                          : "—"}
                      </Text>
                    </View>

                    {tree.length === 0 ? (
                      <Text className="mt-3 text-xs text-muted-foreground">{t("progress.notStarted")}</Text>
                    ) : (
                      <>
                        {radarData.length >= 3 ? (
                          <View className="mt-6 items-center">
                            <RadarChart data={radarData} size={220} color={scheme.primary} gridColor={scheme.border} labelColor={scheme.mutedForeground} />
                          </View>
                        ) : null}

                        <Text className="mt-6 mb-2 text-sm font-medium text-muted-foreground">{t("progress.chapters")}</Text>
                        <View className="gap-3">
                          {tree.map((chapter) => {
                            const color = masteryColor(scheme, chapter.mastery_score);
                            return (
                              <View key={chapter.concept_id} className="flex-row items-center gap-3">
                                <View className="flex-1">
                                  <Text className="text-sm font-medium">{chapter.name}</Text>
                                  <View className="mt-1.5 h-1 overflow-hidden rounded-full bg-border">
                                    <View
                                      className="h-full rounded-full"
                                      style={{ width: `${Math.max(3, chapter.mastery_score ?? 3)}%`, backgroundColor: color }}
                                    />
                                  </View>
                                </View>
                                <Text className="text-[13px] font-semibold" style={{ color }}>
                                  {chapter.mastery_score !== null ? `${Math.round(chapter.mastery_score)}%` : "—"}
                                </Text>
                              </View>
                            );
                          })}
                        </View>
                      </>
                    )}

                    {weakConcepts.length > 0 ? (
                      <>
                        <Text className="mt-6 mb-2 text-sm font-medium text-muted-foreground">{t("progress.gapsDetected")}</Text>
                        <View className="gap-2">
                          {weakConcepts.map((w) => (
                            <View key={w.id} className="rounded-lg border-l-4 border-l-destructive bg-input/30 p-3">
                              <View className="mb-3 flex-row items-center gap-2">
                                <Text className="flex-1 text-sm font-semibold">
                                  {namesById.get(w.concept_id) ?? t("progress.unknownConcept")}
                                </Text>
                                <Tag label={REASON_LABEL[w.reason]} tone="error" />
                              </View>
                              <Button
                                variant="secondary"
                                onPress={() => reviewConcept(subject.id, namesById.get(w.concept_id) ?? "this concept")}
                                className="h-11"
                              >
                                <Text>{t("progress.reviewNow")}</Text>
                              </Button>
                            </View>
                          ))}
                        </View>
                      </>
                    ) : null}
                  </CardContent>
                </Card>
              );
            })}
          </>
        )}
      </ScrollView>
    </Screen>
  );
}
