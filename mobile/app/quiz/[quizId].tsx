/**
 * Quiz-taking screen — the step-by-step, one-question-at-a-time pattern
 * pulled from the Brilliant reference screens: progress bar up top, the
 * question stated plainly, answer options as the main content, a fixed
 * action bar at the bottom. Correct/incorrect is never shown per-question
 * (the backend deliberately withholds it — AnswerAckResponse has no
 * is_correct) — full results only appear after the whole attempt is
 * submitted, on the results view at the bottom of this file.
 */
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";

import { Button, Card, ProgressBar, Screen, Text, TextField } from "../../components/ui";
import { colors, radii, spacing } from "../../constants/theme";
import { quizzesApi } from "../../lib/api";
import type { Quiz, QuizAttemptResult } from "../../lib/api";

export default function QuizAttemptScreen() {
  const { quizId } = useLocalSearchParams<{ quizId: string }>();
  const router = useRouter();

  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [questionStartedAt, setQuestionStartedAt] = useState<number>(Date.now());
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([quizzesApi.getQuiz(quizId), quizzesApi.startAttempt(quizId)])
      .then(([loadedQuiz, attempt]) => {
        setQuiz(loadedQuiz);
        setAttemptId(attempt.id);
        setQuestionStartedAt(Date.now());
      })
      .finally(() => setIsLoading(false));
  }, [quizId]);

  const currentQuestion = quiz?.questions[currentIndex];
  const isLastQuestion = quiz ? currentIndex === quiz.questions.length - 1 : false;

  async function handleContinue() {
    if (!attemptId || !currentQuestion) return;
    setIsSubmittingAnswer(true);
    try {
      const timeSpentSeconds = Math.round((Date.now() - questionStartedAt) / 1000);
      await quizzesApi.submitAnswer(attemptId, {
        question_id: currentQuestion.id,
        answer: currentAnswer,
        time_spent_seconds: timeSpentSeconds,
      });

      if (isLastQuestion) {
        const finalResult = await quizzesApi.submitAttempt(attemptId);
        setResult(finalResult);
      } else {
        setCurrentIndex((i) => i + 1);
        setCurrentAnswer("");
        setQuestionStartedAt(Date.now());
      }
    } finally {
      setIsSubmittingAnswer(false);
    }
  }

  if (isLoading || !quiz) {
    return (
      <Screen>
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </Screen>
    );
  }

  if (result) {
    return <ResultsView result={result} onDone={() => router.back()} />;
  }

  if (!currentQuestion) return null;

  const showsOptions = currentQuestion.options && currentQuestion.options.length > 0;

  return (
    <Screen>
      <View style={styles.progressWrap}>
        <ProgressBar total={quiz.questions.length} completed={currentIndex} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Text variant="title">{currentQuestion.question}</Text>

        {showsOptions ? (
          <View style={styles.options}>
            {currentQuestion.options!.map((option) => (
              <Pressable
                key={option}
                onPress={() => setCurrentAnswer(option)}
                style={[styles.optionRow, currentAnswer === option && styles.optionRowSelected]}
              >
                <Text variant="body" style={currentAnswer === option ? { color: colors.primary } : undefined}>
                  {option}
                </Text>
              </Pressable>
            ))}
          </View>
        ) : (
          <TextField
            placeholder="Type your answer"
            value={currentAnswer}
            onChangeText={setCurrentAnswer}
            multiline={currentQuestion.type === "short_answer"}
            style={styles.freeTextInput}
          />
        )}
      </ScrollView>

      <Button
        label={isLastQuestion ? "Finish" : "Continue"}
        onPress={handleContinue}
        loading={isSubmittingAnswer}
        disabled={!currentAnswer.trim()}
        style={styles.action}
      />
    </Screen>
  );
}

function ResultsView({ result, onDone }: { result: QuizAttemptResult; onDone: () => void }) {
  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.resultsScroll}>
        <Text variant="display">Score: {result.score !== null ? Math.round(result.score) : "—"}%</Text>

        {result.answers.map((answer) => (
          <Card
            key={answer.question_id}
            style={[styles.resultCard, answer.is_correct ? styles.resultCorrect : styles.resultIncorrect]}
          >
            <Text variant="body">{answer.question}</Text>
            <Text variant="caption" style={styles.resultLabel}>
              Your answer: {answer.student_answer ?? "—"}
            </Text>
            {!answer.is_correct ? (
              <Text variant="caption" style={styles.resultLabel}>
                Correct answer: {answer.correct_answer}
              </Text>
            ) : null}
            {answer.explanation ? (
              <Text variant="caption" style={styles.resultExplanation}>
                {answer.explanation}
              </Text>
            ) : null}
          </Card>
        ))}
      </ScrollView>
      <Button label="Done" onPress={onDone} style={styles.action} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  progressWrap: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  body: {
    paddingBottom: spacing.xl,
  },
  options: {
    marginTop: spacing.xl,
    gap: spacing.md,
  },
  optionRow: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    padding: spacing.lg,
    backgroundColor: colors.surface,
  },
  optionRowSelected: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  freeTextInput: {
    marginTop: spacing.xl,
  },
  action: {
    marginBottom: spacing.lg,
  },
  resultsScroll: {
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  resultCard: {
    marginTop: spacing.lg,
  },
  resultCorrect: {
    borderColor: colors.success,
  },
  resultIncorrect: {
    borderColor: colors.error,
  },
  resultLabel: {
    marginTop: spacing.sm,
  },
  resultExplanation: {
    marginTop: spacing.sm,
    fontStyle: "italic",
  },
});
