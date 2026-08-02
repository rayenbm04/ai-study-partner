/**
 * First-run setup: create the student's first subject, then ask how much
 * time they have to study daily. Two screens, not a chat-guided flow (see
 * design decision) — this maps directly onto real backend calls rather
 * than collecting "goal"/"level" answers the API has nowhere to store.
 *
 * The daily-minutes choice isn't persisted anywhere yet (there's no user
 * preferences endpoint on the backend) — it's carried forward as a param
 * into the Study Plan tab so it pre-fills the first plan-generation form
 * instead of being silently dropped. A real "default daily minutes" user
 * setting would be a small, separate backend addition later.
 */
import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Card, ProgressBar, Screen, Text, TextField } from "../components/ui";
import { colors, spacing } from "../constants/theme";
import { ApiError, subjectsApi } from "../lib/api";

const MINUTE_OPTIONS = [15, 30, 45, 60];

export default function OnboardingScreen() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [subjectName, setSubjectName] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState<number | null>(30);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleFinish() {
    setError(null);
    setIsSubmitting(true);
    try {
      await subjectsApi.createSubject({ name: subjectName.trim() });
      router.replace({ pathname: "/(tabs)/study-plan", params: { defaultDailyMinutes: String(dailyMinutes) } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create your subject. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.progress}>
        <ProgressBar total={2} completed={step} />
      </View>

      {step === 1 ? (
        <View style={styles.body}>
          <Text variant="display">What are you studying?</Text>
          <Text variant="body" style={styles.subtitle}>
            Give your first subject a name — you can add more later.
          </Text>
          <TextField
            label="Subject name"
            placeholder="e.g. Physics, Organic Chemistry, SAT Math"
            value={subjectName}
            onChangeText={setSubjectName}
            style={styles.field}
          />
          {error ? (
            <Text variant="caption" style={styles.error}>
              {error}
            </Text>
          ) : null}
          <Button
            label="Continue"
            onPress={() => setStep(2)}
            disabled={!subjectName.trim()}
            style={styles.action}
          />
        </View>
      ) : (
        <View style={styles.body}>
          <Text variant="display">How much time can you study daily?</Text>
          <Text variant="body" style={styles.subtitle}>
            This just sets a starting point for your study plan — easy to change later.
          </Text>
          <View style={styles.options}>
            {MINUTE_OPTIONS.map((minutes) => (
              <Card
                key={minutes}
                onPress={() => setDailyMinutes(minutes)}
                style={[styles.option, dailyMinutes === minutes && styles.optionSelected]}
              >
                <Text variant="title">{minutes} min</Text>
                <Text variant="caption">per day</Text>
              </Card>
            ))}
          </View>
          {error ? (
            <Text variant="caption" style={styles.error}>
              {error}
            </Text>
          ) : null}
          <Button label="Get started" onPress={handleFinish} loading={isSubmitting} style={styles.action} />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  progress: {
    marginTop: spacing.lg,
  },
  body: {
    marginTop: spacing.xxl,
  },
  subtitle: {
    marginTop: spacing.sm,
    marginBottom: spacing.xl,
  },
  field: {
    marginBottom: spacing.lg,
  },
  options: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  option: {
    width: "47%",
    alignItems: "center",
  },
  optionSelected: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  action: {
    marginTop: spacing.xl,
  },
  error: {
    marginBottom: spacing.md,
  },
});
