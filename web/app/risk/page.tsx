"use client";

import { useEffect, useState } from "react";
import { fetchRiskSummary } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

export default function RiskPage() {
  const locale = useLocale();
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchRiskSummary().then(setSummary);
  }, []);

  return (
    <section data-testid="page-risk">
      <h1>{t(locale, "risk.heading")}</h1>
      <p>{t(locale, "risk.description")}</p>
      {summary ? (
        <ul>
          <li>
            {t(locale, "risk.binding")}: {String(summary.binding_breaches)}
          </li>
          <li>
            {t(locale, "risk.advisory")}: {String(summary.advisory_flags)}
          </li>
          <li>
            {t(locale, "risk.lastObservation")}: {String(summary.last_observation)}
          </li>
        </ul>
      ) : (
        <p>{t(locale, "actions.loading")}</p>
      )}
    </section>
  );
}
