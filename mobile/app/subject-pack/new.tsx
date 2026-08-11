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
import { ActivityIndicator, Pressable, ScrollView, useColorScheme, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { accountApi, ApiError, curriculumApi, subjectPacksApi } from "../../lib/api";
import type { AcademicLevel, Country, CurriculumSubject, EducationSystem, Section } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";

type Step = "country" | "system" | "level" | "section" | "preview";

export default function SubjectPackPickerScreen() {
  const router = useRouter();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t, tn } = useLanguage();
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
      .catch(() => setError(t("subjectPack.loadCountriesError")))
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
      setError(t("subjectPack.loadSystemsError"));
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
      setError(t("subjectPack.loadLevelsError"));
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
      setError(t("subjectPack.loadLevelError"));
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
      setError(t("subjectPack.loadSubjectsError"));
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
        setError(t("subjectPack.duplicateError", { name: result.skipped_duplicate_names[0] }));
        return;
      }
      // Only remember this as the student's own classe during first-time
      // onboarding — the same picker reached from Settings' "add another
      // pack" is just adding subjects for a different level, not redoing
      // the student's own profile. Best-effort: a failure here shouldn't
      // block onboarding from proceeding.
      if ((returnTo ?? "/onboarding") === "/onboarding") {
        try {
          await accountApi.setClasse({ academicLevelId: level.id, sectionId: section?.id ?? null });
        } catch {
          // ignore — non-critical
        }
      }
      router.replace({ pathname: (returnTo ?? "/onboarding") as never, params: { packApplied: "1" } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("subjectPack.applyError"));
    } finally {
      setIsApplying(false);
    }
  }

  const STEP_COPY: Record<Step, { title: string; subtitle: string }> = {
    country: { title: t("subjectPack.stepCountryTitle"), subtitle: t("subjectPack.stepCountrySubtitle") },
    system: { title: t("subjectPack.stepSystemTitle"), subtitle: "" },
    level: { title: t("subjectPack.stepLevelTitle"), subtitle: t("subjectPack.stepLevelSubtitle") },
    section: { title: t("subjectPack.stepSectionTitle"), subtitle: "" },
    preview: { title: t("subjectPack.stepPreviewTitle"), subtitle: t("subjectPack.stepPreviewSubtitle") },
  };

  const { title, subtitle } = STEP_COPY[step];

  return (
    <Screen>
      <View className="mt-2">
        <IconButton name="chevron-back" onPress={goBack} />
      </View>
      <Text className="mt-6 text-3xl font-bold">{title}</Text>
      <Text className="mt-1 mb-8 text-muted-foreground">{subtitle}</Text>

      {error ? <Text className="mb-4 text-sm text-destructive">{error}</Text> : null}

      {isLoadingOptions ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
        </View>
      ) : (
        <ScrollView contentContainerClassName="gap-2 pb-16">
          {step === "country" &&
            (countries.length === 0 ? (
              <EmptyState text={t("subjectPack.noCountries")} />
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
                <EmptyState text={t("subjectPack.noSubjectsFound")} />
              ) : (
                previewSubjects.map((s) => (
                  <Card key={s.id} className="py-3">
                    <CardContent>
                      <Text>{s.name}</Text>
                    </CardContent>
                  </Card>
                ))
              )}
              <Button onPress={handleApply} disabled={isApplying || previewSubjects.length === 0} className="mt-4">
                {isApplying ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
                <Text>{tn("subjectPack.addSubjects", previewSubjects.length)}</Text>
              </Button>
            </>
          )}
        </ScrollView>
      )}
    </Screen>
  );
}

function OptionRow({ label, onPress }: { label: string; onPress: () => void }) {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  return (
    <Pressable onPress={onPress}>
      <Card className="py-3">
        <CardContent className="flex-row items-center justify-between">
          <Text>{label}</Text>
          <Ionicons name="chevron-forward" size={18} color={scheme.mutedForeground} />
        </CardContent>
      </Card>
    </Pressable>
  );
}

function EmptyState({ text }: { text: string }) {
  return <Text className="mt-8 text-center">{text}</Text>;
}
