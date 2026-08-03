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
import { useTheme } from "../../lib/theme-context";

const MINUTE_OPTIONS = [15, 30, 45, 60];

export default function StudyPlanScreen() {
  const { colors } = useTheme();
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
          <Text variant="body" style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
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
                <Tag label={item.activity_type} tone="accent" />
              </View>
              <Text variant="body">{item.duration_minutes} min</Text>
            </Card>
          )}
        />
        <Button
          label="Generate a new plan"
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
        <Text variant="display">Study Plan</Text>
        <Text variant="body" style={{ color: colors.textSecondary, marginTop: spacing.xs }}>
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
        Daily study time
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
              <Text style={{ color: selected ? colors.textOnPrimary : colors.textPrimary }}>{minutes} min</Text>
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
