"use client";

import { useEffect, useState } from "react";
import { t, type Locale } from "../lib/i18n";

function useLocale(): Locale {
  const [locale, setLocale] = useState<Locale>("en");
  useEffect(() => {
    const stored = window.localStorage.getItem("cleartrace.locale");
    if (stored) {
      setLocale(stored.startsWith("fr") ? "fr" : "en");
    }
  }, []);
  return locale;
}

type Props = {
  headingKey: string;
  descriptionKey: string;
  testId: string;
};

export function SectionPage({ headingKey, descriptionKey, testId }: Props) {
  const locale = useLocale();
  return (
    <section data-testid={testId}>
      <h1>{t(locale, headingKey)}</h1>
      <p>{t(locale, descriptionKey)}</p>
    </section>
  );
}
