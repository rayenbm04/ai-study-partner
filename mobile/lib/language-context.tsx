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
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { I18nManager } from "react-native";

import { storage } from "./storage";
import { translations, type Language } from "./i18n/translations";

export type { Language };

const LANGUAGE_PREFERENCE_KEY = "language_preference";
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

function syncNativeDirection(language: Language): boolean {
  const wantsRTL = RTL_LANGUAGES.includes(language);
  if (I18nManager.isRTL === wantsRTL) return false;
  I18nManager.allowRTL(wantsRTL);
  I18nManager.forceRTL(wantsRTL);
  return true;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    storage.getItem(LANGUAGE_PREFERENCE_KEY).then((stored) => {
      if (stored === "en" || stored === "fr" || stored === "ar") {
        setLanguageState(stored);
        syncNativeDirection(stored);
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
        return syncNativeDirection(next);
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
