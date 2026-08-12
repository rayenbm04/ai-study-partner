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
import { ActivityIndicator, Pressable, ScrollView, View } from "react-native";
import { CheckCircleIcon, TimerIcon, XCircleIcon, XIcon } from "phosphor-react-native";

import { Button } from "../../components/ui/button";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { TextField } from "../../components/ui/TextField";
import { quizzesApi } from "../../lib/api";
import type { Quiz, QuizAttemptResult } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

export default function QuizAttemptScreen() {
  const { quizId } = useLocalSearchParams<{ quizId: string }>();
  const router = useRouter();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
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
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
          <Text className="mt-3 text-muted-foreground">{t("quiz.timeUp")}</Text>
        </View>
      </Screen>
    );
  }

  if (!currentQuestion) return null;

  const showsOptions = currentQuestion.options && currentQuestion.options.length > 0;

  return (
    <Screen>
      <View className="mt-2 mb-6 flex-row items-center gap-3">
        <IconButton icon={XIcon} onPress={() => router.back()} size={40} />
        <View className="flex-1 flex-row gap-1.5">
          {quiz.questions.map((_, i) => (
            <View key={i} className={cn("h-1.5 flex-1 rounded-full", i <= currentIndex ? "bg-primary" : "bg-border")} />
          ))}
        </View>
        {remainingSeconds !== null ? <TimerChip seconds={remainingSeconds} /> : null}
      </View>

      <ScrollView contentContainerClassName="pb-8">
        <Text className="text-sm font-medium text-primary">
          {t("quiz.questionOf", { current: currentIndex + 1, total: quiz.questions.length })}
        </Text>
        <Text className="mt-3 text-3xl font-bold">{currentQuestion.question}</Text>

        {showsOptions ? (
          <View className="mt-8 gap-3">
            {currentQuestion.options!.map((option) => {
              const selected = currentAnswer === option;
              return (
                <Pressable
                  key={option}
                  onPress={() => setCurrentAnswer(option)}
                  className={cn(
                    "rounded-xl border-2 p-5 shadow-sm shadow-black/5",
                    selected ? "border-primary bg-card" : "border-transparent bg-card"
                  )}
                >
                  <Text className={cn(selected && "font-semibold")}>{option}</Text>
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
            className="mt-8"
          />
        )}
      </ScrollView>

      <Button onPress={handleContinue} disabled={isSubmittingAnswer || !currentAnswer.trim()} className="mb-6">
        {isSubmittingAnswer ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
        <Text>{isLastQuestion ? t("quiz.finish") : t("quiz.continue")}</Text>
      </Button>
    </Screen>
  );
}

function TimerChip({ seconds }: { seconds: number }) {
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  const low = seconds <= 60;
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return (
    <View className={cn("h-8 flex-row items-center gap-1.5 rounded-full px-3", low ? "bg-destructive/10" : "bg-input/30")}>
      <TimerIcon size={14} color={low ? scheme.destructive : scheme.mutedForeground} />
      <Text className={cn("font-semibold", low ? "text-destructive" : "text-muted-foreground")} style={{ fontVariant: ["tabular-nums"] }}>
        {mm}:{ss.toString().padStart(2, "0")}
      </Text>
    </View>
  );
}

function ResultsView({ result, onDone }: { result: QuizAttemptResult; onDone: () => void }) {
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  const { t } = useLanguage();
  const score = result.score !== null ? Math.round(result.score) : null;

  return (
    <Screen>
      <ScrollView contentContainerClassName="pt-6 pb-8">
        <View className="mb-8 items-center">
          <View className="size-37 items-center justify-center rounded-full border-8 border-primary bg-card">
            <Text className="text-4xl font-extrabold">{score !== null ? `${score}%` : "—"}</Text>
          </View>
          <Text className="mt-6 text-3xl font-bold">{t("quiz.niceWork")}</Text>
        </View>

        {result.answers.map((answer) => (
          <View
            key={answer.question_id}
            className={cn(
              "mt-3 rounded-xl border-l-4 bg-card p-5 shadow-sm shadow-black/5",
              answer.is_correct ? "border-l-emerald-500" : "border-l-destructive"
            )}
          >
            <View className="flex-row items-start gap-2">
              {answer.is_correct ? (
                <CheckCircleIcon size={18} color="#10b981" weight="fill" />
              ) : (
                <XCircleIcon size={18} color={scheme.destructive} weight="fill" />
              )}
              <Text className="flex-1">{answer.question}</Text>
            </View>
            <Text className="mt-2 text-xs text-muted-foreground">{t("quiz.yourAnswer", { answer: answer.student_answer ?? "—" })}</Text>
            {!answer.is_correct ? (
              <Text className="mt-2 text-xs text-muted-foreground">{t("quiz.correctAnswer", { answer: answer.correct_answer })}</Text>
            ) : null}
            {answer.explanation ? <Text className="mt-2 text-xs text-muted-foreground italic">{answer.explanation}</Text> : null}
          </View>
        ))}
      </ScrollView>
      <Button onPress={onDone} className="mb-6">
        <Text>{t("quiz.done")}</Text>
      </Button>
    </Screen>
  );
}
