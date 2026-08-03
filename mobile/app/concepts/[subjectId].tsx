/**
 * Concept map — the per-concept mastery tree (GET /subjects/{id}/progress)
 * and the active weak-concept flags (GET /subjects/{id}/weak-concepts),
 * cross-referenced by concept_id for a name since WeakConcept only carries
 * the id. This is the screen that actually shows the two things the product
 * is meant to differentiate on: a concept-by-concept "knowledge graph" of
 * mastery (not just one subject-wide average) and *why* each weak spot was
 * flagged (repeated wrong answers / slow to answer / decayed since last
 * check), not just a bare count.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";

import { Card, IconButton, Screen, Tag, Text } from "../../components/ui";
import { fontFamilies, radii, spacing } from "../../constants/theme";
import { progressApi, subjectsApi } from "../../lib/api";
import type { ColorScheme } from "../../constants/theme";
import type { ConceptMastery, Subject, WeakConcept } from "../../lib/api";
import { useTheme } from "../../lib/theme-context";

const REASON_LABEL: Record<WeakConcept["reason"], string> = {
  repeated_errors: "Repeated mistakes",
  slow_response: "Slow to answer",
  decay: "Fading from memory",
};

function masteryColor(colors: ColorScheme, score: number | null): string {
  if (score === null) return colors.textMuted;
  if (score >= 70) return colors.sage;
  if (score >= 40) return colors.accent;
  return colors.error;
}

function flattenNames(nodes: ConceptMastery[], out: Map<string, string>) {
  for (const node of nodes) {
    out.set(node.concept_id, node.name);
    if (node.children.length > 0) flattenNames(node.children, out);
  }
}

export default function ConceptMapScreen() {
  const { subjectId } = useLocalSearchParams<{ subjectId: string }>();
  const router = useRouter();
  const { colors } = useTheme();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [tree, setTree] = useState<ConceptMastery[]>([]);
  const [weakConcepts, setWeakConcepts] = useState<WeakConcept[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      Promise.all([
        subjectsApi.getSubject(subjectId),
        progressApi.getProgress(subjectId),
        progressApi.getWeakConcepts(subjectId),
      ])
        .then(([s, progress, weak]) => {
          if (cancelled) return;
          setSubject(s);
          setTree(progress);
          setWeakConcepts(weak.filter((w) => w.status === "active"));
        })
        .finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [subjectId])
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

  const namesById = new Map<string, string>();
  flattenNames(tree, namesById);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.headerRow}>
          <IconButton name="chevron-back" onPress={() => router.back()} />
        </View>
        <Text variant="display">Concept map</Text>
        <Text variant="body" style={[styles.subtitle, { color: colors.textSecondary }]}>
          {subject?.name}
        </Text>

        {weakConcepts.length > 0 ? (
          <>
            <Text variant="title" style={styles.sectionLabel}>
              Weak spots
            </Text>
            <View style={styles.weakList}>
              {weakConcepts.map((w) => (
                <Card key={w.id} style={styles.weakCard}>
                  <View style={styles.weakRow}>
                    <Ionicons name="alert-circle" size={18} color={colors.error} />
                    <Text variant="subtitle" style={styles.weakName}>
                      {namesById.get(w.concept_id) ?? "Unknown concept"}
                    </Text>
                  </View>
                  <View style={styles.weakMeta}>
                    <Tag label={REASON_LABEL[w.reason]} tone="error" />
                    <Text variant="caption">{Math.round(w.confidence * 100)}% confidence</Text>
                  </View>
                </Card>
              ))}
            </View>
          </>
        ) : null}

        <Text variant="title" style={styles.sectionLabel}>
          Mastery by concept
        </Text>
        {tree.length === 0 ? (
          <Card>
            <Text variant="body">
              No concepts tracked yet — mastery builds up as you review flashcards and take quizzes.
            </Text>
          </Card>
        ) : (
          <Card style={styles.treeCard}>
            {tree.map((node, i) => (
              <ConceptRow key={node.concept_id} node={node} depth={0} isLast={i === tree.length - 1} />
            ))}
          </Card>
        )}
      </ScrollView>
    </Screen>
  );
}

function ConceptRow({ node, depth, isLast }: { node: ConceptMastery; depth: number; isLast: boolean }) {
  const { colors } = useTheme();
  const isParent = node.children.length > 0;
  const color = masteryColor(colors, node.mastery_score);

  return (
    <View>
      <View
        style={[
          styles.conceptRow,
          { paddingLeft: spacing.md + depth * spacing.lg, borderBottomColor: colors.border },
          isLast && depth === 0 && !isParent ? styles.noBorder : null,
        ]}
      >
        <View style={styles.conceptText}>
          <Text
            style={{
              fontFamily: isParent ? fontFamilies.semibold : fontFamilies.regular,
              fontSize: isParent ? 15.5 : 14.5,
              color: colors.textPrimary,
            }}
          >
            {node.name}
          </Text>
          {!isParent ? (
            <View style={[styles.miniBarTrack, { backgroundColor: colors.border }]}>
              <View
                style={[
                  styles.miniBarFill,
                  { width: `${Math.max(3, node.mastery_score ?? 3)}%`, backgroundColor: color },
                ]}
              />
            </View>
          ) : null}
        </View>
        <View style={styles.conceptScoreWrap}>
          {node.trend ? (
            <Ionicons
              name={node.trend === "up" ? "trending-up" : node.trend === "down" ? "trending-down" : "remove"}
              size={14}
              color={node.trend === "up" ? colors.sage : node.trend === "down" ? colors.error : colors.textMuted}
            />
          ) : null}
          <Text style={{ fontFamily: fontFamilies.semibold, fontSize: 13.5, color }}>
            {node.mastery_score !== null ? `${Math.round(node.mastery_score)}%` : "—"}
          </Text>
        </View>
      </View>
      {node.children.map((child, i) => (
        <ConceptRow key={child.concept_id} node={child} depth={depth + 1} isLast={isLast && i === node.children.length - 1} />
      ))}
    </View>
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
    paddingBottom: spacing.xxxl,
  },
  headerRow: {
    marginBottom: spacing.md,
  },
  subtitle: {
    marginTop: spacing.xs,
  },
  sectionLabel: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  weakList: {
    gap: spacing.sm,
  },
  weakCard: {
    marginBottom: 0,
  },
  weakRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  weakName: {
    flex: 1,
  },
  weakMeta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  treeCard: {
    padding: 0,
    overflow: "hidden",
  },
  conceptRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingRight: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
  },
  noBorder: {
    borderBottomWidth: 0,
  },
  conceptText: {
    flex: 1,
  },
  miniBarTrack: {
    height: 5,
    borderRadius: radii.full,
    marginTop: 6,
    overflow: "hidden",
  },
  miniBarFill: {
    height: "100%",
    borderRadius: radii.full,
  },
  conceptScoreWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
});
