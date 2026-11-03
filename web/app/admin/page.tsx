"use client";

import { useEffect, useState } from "react";
import { fetchAdminSettings } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

export default function AdminPage() {
  const locale = useLocale();
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchAdminSettings().then(setSettings);
  }, []);

  return (
    <section data-testid="page-admin">
      <h1>{t(locale, "admin.heading")}</h1>
      <p>{t(locale, "admin.description")}</p>
      {settings ? (
        <ul>
          <li>
            {t(locale, "admin.webhooks")}: {String(settings.webhooks)}
          </li>
          <li>
            {t(locale, "admin.connectors")}: {String(settings.connectors)}
          </li>
          <li>
            {t(locale, "admin.localeDefault")}: {String(settings.locale_default)}
          </li>
        </ul>
      ) : (
        <p>{t(locale, "actions.loading")}</p>
      )}
    </section>
  );
}
