/**
 * Progress tab — cross-subject mastery at a glance, reusing the analytics
 * overview (the backend has no single "all my progress" endpoint; overview
 * already carries per-subject average_mastery/weak_concept_count, which is
 * exactly this screen's shape). Tapping a subject goes to its detail screen
 * rather than a separate concept-tree view — a dedicated drill-down into
 * the full concept tree (GET /subjects/{id}/progress) is a good next step,
 * not built in this pass.
 */
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { FlatList, StyleSheet, View } from "react-native";

import { Card, Screen, Text } from "../../components/ui";
import { colors, spacing } from "../../constants/theme";
import { analyticsApi } from "../../lib/api";
import type { SubjectAnalytics } from "../../lib/api";

export default function ProgressScreen() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<SubjectAnalytics[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      analyticsApi
        .getOverview()
        .then((overview) => !cancelled && setSubjects(overview.subjects))
        .finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [])
  );

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Progress</Text>
      </View>

      <FlatList
        data={subjects}
        keyExtractor={(item) => item.subject_id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <Card>
              <Text variant="body">Add a subject and some documents to start tracking mastery.</Text>
            </Card>
          ) : null
        }
        renderItem={({ item }) => (
          <Card onPress={() => router.push(`/subject/${item.subject_id}`)} style={styles.card}>
            <View style={styles.row}>
              <Text variant="title" style={styles.name}>
                {item.subject_name}
              </Text>
              <Text variant="title" style={{ color: colors.primary }}>
                {item.average_mastery !== null ? `${Math.round(item.average_mastery)}%` : "—"}
              </Text>
            </View>
            <Text variant="caption">
              {item.concepts_practiced}/{item.concepts_total} concepts practiced
              {item.weak_concept_count > 0 ? ` · ${item.weak_concept_count} weak spot${item.weak_concept_count === 1 ? "" : "s"}` : ""}
            </Text>
          </Card>
        )}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  list: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
  },
  card: {
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xs,
  },
  name: {
    flex: 1,
  },
});
