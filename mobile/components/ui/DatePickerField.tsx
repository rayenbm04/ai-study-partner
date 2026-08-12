import { CalendarBlankIcon, CaretLeftIcon, XIcon } from "phosphor-react-native";
import { useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, View, type StyleProp, type ViewStyle } from "react-native";

import { useLanguage } from "../../lib/language-context";
import type { Language } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";
import { Text } from "./text";

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
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
      {label ? <Text className="mb-1.5 ml-1 text-sm font-medium text-muted-foreground">{label}</Text> : null}
      <Pressable
        onPress={open}
        className={cn(
          "min-h-14 flex-row items-center justify-between rounded-full border bg-input/30 px-4",
          error ? "border-destructive" : "border-transparent"
        )}
      >
        <Text className={cn(parsed ? "text-foreground" : "text-muted-foreground")}>{displayText || placeholder}</Text>
        <CalendarBlankIcon size={20} color={scheme.mutedForeground} />
      </Pressable>
      {error ? <Text className="mt-1 ml-1 text-xs text-destructive">{error}</Text> : null}

      <Modal visible={visible} transparent animationType="fade" onRequestClose={() => setVisible(false)}>
        <Pressable className="flex-1 justify-end bg-black/40" onPress={() => setVisible(false)}>
          <Pressable
            className="max-h-[70%] rounded-t-2xl bg-popover p-5"
            onPress={(e) => e.stopPropagation()}
          >
            <View className="mb-5 flex-row items-center justify-between">
              {step !== "year" ? (
                <Pressable onPress={() => setStep(step === "day" ? "month" : "year")} hitSlop={8}>
                  <CaretLeftIcon size={22} color={scheme.foreground} />
                </Pressable>
              ) : (
                <View className="w-[22px]" />
              )}
              <Text className="text-base font-semibold">
                {step === "year" ? " " : step === "month" ? `${viewYear}` : `${monthNames[viewMonth]} ${viewYear}`}
              </Text>
              <Pressable onPress={() => setVisible(false)} hitSlop={8}>
                <XIcon size={22} color={scheme.foreground} />
              </Pressable>
            </View>

            {step === "year" && (
              <ScrollView className="max-h-80">
                <View className="flex-row flex-wrap gap-2 pb-4">
                  {years.map((y) => (
                    <Pressable
                      key={y}
                      onPress={() => selectYear(y)}
                      className={cn(
                        "grow basis-[22%] items-center rounded-lg py-3",
                        y === parsed?.year ? "bg-primary" : "bg-input/30"
                      )}
                    >
                      <Text className={y === parsed?.year ? "text-primary-foreground" : "text-foreground"}>{y}</Text>
                    </Pressable>
                  ))}
                </View>
              </ScrollView>
            )}

            {step === "month" && (
              <View className="flex-row flex-wrap gap-2 pb-4">
                {monthNames.map((name, index) => (
                  <Pressable
                    key={name}
                    onPress={() => selectMonth(index)}
                    className={cn(
                      "grow basis-[30%] items-center rounded-lg py-3",
                      index === parsed?.month && viewYear === parsed?.year ? "bg-primary" : "bg-input/30"
                    )}
                  >
                    <Text
                      className={
                        index === parsed?.month && viewYear === parsed?.year ? "text-primary-foreground" : "text-foreground"
                      }
                    >
                      {name}
                    </Text>
                  </Pressable>
                ))}
              </View>
            )}

            {step === "day" && (
              <View>
                <View className="flex-row">
                  {weekdayNames.map((name) => (
                    <View key={name} className="w-[14.28%] items-center justify-center py-1">
                      <Text className="text-xs text-muted-foreground">{name}</Text>
                    </View>
                  ))}
                </View>
                <View className="flex-row flex-wrap">
                  {dayCells.map((day, index) => {
                    const isSelected =
                      day !== null && day === parsed?.day && viewMonth === parsed?.month && viewYear === parsed?.year;
                    return (
                      <View key={index} className="w-[14.28%] items-center justify-center py-1">
                        {day !== null ? (
                          <Pressable
                            onPress={() => selectDay(day)}
                            className={cn(
                              "h-9 w-9 items-center justify-center rounded-full",
                              isSelected ? "bg-primary" : "bg-transparent"
                            )}
                          >
                            <Text className={isSelected ? "text-primary-foreground" : "text-foreground"}>{day}</Text>
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
