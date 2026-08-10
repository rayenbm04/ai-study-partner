/**
 * Quiz-taking screen — the step-by-step, one-question-at-a-time pattern
 * pulled from the Brilliant reference screens: progress segments up top,
 * the question stated plainly, answer options as the main content, a fixed
 * action bar at the bottom. Correct/incorrect is never shown per-question
 * (the backend deliberately withholds it — AnswerAckResponse has no
 * is_correct) — full results only appear after the whole attempt is
 * submitted, on the results view at the bottom of this file.
 *
 * Exams are quizzes with kind="exam" and a duration_minutes — same
 * attempt/answer/submit flow, plus a countdown that auto-submits whatever
 * has been answered so far when time runs out (a real quiz has no timer at
 * all: duration_minutes is null, so the countdown code below never mounts).
 */
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Button, IconButton, Screen, Text, TextField } from "../../components/ui";
import { radii, spacing } from "../../constants/theme";
import { quizzesApi } from "../../lib/api";
import type { Quiz, QuizAttemptResult } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function QuizAttemptScreen() {
  const { quizId } = useLocalSearchParams<{ quizId: string }>();
  const router = useRouter();
  const { colors } = useTheme();
  const { t } = useLanguage();

  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [questionStartedAt, setQuestionStartedAt] = useState<number>(Date.now());
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [examEndsAt, setExamEndsAt] = useState<number | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [timeUp, setTimeUp] = useState(false);
  const isFinalizingRef = useRef(false);

  useEffect(() => {
    Promise.all([quizzesApi.getQuiz(quizId), quizzesApi.startAttempt(quizId)])
      .then(([loadedQuiz, attempt]) => {
        setQuiz(loadedQuiz);
        setAttemptId(attempt.id);
        setQuestionStartedAt(Date.now());
        if (loadedQuiz.kind === "exam" && loadedQuiz.duration_minutes) {
          setExamEndsAt(Date.now() + loadedQuiz.duration_minutes * 60_000);
        }
      })
      .finally(() => setIsLoading(false));
  }, [quizId]);

  // Countdown tick — recomputed from the fixed end timestamp each second
  // rather than decremented, so it can't drift no matter how often this
  // effect re-runs.
  useEffect(() => {
    if (examEndsAt === null || result || timeUp) return;
    const tick = () => {
      const secondsLeft = Math.max(0, Math.round((examEndsAt - Date.now()) / 1000));
      setRemainingSeconds(secondsLeft);
      if (secondsLeft <= 0) setTimeUp(true);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [examEndsAt, result, timeUp]);

  const currentQuestion = quiz?.questions[currentIndex];
  const isLastQuestion = quiz ? currentIndex === quiz.questions.length - 1 : false;

  // Time ran out — best-effort submit whatever answer is currently on
  // screen, then finalize the attempt with however many questions actually
  // got answered.
  useEffect(() => {
    if (!timeUp || isFinalizingRef.current || !attemptId) return;
    isFinalizingRef.current = true;
    (async () => {
      if (currentAnswer.trim() && currentQuestion) {
        const timeSpentSeconds = Math.round((Date.now() - questionStartedAt) / 1000);
        await quizzesApi
          .submitAnswer(attemptId, { question_id: currentQuestion.id, answer: currentAnswer, time_spent_seconds: timeSpentSeconds })
          .catch(() => {});
      }
      const finalResult = await quizzesApi.submitAttempt(attemptId);
      setResult(finalResult);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeUp]);

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
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  if (result) {
    return <ResultsView result={result} onDone={() => router.back()} />;
  }

  if (timeUp) {
    return (
      <Screen>
        <View style={styles.loading}>
          <ActivityIndicator color={colors.accent} />
          <Text variant="body" style={{ marginTop: spacing.md, color: colors.textSecondary }}>
            {t("quiz.timeUp")}
          </Text>
        </View>
      </Screen>
    );
  }

  if (!currentQuestion) return null;

  const showsOptions = currentQuestion.options && currentQuestion.options.length > 0;

  return (
    <Screen>
      <View style={styles.progressRow}>
        <IconButton name="close" onPress={() => router.back()} size={40} />
        <View style={styles.segments}>
          {quiz.questions.map((_, i) => (
            <View
              key={i}
              style={[styles.segment, { backgroundColor: i <= currentIndex ? colors.accent : colors.border }]}
            />
          ))}
        </View>
        {remainingSeconds !== null ? <TimerChip seconds={remainingSeconds} /> : null}
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <Text variant="label" style={{ color: colors.accentDark }}>
          {t("quiz.questionOf", { current: currentIndex + 1, total: quiz.questions.length })}
        </Text>
        <Text variant="display" style={styles.question}>
          {currentQuestion.question}
        </Text>

        {showsOptions ? (
          <View style={styles.options}>
            {currentQuestion.options!.map((option) => {
              const selected = currentAnswer === option;
              return (
                <Pressable
                  key={option}
                  onPress={() => setCurrentAnswer(option)}
                  style={[
                    styles.optionRow,
                    {
                      backgroundColor: colors.surface,
                      shadowColor: colors.shadow,
                      borderColor: selected ? colors.accent : "transparent",
                    },
                  ]}
                >
                  <Text variant="body" style={{ fontWeight: selected ? "600" : "400" }}>
                    {option}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        ) : (
          <TextField
            placeholder={t("quiz.typeYourAnswer")}
            value={currentAnswer}
            onChangeText={setCurrentAnswer}
            multiline={currentQuestion.type === "short_answer"}
            style={styles.freeTextInput}
          />
        )}
      </ScrollView>

      <Button
        label={isLastQuestion ? t("quiz.finish") : t("quiz.continue")}
        onPress={handleContinue}
        loading={isSubmittingAnswer}
        disabled={!currentAnswer.trim()}
        style={styles.action}
      />
    </Screen>
  );
}

function TimerChip({ seconds }: { seconds: number }) {
  const { colors } = useTheme();
  const low = seconds <= 60;
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return (
    <View style={[styles.timerChip, { backgroundColor: low ? colors.errorLight : colors.surfaceAlt }]}>
      <Ionicons name="timer-outline" size={14} color={low ? colors.error : colors.textSecondary} />
      <Text style={{ fontVariant: ["tabular-nums"], color: low ? colors.error : colors.textSecondary, fontWeight: "600" }}>
        {mm}:{ss.toString().padStart(2, "0")}
      </Text>
    </View>
  );
}

function ResultsView({ result, onDone }: { result: QuizAttemptResult; onDone: () => void }) {
  const { colors } = useTheme();
  const { t } = useLanguage();
  const score = result.score !== null ? Math.round(result.score) : null;

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.resultsScroll}>
        <View style={styles.scoreWrap}>
          <View style={[styles.scoreRing, { borderColor: colors.accent, backgroundColor: colors.surface }]}>
            <Text variant="hero">{score !== null ? `${score}%` : "—"}</Text>
          </View>
          <Text variant="display" style={styles.scoreTitle}>
            {t("quiz.niceWork")}
          </Text>
        </View>

        {result.answers.map((answer) => (
          <View
            key={answer.question_id}
            style={[
              styles.resultCard,
              {
                backgroundColor: colors.surface,
                shadowColor: colors.shadow,
                borderLeftColor: answer.is_correct ? colors.sage : colors.error,
              },
            ]}
          >
            <View style={styles.resultHeader}>
              <Ionicons
                name={answer.is_correct ? "checkmark-circle" : "close-circle"}
                size={18}
                color={answer.is_correct ? colors.sage : colors.error}
              />
              <Text variant="body" style={styles.resultQuestion}>
                {answer.question}
              </Text>
            </View>
            <Text variant="caption" style={styles.resultLabel}>
              {t("quiz.yourAnswer", { answer: answer.student_answer ?? "—" })}
            </Text>
            {!answer.is_correct ? (
              <Text variant="caption" style={styles.resultLabel}>
                {t("quiz.correctAnswer", { answer: answer.correct_answer })}
              </Text>
            ) : null}
            {answer.explanation ? (
              <Text variant="caption" style={[styles.resultExplanation, { color: colors.textSecondary }]}>
                {answer.explanation}
              </Text>
            ) : null}
          </View>
        ))}
      </ScrollView>
      <Button label={t("quiz.done")} onPress={onDone} style={styles.action} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  progressRow: {
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  segments: {
    flex: 1,
    flexDirection: "row",
    gap: 5,
  },
  timerChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    height: 32,
    borderRadius: radii.full,
  },
  segment: {
    flex: 1,
    height: 6,
    borderRadius: radii.full,
  },
  body: {
    paddingBottom: spacing.xl,
  },
  question: {
    marginTop: spacing.md,
  },
  options: {
    marginTop: spacing.xl,
    gap: spacing.md,
  },
  optionRow: {
    borderRadius: radii.lg,
    borderWidth: 2,
    padding: spacing.lg,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 2,
  },
  freeTextInput: {
    marginTop: spacing.xl,
  },
  action: {
    marginBottom: 24,
  },
  resultsScroll: {
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  scoreWrap: {
    alignItems: "center",
    marginBottom: spacing.xl,
  },
  scoreRing: {
    width: 148,
    height: 148,
    borderRadius: radii.full,
    borderWidth: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  scoreTitle: {
    marginTop: spacing.lg,
  },
  resultCard: {
    marginTop: spacing.md,
    borderRadius: radii.lg,
    borderLeftWidth: 4,
    padding: spacing.lg,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 2,
  },
  resultHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
  },
  resultQuestion: {
    flex: 1,
  },
  resultLabel: {
    marginTop: spacing.sm,
  },
  resultExplanation: {
    marginTop: spacing.sm,
    fontStyle: "italic",
  },
});
