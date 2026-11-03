"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSystems, type SystemRow } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

export default function RegisterPage() {
  const locale = useLocale();
  const [systems, setSystems] = useState<SystemRow[]>([]);

  useEffect(() => {
    fetchSystems(locale).then(setSystems);
  }, [locale]);

  return (
    <section data-testid="page-register">
      <h1>{t(locale, "register.heading")}</h1>
      <p>{t(locale, "register.description")}</p>
      {systems.length === 0 ? (
        <p>{t(locale, "register.empty")}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t(locale, "register.columnKey")}</th>
              <th>{t(locale, "register.columnName")}</th>
              <th>{t(locale, "register.columnCategory")}</th>
              <th>{t(locale, "register.columnStatus")}</th>
            </tr>
          </thead>
          <tbody>
            {systems.map((system) => (
              <tr key={system.id}>
                <td>
                  <Link href={`/register/${system.id}`}>{system.key}</Link>
                </td>
                <td>{system.name}</td>
                <td>{system.category}</td>
                <td>{system.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
