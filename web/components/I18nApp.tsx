"use client";

import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import type { Locale } from "../lib/i18n";
import { resolveLocale } from "../lib/i18n";

const STORAGE_KEY = "cleartrace.locale";

export function I18nApp({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setLocale(resolveLocale(stored));
    }
  }, []);

  const onLocaleChange = (next: Locale) => {
    setLocale(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.lang = next === "fr" ? "fr-CA" : "en-CA";
  };

  useEffect(() => {
    document.documentElement.lang = locale === "fr" ? "fr-CA" : "en-CA";
  }, [locale]);

  return (
    <AppShell locale={locale} onLocaleChange={onLocaleChange}>
      {children}
    </AppShell>
  );
}
