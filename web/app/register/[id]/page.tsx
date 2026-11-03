"use client";

import { useEffect, useState } from "react";
import { fetchSystem } from "../../../lib/api/client";
import { useLocale } from "../../../lib/hooks/useLocale";
import { t } from "../../../lib/i18n";

type Props = { params: Promise<{ id: string }> };

export default function RegisterDetailPage({ params }: Props) {
  const locale = useLocale();
  const [system, setSystem] = useState<Record<string, unknown> | null>(null);
  const [id, setId] = useState<string>("");

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      fetchSystem(locale, p.id).then(setSystem);
    });
  }, [locale, params]);

  return (
    <section data-testid="page-register-detail">
      <h1>{t(locale, "register.detailHeading")}</h1>
      <p>{t(locale, "register.detailDescription")}</p>
      {system ? (
        <dl>
          <dt>{t(locale, "register.columnKey")}</dt>
          <dd>{String(system.key)}</dd>
          <dt>{t(locale, "register.columnName")}</dt>
          <dd>{String(system.name)}</dd>
          <dt>{t(locale, "register.columnStatus")}</dt>
          <dd>{String(system.status)}</dd>
        </dl>
      ) : (
        <p>{t(locale, "actions.loading")}</p>
      )}
      <input type="hidden" value={id} readOnly />
    </section>
  );
}
