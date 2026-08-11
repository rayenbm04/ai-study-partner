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
import { ActivityIndicator, ScrollView, useColorScheme, View } from "react-native";

import { Card, CardContent } from "../../components/ui/card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Tag } from "../../components/ui/Tag";
import { Text } from "../../components/ui/text";
import { progressApi, subjectsApi } from "../../lib/api";
import type { ConceptMastery, Subject, WeakConcept } from "../../lib/api";
import { flattenConceptNames, masteryColor } from "../../lib/progress-utils";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { cn } from "../../lib/utils";

export default function ConceptMapScreen() {
  const { subjectId } = useLocalSearchParams<{ subjectId: string }>();
  const router = useRouter();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t } = useLanguage();
  const REASON_LABEL: Record<WeakConcept["reason"], string> = {
    repeated_errors: t("weakConceptReason.repeatedErrors"),
    slow_response: t("weakConceptReason.slowResponse"),
    decay: t("weakConceptReason.decay"),
  };

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
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
        </View>
      </Screen>
    );
  }

  const namesById = flattenConceptNames(tree);

  return (
    <Screen>
      <ScrollView contentContainerClassName="pt-2 pb-16">
        <View className="mb-3">
          <IconButton name="chevron-back" onPress={() => router.back()} />
        </View>
        <Text className="text-3xl font-bold">{t("concepts.title")}</Text>
        <Text className="mt-1 text-muted-foreground">{subject?.name}</Text>

        {weakConcepts.length > 0 ? (
          <>
            <Text className="mt-8 mb-2 text-lg font-semibold">{t("progress.weakSpots")}</Text>
            <View className="gap-2">
              {weakConcepts.map((w) => (
                <Card key={w.id}>
                  <CardContent>
                    <View className="flex-row items-center gap-2">
                      <Ionicons name="alert-circle" size={18} color={scheme.destructive} />
                      <Text className="flex-1 text-base font-semibold">{namesById.get(w.concept_id) ?? t("progress.unknownConcept")}</Text>
                    </View>
                    <View className="mt-3 flex-row items-center justify-between">
                      <Tag label={REASON_LABEL[w.reason]} tone="error" />
                      <Text className="text-xs text-muted-foreground">{t("concepts.confidence", { percent: Math.round(w.confidence * 100) })}</Text>
                    </View>
                  </CardContent>
                </Card>
              ))}
            </View>
          </>
        ) : null}

        <Text className="mt-8 mb-2 text-lg font-semibold">{t("concepts.masteryByConcept")}</Text>
        {tree.length === 0 ? (
          <Card>
            <CardContent>
              <Text>{t("concepts.noConceptsTracked")}</Text>
            </CardContent>
          </Card>
        ) : (
          <Card className="overflow-hidden py-0">
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
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const isParent = node.children.length > 0;
  const color = masteryColor(scheme, node.mastery_score);
  const noBorder = isLast && depth === 0 && !isParent;

  return (
    <View>
      <View
        className={cn("flex-row items-center gap-3 py-3 pr-4", !noBorder && "border-b border-border")}
        style={{ paddingLeft: 12 + depth * 16 }}
      >
        <View className="flex-1">
          <Text className={cn(isParent ? "text-[15.5px] font-semibold" : "text-[14.5px]")}>{node.name}</Text>
          {!isParent ? (
            <View className="mt-1.5 h-1 overflow-hidden rounded-full bg-border">
              <View className="h-full rounded-full" style={{ width: `${Math.max(3, node.mastery_score ?? 3)}%`, backgroundColor: color }} />
            </View>
          ) : null}
        </View>
        <View className="flex-row items-center gap-1">
          {node.trend ? (
            <Ionicons
              name={node.trend === "up" ? "trending-up" : node.trend === "down" ? "trending-down" : "remove"}
              size={14}
              color={node.trend === "up" ? "hsl(152 55% 40%)" : node.trend === "down" ? scheme.destructive : scheme.mutedForeground}
            />
          ) : null}
          <Text className="text-[13.5px] font-semibold" style={{ color }}>
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
