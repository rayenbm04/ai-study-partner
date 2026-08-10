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
import { FlatList, Pressable, StyleSheet, View } from "react-native";

import { Button, Card, Screen, Tag, Text } from "../../components/ui";
import { radii, spacing } from "../../constants/theme";
import { ApiError, studyPlansApi, subjectsApi } from "../../lib/api";
import type { StudyPlan, Subject } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

const MINUTE_OPTIONS = [15, 30, 45, 60];

export default function StudyPlanScreen() {
  const { colors } = useTheme();
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
        <View style={styles.header}>
          <Text variant="display">{plan.name}</Text>
          <Text variant="body" style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
            {tn("studyPlan.sessionsScheduled", plan.items.length)}
          </Text>
        </View>
        <FlatList
          data={plan.items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Card style={styles.itemCard}>
              <View style={styles.itemRow}>
                <Text variant="label">{item.scheduled_date}</Text>
                <Tag label={t(`activityType.${item.activity_type}`)} tone="accent" />
              </View>
              <Text variant="body">{t("common.minutes", { minutes: item.duration_minutes })}</Text>
            </Card>
          )}
        />
        <Button
          label={t("studyPlan.generateNewPlan")}
          variant="secondary"
          onPress={() => setPlan(null)}
          style={styles.bottomAction}
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">{t("studyPlan.title")}</Text>
        <Text variant="body" style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
          {t("studyPlan.subtitle")}
        </Text>
      </View>

      <Text variant="label" style={styles.sectionLabel}>
        {t("common.subjects")}
      </Text>
      <View style={styles.chipRow}>
        {subjects.map((subject) => {
          const selected = selectedSubjectIds.includes(subject.id);
          return (
            <Pressable
              key={subject.id}
              onPress={() => toggleSubject(subject.id)}
              style={[
                styles.chip,
                { backgroundColor: selected ? colors.primary : colors.surface, shadowColor: colors.shadow },
              ]}
            >
              <Text style={{ color: selected ? colors.textOnPrimary : colors.textPrimary }}>{subject.name}</Text>
            </Pressable>
          );
        })}
      </View>

      <Text variant="label" style={styles.sectionLabel}>
        {t("studyPlan.dailyStudyTime")}
      </Text>
      <View style={styles.chipRow}>
        {MINUTE_OPTIONS.map((minutes) => {
          const selected = dailyMinutes === minutes;
          return (
            <Pressable
              key={minutes}
              onPress={() => setDailyMinutes(minutes)}
              style={[
                styles.chip,
                { backgroundColor: selected ? colors.primary : colors.surface, shadowColor: colors.shadow },
              ]}
            >
              <Text style={{ color: selected ? colors.textOnPrimary : colors.textPrimary }}>
                {t("common.minutes", { minutes })}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {error ? (
        <Text variant="caption" style={[styles.error, { color: colors.error }]}>
          {error}
        </Text>
      ) : null}

      <Button
        label={t("studyPlan.generatePlan")}
        onPress={handleGenerate}
        loading={isGenerating}
        disabled={selectedSubjectIds.length === 0}
        style={styles.generateButton}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  sectionLabel: {
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  chip: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.full,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 1,
    shadowRadius: 14,
    elevation: 2,
  },
  error: {
    marginTop: spacing.lg,
  },
  generateButton: {
    marginTop: spacing.xl,
    marginBottom: 110,
  },
  bottomAction: {
    marginBottom: 110,
  },
  list: {
    gap: spacing.md,
    paddingBottom: 130,
  },
  itemCard: {
    marginBottom: 0,
  },
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xs,
  },
});
