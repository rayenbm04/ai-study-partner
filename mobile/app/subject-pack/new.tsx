/**
 * Shared curriculum-pack picker, pushed from both onboarding ("use a pack")
 * and Settings ("add another pack") via a `returnTo` param. Drills
 * Country -> EducationSystem -> AcademicLevel -> Section (only if the level
 * has any -- an unsectioned level like "3eme" skips straight to subjects,
 * since GET .../subjects with no section_id would otherwise mix subjects
 * from every section together) -> a preview of the subjects that will be
 * added, then calls subjectPacksApi.applyPack and hands control back to
 * whichever screen pushed this one.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";

import { Button, Card, IconButton, Screen, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError, curriculumApi, subjectPacksApi } from "../../lib/api";
import type { AcademicLevel, Country, CurriculumSubject, EducationSystem, Section } from "../../lib/api";
import { useTheme } from "../../lib/theme-context";

type Step = "country" | "system" | "level" | "section" | "preview";

export default function SubjectPackPickerScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();

  const [step, setStep] = useState<Step>("country");
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);

  const [countries, setCountries] = useState<Country[]>([]);
  const [systems, setSystems] = useState<EducationSystem[]>([]);
  const [levels, setLevels] = useState<AcademicLevel[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [previewSubjects, setPreviewSubjects] = useState<CurriculumSubject[]>([]);

  const [country, setCountry] = useState<Country | null>(null);
  const [system, setSystem] = useState<EducationSystem | null>(null);
  const [level, setLevel] = useState<AcademicLevel | null>(null);
  const [section, setSection] = useState<Section | null>(null);

  useEffect(() => {
    setIsLoadingOptions(true);
    setError(null);
    curriculumApi
      .listCountries()
      .then(setCountries)
      .catch(() => setError("Couldn't load countries. Try again."))
      .finally(() => setIsLoadingOptions(false));
  }, []);

  function goBack() {
    setError(null);
    if (step === "country") {
      router.back();
    } else if (step === "system") {
      setStep("country");
    } else if (step === "level") {
      setStep("system");
    } else if (step === "section") {
      setStep("level");
    } else {
      setStep(sections.length > 0 ? "section" : "level");
    }
  }

  async function selectCountry(selected: Country) {
    setCountry(selected);
    setIsLoadingOptions(true);
    setError(null);
    try {
      setSystems(await curriculumApi.listEducationSystems(selected.id));
      setStep("system");
    } catch {
      setError("Couldn't load education systems. Try again.");
    } finally {
      setIsLoadingOptions(false);
    }
  }

  async function selectSystem(selected: EducationSystem) {
    setSystem(selected);
    setIsLoadingOptions(true);
    setError(null);
    try {
      setLevels(await curriculumApi.listAcademicLevels(selected.id));
      setStep("level");
    } catch {
      setError("Couldn't load academic levels. Try again.");
    } finally {
      setIsLoadingOptions(false);
    }
  }

  async function selectLevel(selected: AcademicLevel) {
    setLevel(selected);
    setIsLoadingOptions(true);
    setError(null);
    try {
      const levelSections = await curriculumApi.listSections(selected.id);
      setSections(levelSections);
      if (levelSections.length > 0) {
        setStep("section");
      } else {
        setSection(null);
        setPreviewSubjects(await curriculumApi.listCurriculumSubjects(selected.id));
        setStep("preview");
      }
    } catch {
      setError("Couldn't load this level. Try again.");
    } finally {
      setIsLoadingOptions(false);
    }
  }

  async function selectSection(selected: Section) {
    if (!level) return;
    setSection(selected);
    setIsLoadingOptions(true);
    setError(null);
    try {
      setPreviewSubjects(await curriculumApi.listCurriculumSubjects(level.id, selected.id));
      setStep("preview");
    } catch {
      setError("Couldn't load subjects. Try again.");
    } finally {
      setIsLoadingOptions(false);
    }
  }

  async function handleApply() {
    if (!level) return;
    setIsApplying(true);
    setError(null);
    try {
      const result = await subjectPacksApi.applyPack({ academicLevelId: level.id, sectionId: section?.id ?? null });
      if (result.created.length === 0) {
        // Every subject in this pack already exists under this name for the
        // user (active, or from a different pack that happens to share a
        // name) — nothing changed, so don't silently navigate away as if it
        // worked.
        setError(`You already have a subject named "${result.skipped_duplicate_names[0]}" — nothing was added.`);
        return;
      }
      router.replace({ pathname: (returnTo ?? "/onboarding") as never, params: { packApplied: "1" } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add this pack. Try again.");
    } finally {
      setIsApplying(false);
    }
  }

  const { title, subtitle } = STEP_COPY[step];

  return (
    <Screen>
      <View style={styles.headerRow}>
        <IconButton name="chevron-back" onPress={goBack} />
      </View>
      <Text variant="display" style={styles.title}>
        {title}
      </Text>
      <Text variant="body" style={[styles.subtitle, { color: colors.textSecondary }]}>
        {subtitle}
      </Text>

      {error ? (
        <Text variant="caption" style={[styles.error, { color: colors.error }]}>
          {error}
        </Text>
      ) : null}

      {isLoadingOptions ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.accent} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {step === "country" &&
            (countries.length === 0 ? (
              <EmptyState text="No countries in the catalog yet." />
            ) : (
              countries.map((c) => <OptionRow key={c.id} label={c.name} onPress={() => selectCountry(c)} />)
            ))}
          {step === "system" &&
            systems.map((s) => <OptionRow key={s.id} label={s.name} onPress={() => selectSystem(s)} />)}
          {step === "level" &&
            levels.map((lvl) => <OptionRow key={lvl.id} label={lvl.name} onPress={() => selectLevel(lvl)} />)}
          {step === "section" &&
            sections.map((s) => <OptionRow key={s.id} label={s.name} onPress={() => selectSection(s)} />)}
          {step === "preview" && (
            <>
              {previewSubjects.length === 0 ? (
                <EmptyState text="No subjects found for this selection." />
              ) : (
                previewSubjects.map((s) => (
                  <Card key={s.id} style={styles.previewCard}>
                    <Text variant="body">{s.name}</Text>
                  </Card>
                ))
              )}
              <Button
                label={`Add ${previewSubjects.length} subject${previewSubjects.length === 1 ? "" : "s"}`}
                onPress={handleApply}
                loading={isApplying}
                disabled={previewSubjects.length === 0}
                style={styles.applyButton}
              />
            </>
          )}
        </ScrollView>
      )}
    </Screen>
  );
}

const STEP_COPY: Record<Step, { title: string; subtitle: string }> = {
  country: { title: "Choose your country", subtitle: "We'll show the curriculum for your education system." },
  system: { title: "Choose your education system", subtitle: "" },
  level: { title: "Choose your year", subtitle: "e.g. Bac, 3eme" },
  section: { title: "Choose your section", subtitle: "" },
  preview: { title: "Ready to add", subtitle: "These subjects will be added to your account." },
};

function OptionRow({ label, onPress }: { label: string; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Card onPress={onPress} style={styles.optionCard}>
      <View style={styles.optionRow}>
        <Text variant="body">{label}</Text>
        <Ionicons name="chevron-forward" size={18} color={colors.textSecondary} />
      </View>
    </Card>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <Text variant="body" style={styles.empty}>
      {text}
    </Text>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    marginTop: spacing.sm,
  },
  title: {
    marginTop: spacing.lg,
  },
  subtitle: {
    marginTop: spacing.xs,
    marginBottom: spacing.xl,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  list: {
    paddingBottom: spacing.xxxl,
    gap: spacing.sm,
  },
  optionCard: {
    paddingVertical: spacing.md,
  },
  optionRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  previewCard: {
    paddingVertical: spacing.md,
  },
  applyButton: {
    marginTop: spacing.lg,
  },
  error: {
    marginBottom: spacing.md,
  },
  empty: {
    textAlign: "center",
    marginTop: spacing.xxl,
  },
});
