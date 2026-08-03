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
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";

import { RadarChart } from "../../components/RadarChart";
import { AnimatedNumber, Avatar, Button, Card, RingProgress, Screen, Tag, Text } from "../../components/ui";
import { fontFamilies, radii, spacing } from "../../constants/theme";
import { analyticsApi, progressApi, subjectsApi } from "../../lib/api";
import type { ConceptMastery, OverviewAnalytics, Subject, WeakConcept } from "../../lib/api";
import { flattenConceptNames, masteryColor } from "../../lib/progress-utils";
import { useTheme } from "../../lib/theme-context";

const REASON_LABEL: Record<WeakConcept["reason"], string> = {
  repeated_errors: "Repeated mistakes",
  slow_response: "Slow to answer",
  decay: "Fading from memory",
};

type SubjectProgress = {
  subject: Subject;
  tree: ConceptMastery[];
  weakConcepts: WeakConcept[];
};

export default function ProgressScreen() {
  const router = useRouter();
  const { colors } = useTheme();
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
        <View style={styles.center}>
          <ActivityIndicator color={colors.accent} />
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
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text variant="display" style={styles.header}>
          Progress
        </Text>

        {sections.length === 0 ? (
          <Card>
            <Text variant="body">Add a subject and some documents to start tracking mastery.</Text>
            <Button label="+ New subject" variant="secondary" onPress={() => router.push("/subject/new")} style={styles.emptyAction} />
          </Card>
        ) : (
          <>
            <View style={styles.statsRow}>
              <Card style={styles.statCard}>
                <RingProgress percentage={overallMastery ?? 0} size={64} strokeWidth={7} color={colors.accent} trackColor={colors.border}>
                  <Text style={{ position: "absolute", fontFamily: fontFamilies.semibold, fontSize: 13 }}>
                    {overallMastery !== null ? `${overallMastery}%` : "—"}
                  </Text>
                </RingProgress>
                <Text variant="caption" style={styles.statLabel}>
                  Overall mastery
                </Text>
              </Card>
              <Card style={styles.statCard}>
                <View style={[styles.statIcon, { backgroundColor: colors.primaryLight }]}>
                  <Ionicons name="albums" size={22} color={colors.accentDark} />
                </View>
                <Text style={{ fontFamily: fontFamilies.display, fontSize: 20, marginTop: spacing.sm }}>
                  <AnimatedNumber value={dueToday} />
                </Text>
                <Text variant="caption" style={styles.statLabel}>
                  Due today
                </Text>
              </Card>
              <Card style={styles.statCard}>
                <View style={[styles.statIcon, { backgroundColor: colors.errorLight }]}>
                  <Ionicons name="alert-circle" size={22} color={colors.error} />
                </View>
                <Text style={{ fontFamily: fontFamilies.display, fontSize: 20, marginTop: spacing.sm }}>
                  <AnimatedNumber value={weakSpotsTotal} />
                </Text>
                <Text variant="caption" style={styles.statLabel}>
                  Weak spots
                </Text>
              </Card>
            </View>

            {sections.map(({ subject, tree, weakConcepts }) => {
              const stats = subjectStats.find((s) => s.subject_id === subject.id);
              const namesById = flattenConceptNames(tree);
              const radarData = tree.slice(0, 8).map((c) => ({ label: c.name, value: c.mastery_score ?? 0 }));

              return (
                <Card key={subject.id} style={styles.subjectCard}>
                  <View style={styles.subjectHeader}>
                    <Avatar label={subject.name} size={40} />
                    <Text variant="subtitle" style={styles.subjectName}>
                      {subject.name}
                    </Text>
                    <Text variant="title" style={{ color: colors.accentDark }}>
                      {stats?.average_mastery !== null && stats?.average_mastery !== undefined
                        ? `${Math.round(stats.average_mastery)}%`
                        : "—"}
                    </Text>
                  </View>

                  {tree.length === 0 ? (
                    <Text variant="caption" style={styles.notStarted}>
                      Not started yet — practice a flashcard or take a quiz to begin tracking mastery.
                    </Text>
                  ) : (
                    <>
                      {radarData.length >= 3 ? (
                        <View style={styles.radarWrap}>
                          <RadarChart
                            data={radarData}
                            size={220}
                            color={colors.accent}
                            gridColor={colors.border}
                            labelColor={colors.textSecondary}
                          />
                        </View>
                      ) : null}

                      <Text variant="label" style={styles.chaptersLabel}>
                        Chapters
                      </Text>
                      <View style={styles.chapters}>
                        {tree.map((chapter) => {
                          const color = masteryColor(colors, chapter.mastery_score);
                          return (
                            <View key={chapter.concept_id} style={styles.chapterRow}>
                              <View style={styles.chapterText}>
                                <Text style={{ fontFamily: fontFamilies.medium, fontSize: 14 }}>{chapter.name}</Text>
                                <View style={[styles.chapterBarTrack, { backgroundColor: colors.border }]}>
                                  <View
                                    style={[
                                      styles.chapterBarFill,
                                      { width: `${Math.max(3, chapter.mastery_score ?? 3)}%`, backgroundColor: color },
                                    ]}
                                  />
                                </View>
                              </View>
                              <Text style={{ fontFamily: fontFamilies.semibold, fontSize: 13, color }}>
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
                      <Text variant="label" style={styles.gapsLabel}>
                        Gaps detected
                      </Text>
                      <View style={styles.gaps}>
                        {weakConcepts.map((w) => (
                          <View key={w.id} style={[styles.gapCard, { backgroundColor: colors.surfaceAlt, borderLeftColor: colors.error }]}>
                            <View style={styles.gapHeader}>
                              <Text style={{ fontFamily: fontFamilies.semibold, fontSize: 14, flex: 1 }}>
                                {namesById.get(w.concept_id) ?? "Unknown concept"}
                              </Text>
                              <Tag label={REASON_LABEL[w.reason]} tone="error" />
                            </View>
                            <Button
                              label="Review now"
                              variant="secondary"
                              onPress={() => reviewConcept(subject.id, namesById.get(w.concept_id) ?? "this concept")}
                              style={styles.gapAction}
                            />
                          </View>
                        ))}
                      </View>
                    </>
                  ) : null}
                </Card>
              );
            })}
          </>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  scroll: {
    paddingTop: spacing.sm,
    paddingBottom: 130,
  },
  header: {
    marginBottom: spacing.lg,
  },
  emptyAction: {
    marginTop: spacing.lg,
  },
  statsRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  statCard: {
    flex: 1,
    alignItems: "center",
    padding: spacing.md,
  },
  statIcon: {
    width: 44,
    height: 44,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
  },
  statLabel: {
    marginTop: spacing.sm,
    textAlign: "center",
  },
  subjectCard: {
    marginBottom: spacing.md,
  },
  subjectHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  subjectName: {
    flex: 1,
  },
  notStarted: {
    marginTop: spacing.md,
  },
  radarWrap: {
    alignItems: "center",
    marginTop: spacing.lg,
  },
  chaptersLabel: {
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  chapters: {
    gap: spacing.md,
  },
  chapterRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  chapterText: {
    flex: 1,
  },
  chapterBarTrack: {
    height: 5,
    borderRadius: radii.full,
    marginTop: 6,
    overflow: "hidden",
  },
  chapterBarFill: {
    height: "100%",
    borderRadius: radii.full,
  },
  gapsLabel: {
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  gaps: {
    gap: spacing.sm,
  },
  gapCard: {
    borderRadius: radii.lg,
    borderLeftWidth: 4,
    padding: spacing.md,
  },
  gapHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  gapAction: {
    height: 44,
  },
});
