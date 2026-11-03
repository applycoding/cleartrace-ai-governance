"use client";

import { useEffect, useState } from "react";
import { fetchAuditEvents, verifyAuditLedger } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

type Event = { id: string; action: string; hash: string };

export default function AuditPage() {
  const locale = useLocale();
  const [events, setEvents] = useState<Event[]>([]);
  const [verifyMessage, setVerifyMessage] = useState("");

  useEffect(() => {
    fetchAuditEvents().then((rows) => setEvents(rows as Event[]));
  }, []);

  const onVerify = async () => {
    const result = await verifyAuditLedger();
    if (result && (result as { valid?: boolean }).valid) {
      setVerifyMessage(t(locale, "audit.verifyOk"));
    }
  };

  return (
    <section data-testid="page-audit">
      <h1>{t(locale, "audit.heading")}</h1>
      <p>{t(locale, "audit.description")}</p>
      <button type="button" onClick={onVerify}>
        {t(locale, "actions.verify")}
      </button>
      {verifyMessage ? <p data-testid="audit-verify">{verifyMessage}</p> : null}
      <table>
        <thead>
          <tr>
            <th>{t(locale, "audit.columnAction")}</th>
            <th>{t(locale, "audit.columnHash")}</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{event.action}</td>
              <td>{event.hash}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
