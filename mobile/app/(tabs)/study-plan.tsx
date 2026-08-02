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
import { FlatList, StyleSheet, View } from "react-native";

import { Button, Card, Screen, Text } from "../../components/ui";
import { colors, radii, spacing } from "../../constants/theme";
import { ApiError, studyPlansApi, subjectsApi } from "../../lib/api";
import type { StudyPlan, Subject } from "../../lib/api";

const MINUTE_OPTIONS = [15, 30, 45, 60];

export default function StudyPlanScreen() {
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
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't generate a plan. Make sure the selected subjects have documents processed."
      );
    } finally {
      setIsGenerating(false);
    }
  }

  if (plan) {
    return (
      <Screen>
        <View style={styles.header}>
          <Text variant="display">{plan.name}</Text>
          <Text variant="body" style={styles.subtitle}>
            {plan.items.length} sessions scheduled
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
                <View style={styles.activityBadge}>
                  <Text variant="caption" style={{ color: colors.primary }}>
                    {item.activity_type}
                  </Text>
                </View>
              </View>
              <Text variant="body">{item.duration_minutes} min</Text>
            </Card>
          )}
        />
        <Button label="Generate a new plan" variant="secondary" onPress={() => setPlan(null)} />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Study Plan</Text>
        <Text variant="body" style={styles.subtitle}>
          Pick the subjects to include and how much time you have each day.
        </Text>
      </View>

      <Text variant="label" style={styles.sectionLabel}>
        Subjects
      </Text>
      <View style={styles.chipRow}>
        {subjects.map((subject) => {
          const selected = selectedSubjectIds.includes(subject.id);
          return (
            <Card
              key={subject.id}
              onPress={() => toggleSubject(subject.id)}
              style={[styles.chip, selected && styles.chipSelected]}
            >
              <Text variant="body" style={selected ? { color: colors.primary } : undefined}>
                {subject.name}
              </Text>
            </Card>
          );
        })}
      </View>

      <Text variant="label" style={styles.sectionLabel}>
        Daily study time
      </Text>
      <View style={styles.chipRow}>
        {MINUTE_OPTIONS.map((minutes) => (
          <Card
            key={minutes}
            onPress={() => setDailyMinutes(minutes)}
            style={[styles.chip, dailyMinutes === minutes && styles.chipSelected]}
          >
            <Text variant="body" style={dailyMinutes === minutes ? { color: colors.primary } : undefined}>
              {minutes} min
            </Text>
          </Card>
        ))}
      </View>

      {error ? (
        <Text variant="caption" style={styles.error}>
          {error}
        </Text>
      ) : null}

      <Button
        label="Generate plan"
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
  subtitle: {
    marginTop: spacing.xs,
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
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radii.full,
  },
  chipSelected: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  error: {
    marginTop: spacing.lg,
  },
  generateButton: {
    marginTop: spacing.xl,
  },
  list: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
  },
  itemCard: {
    marginBottom: spacing.md,
  },
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.xs,
  },
  activityBadge: {
    backgroundColor: colors.primaryLight,
    borderRadius: radii.full,
    paddingHorizontal: spacing.sm,
  },
});
