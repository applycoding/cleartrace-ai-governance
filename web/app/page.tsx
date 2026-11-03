"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSystems } from "../lib/api/client";
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

export default function HomePage() {
  const locale = useLocale();
  const [systems, setSystems] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    fetchSystems().then(setSystems).catch(() => setSystems([]));
  }, []);

  return (
    <section>
      <h1>{t(locale, "home.welcome")}</h1>
      <p>{t(locale, "app.tagline")}</p>
      <p data-testid="systems-count">
        {systems.length > 0 ? systems.length : t(locale, "actions.loading")}
      </p>
      <Link href="/register" data-testid="home-cta">
        {t(locale, "home.cta")}
      </Link>
    </section>
  );
}
