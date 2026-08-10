import { Ionicons } from "@expo/vector-icons";
import { useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";

import { radii, spacing } from "../../constants/theme";
import { useLanguage } from "../../lib/language-context";
import type { Language } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";
import { Text } from "./Text";

const MONTH_NAMES: Record<Language, string[]> = {
  en: [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ],
  fr: [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
  ],
  ar: [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
  ],
};

const WEEKDAY_NAMES: Record<Language, string[]> = {
  en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
  fr: ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"],
  ar: ["إث", "ثل", "أر", "خم", "جم", "سب", "أح"],
};

type Step = "year" | "month" | "day";

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

function parseISODate(value: string): { year: number; month: number; day: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  if (month < 0 || month > 11 || day < 1 || day > 31) return null;
  return { year, month, day };
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

/** Tap-to-open calendar date picker — replaces free-typed "YYYY-MM-DD" text
 * entry with year -> month -> day grids, ending in an actual calendar for
 * the day step. No native module dependency, so it works the same on iOS,
 * Android, and web. */
export function DatePickerField({
  label,
  value,
  onChange,
  placeholder,
  error,
  minYear,
  maxYear,
  style,
}: {
  label?: string;
  value: string; // "YYYY-MM-DD" or ""
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string | null;
  minYear?: number;
  maxYear?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const { language } = useLanguage();
  const monthNames = MONTH_NAMES[language] ?? MONTH_NAMES.en;
  const weekdayNames = WEEKDAY_NAMES[language] ?? WEEKDAY_NAMES.en;

  const today = useMemo(() => new Date(), []);
  const effectiveMaxYear = maxYear ?? today.getFullYear() - 3;
  const effectiveMinYear = minYear ?? today.getFullYear() - 120;

  const parsed = parseISODate(value);

  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState<Step>("year");
  const [viewYear, setViewYear] = useState(parsed?.year ?? effectiveMaxYear);
  const [viewMonth, setViewMonth] = useState(parsed?.month ?? 0);

  function open() {
    setViewYear(parsed?.year ?? effectiveMaxYear);
    setViewMonth(parsed?.month ?? 0);
    setStep(parsed ? "day" : "year");
    setVisible(true);
  }

  function selectYear(year: number) {
    setViewYear(year);
    setStep("month");
  }

  function selectMonth(month: number) {
    setViewMonth(month);
    setStep("day");
  }

  function selectDay(day: number) {
    onChange(`${viewYear}-${pad2(viewMonth + 1)}-${pad2(day)}`);
    setVisible(false);
  }

  const years: number[] = [];
  for (let y = effectiveMaxYear; y >= effectiveMinYear; y--) years.push(y);

  const firstWeekday = (new Date(viewYear, viewMonth, 1).getDay() + 6) % 7; // Monday-first
  const totalDays = daysInMonth(viewYear, viewMonth);
  const dayCells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: totalDays }, (_, i) => i + 1),
  ];

  const displayText = parsed ? `${parsed.day} ${monthNames[parsed.month]} ${parsed.year}` : "";

  return (
    <View style={style}>
      {label ? (
        <Text variant="label" style={styles.label}>
          {label}
        </Text>
      ) : null}
      <Pressable
        onPress={open}
        style={[
          styles.field,
          {
            backgroundColor: colors.surfaceAlt,
            borderColor: error ? colors.error : "transparent",
          },
        ]}
      >
        <Text variant="body" style={{ color: parsed ? colors.textPrimary : colors.textMuted }}>
          {displayText || placeholder}
        </Text>
        <Ionicons name="calendar-outline" size={20} color={colors.textSecondary} />
      </Pressable>
      {error ? (
        <Text variant="caption" style={[styles.error, { color: colors.error }]}>
          {error}
        </Text>
      ) : null}

      <Modal visible={visible} transparent animationType="fade" onRequestClose={() => setVisible(false)}>
        <Pressable style={styles.overlay} onPress={() => setVisible(false)}>
          <Pressable style={[styles.sheet, { backgroundColor: colors.surface }]} onPress={(e) => e.stopPropagation()}>
            <View style={styles.sheetHeader}>
              {step !== "year" ? (
                <Pressable onPress={() => setStep(step === "day" ? "month" : "year")} hitSlop={8}>
                  <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
                </Pressable>
              ) : (
                <View style={styles.headerSpacer} />
              )}
              <Text variant="subtitle">
                {step === "year" ? " " : step === "month" ? `${viewYear}` : `${monthNames[viewMonth]} ${viewYear}`}
              </Text>
              <Pressable onPress={() => setVisible(false)} hitSlop={8}>
                <Ionicons name="close" size={22} color={colors.textPrimary} />
              </Pressable>
            </View>

            {step === "year" && (
              <ScrollView style={styles.scrollArea}>
                <View style={styles.grid}>
                  {years.map((y) => (
                    <Pressable
                      key={y}
                      onPress={() => selectYear(y)}
                      style={[
                        styles.yearCell,
                        {
                          backgroundColor: y === parsed?.year ? colors.accent : colors.surfaceAlt,
                        },
                      ]}
                    >
                      <Text variant="body" style={{ color: y === parsed?.year ? colors.textOnAccent : colors.textPrimary }}>
                        {y}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </ScrollView>
            )}

            {step === "month" && (
              <View style={styles.grid}>
                {monthNames.map((name, index) => (
                  <Pressable
                    key={name}
                    onPress={() => selectMonth(index)}
                    style={[
                      styles.monthCell,
                      {
                        backgroundColor:
                          index === parsed?.month && viewYear === parsed?.year ? colors.accent : colors.surfaceAlt,
                      },
                    ]}
                  >
                    <Text
                      variant="body"
                      style={{
                        color:
                          index === parsed?.month && viewYear === parsed?.year ? colors.textOnAccent : colors.textPrimary,
                      }}
                    >
                      {name}
                    </Text>
                  </Pressable>
                ))}
              </View>
            )}

            {step === "day" && (
              <View>
                <View style={styles.weekdayRow}>
                  {weekdayNames.map((name) => (
                    <View key={name} style={styles.dayCell}>
                      <Text variant="caption">{name}</Text>
                    </View>
                  ))}
                </View>
                <View style={styles.dayGrid}>
                  {dayCells.map((day, index) => {
                    const isSelected =
                      day !== null && day === parsed?.day && viewMonth === parsed?.month && viewYear === parsed?.year;
                    return (
                      <View key={index} style={styles.dayCell}>
                        {day !== null ? (
                          <Pressable
                            onPress={() => selectDay(day)}
                            style={[
                              styles.dayButton,
                              { backgroundColor: isSelected ? colors.accent : "transparent" },
                            ]}
                          >
                            <Text variant="body" style={{ color: isSelected ? colors.textOnAccent : colors.textPrimary }}>
                              {day}
                            </Text>
                          </Pressable>
                        ) : null}
                      </View>
                    );
                  })}
                </View>
              </View>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    marginBottom: spacing.xs,
    marginLeft: spacing.sm,
  },
  field: {
    minHeight: 56,
    borderRadius: radii.full,
    borderWidth: 1.5,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  error: {
    marginTop: spacing.xs,
    marginLeft: spacing.sm,
  },
  overlay: {
    flex: 1,
    backgroundColor: "rgba(20,18,17,0.44)",
    justifyContent: "flex-end",
  },
  sheet: {
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.lg,
    maxHeight: "70%",
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.lg,
  },
  headerSpacer: {
    width: 22,
  },
  scrollArea: {
    maxHeight: 320,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    paddingBottom: spacing.md,
  },
  yearCell: {
    flexBasis: "22%",
    flexGrow: 1,
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    alignItems: "center",
  },
  monthCell: {
    flexBasis: "30%",
    flexGrow: 1,
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    alignItems: "center",
  },
  weekdayRow: {
    flexDirection: "row",
  },
  dayGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  dayCell: {
    width: `${100 / 7}%`,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.xs,
  },
  dayButton: {
    width: 36,
    height: 36,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
  },
});
