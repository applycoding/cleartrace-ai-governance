"use client";

import { useEffect, useState } from "react";
import { fetchFrameworks } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

export default function FrameworksPage() {
  const locale = useLocale();
  const [items, setItems] = useState<
    { id: string; code: string; version: string; coverage: number }[]
  >([]);

  useEffect(() => {
    fetchFrameworks().then((rows) => setItems(rows as typeof items));
  }, []);

  return (
    <section data-testid="page-frameworks">
      <h1>{t(locale, "frameworks.heading")}</h1>
      <p>{t(locale, "frameworks.description")}</p>
      <table>
        <thead>
          <tr>
            <th>{t(locale, "frameworks.columnCode")}</th>
            <th>{t(locale, "frameworks.columnVersion")}</th>
            <th>{t(locale, "frameworks.columnCoverage")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.id}>
              <td>{row.code}</td>
              <td>{row.version}</td>
              <td>{Math.round(row.coverage * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
