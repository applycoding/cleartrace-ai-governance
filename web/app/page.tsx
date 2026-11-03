"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSystems } from "../lib/api/client";
import { useLocale } from "../lib/hooks/useLocale";
import { t } from "../lib/i18n";

export default function HomePage() {
  const locale = useLocale();
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    fetchSystems(locale)
      .then((systems) => setCount(systems.length))
      .catch(() => setCount(0));
  }, [locale]);

  return (
    <section>
      <h1>{t(locale, "home.welcome")}</h1>
      <p>{t(locale, "app.tagline")}</p>
      <p data-testid="systems-count">
        {count === null ? t(locale, "actions.loading") : count}
      </p>
      <Link href="/register" data-testid="home-cta">
        {t(locale, "home.cta")}
      </Link>
    </section>
  );
}
