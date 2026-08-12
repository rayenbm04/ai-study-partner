/**
 * Saved study materials — browses back to everything already generated and
 * persisted server-side for this subject: past quizzes/exams (one row per
 * generation) and past summaries (upserted per document+type). Nothing here
 * is generated on this screen; it's purely a browsing view for material that
 * would otherwise be lost once its generation sheet/screen was closed.
 */
import { CaretDownIcon, CaretLeftIcon, CaretRightIcon, CaretUpIcon } from "phosphor-react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, Pressable, ScrollView, useColorScheme, View } from "react-native";

import { Card, CardContent } from "../../components/ui/card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Tag } from "../../components/ui/Tag";
import { Text } from "../../components/ui/text";
import { documentsApi, quizzesApi, subjectsApi, summariesApi } from "../../lib/api";
import type { Document, QuizListItem, Subject, Summary } from "../../lib/api";
import { localeTags } from "../../lib/i18n/translations";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";

type DocumentSummaries = { document: Document; summaries: Summary[] };

export default function SavedMaterialsScreen() {
  const { subjectId } = useLocalSearchParams<{ subjectId: string }>();
  const router = useRouter();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t, tn, language } = useLanguage();

  const SUMMARY_TYPE_LABELS: Record<string, string> = {
    short: t("summaryType.short"),
    detailed: t("summaryType.detailed"),
    bullet: t("summaryType.bullet"),
    key_concepts: t("summaryType.keyConcepts"),
    formula_sheet: t("summaryType.formulaSheet"),
    definitions: t("summaryType.definitions"),
  };

  const [subject, setSubject] = useState<Subject | null>(null);
  const [quizzes, setQuizzes] = useState<QuizListItem[]>([]);
  const [documentSummaries, setDocumentSummaries] = useState<DocumentSummaries[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      Promise.all([
        subjectsApi.getSubject(subjectId),
        quizzesApi.listQuizzesForSubject(subjectId),
        documentsApi.listDocuments(subjectId),
      ])
        .then(async ([s, quizList, documents]) => {
          const readyDocuments = documents.filter((d) => d.status === "ready");
          const summariesPerDocument = await Promise.all(
            readyDocuments.map((document) => summariesApi.listSummariesForDocument(document.id))
          );
          if (cancelled) return;
          setSubject(s);
          setQuizzes(quizList);
          setDocumentSummaries(
            readyDocuments
              .map((document, i) => ({ document, summaries: summariesPerDocument[i] }))
              .filter((entry) => entry.summaries.length > 0)
          );
        })
        .finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [subjectId])
  );

  if (isLoading || !subject) {
    return (
      <Screen>
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView contentContainerClassName="pt-2 pb-16">
        <View className="mb-3">
          <IconButton icon={CaretLeftIcon} onPress={() => router.back()} />
        </View>
        <Text className="mb-1 text-3xl font-bold">{t("materials.title")}</Text>
        <Text className="text-muted-foreground">{subject.name}</Text>

        <Text className="mt-8 mb-2 text-lg font-semibold">{t("materials.quizzesAndExams")}</Text>
        {quizzes.length === 0 ? (
          <Card>
            <CardContent>
              <Text>{t("materials.noQuizzes")}</Text>
            </CardContent>
          </Card>
        ) : (
          quizzes.map((quiz) => (
            <Pressable key={quiz.id} onPress={() => router.push(`/quiz/${quiz.id}`)} className="mb-3">
              <Card>
                <CardContent className="flex-row items-center gap-2">
                  <View className="flex-1">
                    <Text>{quiz.title}</Text>
                    <Text className="mt-0.5 text-xs text-muted-foreground">
                      {tn("common.questionCount", quiz.question_count)} ·{" "}
                      {new Date(quiz.created_at).toLocaleDateString(localeTags[language])}
                    </Text>
                  </View>
                  <Tag label={quiz.kind === "exam" ? t("subjectDetail.exam") : t("subjectDetail.quiz")} tone={quiz.kind === "exam" ? "accent" : "neutral"} />
                  <CaretRightIcon size={16} color={scheme.mutedForeground} />
                </CardContent>
              </Card>
            </Pressable>
          ))
        )}

        <Text className="mt-8 mb-2 text-lg font-semibold">{t("materials.summaries")}</Text>
        {documentSummaries.length === 0 ? (
          <Card>
            <CardContent>
              <Text>{t("materials.noSummaries")}</Text>
            </CardContent>
          </Card>
        ) : (
          documentSummaries.map(({ document, summaries }) => (
            <Card key={document.id} className="mb-3">
              <CardContent>
                <Text className="mb-2 text-sm font-medium text-muted-foreground">{document.original_filename}</Text>
                {summaries.map((summary) => (
                  <View key={summary.id}>
                    <Pressable
                      className="flex-row items-center justify-between py-2"
                      onPress={() => setExpandedSummaryId((current) => (current === summary.id ? null : summary.id))}
                    >
                      <Text className="flex-1">{SUMMARY_TYPE_LABELS[summary.summary_type] ?? summary.summary_type}</Text>
                      {expandedSummaryId === summary.id ? (
                        <CaretUpIcon size={16} color={scheme.mutedForeground} />
                      ) : (
                        <CaretDownIcon size={16} color={scheme.mutedForeground} />
                      )}
                    </Pressable>
                    {expandedSummaryId === summary.id ? (
                      <Text className="pb-2 text-muted-foreground">{summary.content}</Text>
                    ) : null}
                  </View>
                ))}
              </CardContent>
            </Card>
          ))
        )}
      </ScrollView>
    </Screen>
  );
}
