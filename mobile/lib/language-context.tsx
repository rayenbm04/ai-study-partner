/**
 * App-wide language setting (English/French/Arabic). Mirrors
 * theme-context.tsx: persisted via the same cross-platform `storage`
 * wrapper, exposed through a context + hook, manual choice wins over any
 * default.
 *
 * Arabic also flips layout direction. React Native's I18nManager flag is
 * stored natively and only takes full effect after a reload, so
 * setLanguage() applies translated text immediately but only requests the
 * RTL flip — callers should prompt the user to restart when
 * `restartRequired` comes back true.
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { I18nManager } from "react-native";

import { storage } from "./storage";
import { translations, type Language } from "./i18n/translations";

export type { Language };

// Exported so lib/api/client.ts can read the current language without a
// React import cycle — every request attaches it as X-App-Language so the
// backend can generate content (chat, quizzes, flashcards, summaries) in
// whatever language the UI is set to.
export const LANGUAGE_PREFERENCE_KEY = "language_preference";
const RTL_LANGUAGES: Language[] = ["ar"];

type TranslationVars = Record<string, string | number>;

type LanguageContextValue = {
  language: Language;
  isRTL: boolean;
  setLanguage: (language: Language) => boolean; // returns true if an app restart is needed to fully apply RTL
  t: (key: string, vars?: TranslationVars) => string;
  tn: (key: string, count: number, vars?: TranslationVars) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

function interpolate(template: string, vars?: TranslationVars): string {
  if (!vars) return template;
  return Object.entries(vars).reduce(
    (result, [name, value]) => result.replaceAll(`{{${name}}}`, String(value)),
    template
  );
}

function lookup(language: Language, key: string): unknown {
  const parts = key.split(".");
  let node: unknown = translations[language];
  for (const part of parts) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return node;
}

// I18nManager.isRTL is captured once at module load and never updates for
// the rest of the session, even after forceRTL() — comparing against it on
// every switch means a second switch (e.g. ar -> fr) sees the same stale
// "true" it saw on the first switch and wrongly reports RTL changed again on
// every subsequent switch, including between two LTR languages like fr <->
// en. Track the RTL-ness we've actually applied this session instead.
function syncNativeDirection(language: Language, appliedRTLRef: { current: boolean }): boolean {
  const wantsRTL = RTL_LANGUAGES.includes(language);
  if (appliedRTLRef.current === wantsRTL) return false;
  I18nManager.allowRTL(wantsRTL);
  I18nManager.forceRTL(wantsRTL);
  appliedRTLRef.current = wantsRTL;
  return true;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");
  const appliedRTLRef = useRef(I18nManager.isRTL);

  useEffect(() => {
    storage.getItem(LANGUAGE_PREFERENCE_KEY).then((stored) => {
      if (stored === "en" || stored === "fr" || stored === "ar") {
        setLanguageState(stored);
        syncNativeDirection(stored, appliedRTLRef);
      }
    });
  }, []);

  const value = useMemo<LanguageContextValue>(() => {
    const t = (key: string, vars?: TranslationVars): string => {
      const entry = lookup(language, key) ?? lookup("en", key);
      return typeof entry === "string" ? interpolate(entry, vars) : key;
    };

    const tn = (key: string, count: number, vars?: TranslationVars): string => {
      const entry = (lookup(language, key) ?? lookup("en", key)) as
        | { one?: string; other?: string }
        | undefined;
      const template = (count === 1 ? entry?.one : entry?.other) ?? entry?.other ?? key;
      return interpolate(template, { count, ...vars });
    };

    return {
      language,
      isRTL: RTL_LANGUAGES.includes(language),
      setLanguage: (next: Language) => {
        setLanguageState(next);
        storage.setItem(LANGUAGE_PREFERENCE_KEY, next);
        return syncNativeDirection(next, appliedRTLRef);
      },
      t,
      tn,
    };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage() must be used within a LanguageProvider");
  return ctx;
}
