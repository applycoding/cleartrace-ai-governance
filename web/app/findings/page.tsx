"use client";

import { useEffect, useState } from "react";
import { fetchFindings } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

type Finding = {
  id: string;
  control_id: string;
  outcome: string;
  explanation: string;
  certainty: number;
};

export default function FindingsPage() {
  const locale = useLocale();
  const [items, setItems] = useState<Finding[]>([]);

  useEffect(() => {
    fetchFindings(locale).then((rows) => setItems(rows as Finding[]));
  }, [locale]);

  return (
    <section data-testid="page-findings">
      <h1>{t(locale, "findings.heading")}</h1>
      <p>{t(locale, "findings.description")}</p>
      <table>
        <thead>
          <tr>
            <th>{t(locale, "findings.columnControl")}</th>
            <th>{t(locale, "findings.columnOutcome")}</th>
            <th>{t(locale, "findings.columnExplanation")}</th>
            <th>{t(locale, "findings.columnCertainty")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.id}>
              <td>{row.control_id}</td>
              <td>{t(locale, `outcomes.${row.outcome}`)}</td>
              <td>{row.explanation}</td>
              <td>{row.certainty.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
