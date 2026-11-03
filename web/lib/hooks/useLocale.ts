"use client";

import { useEffect, useState } from "react";
import type { Locale } from "../i18n";

export function useLocale(): Locale {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    const stored = window.localStorage.getItem("cleartrace.locale");
    if (stored) {
      setLocale(stored.startsWith("fr") ? "fr" : "en");
    }
    const onStorage = () => {
      const next = window.localStorage.getItem("cleartrace.locale");
      if (next) {
        setLocale(next.startsWith("fr") ? "fr" : "en");
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return locale;
}
