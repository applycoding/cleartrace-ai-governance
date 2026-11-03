"use client";

import { useState } from "react";
import { uploadEvidence } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

export default function EvidencePage() {
  const locale = useLocale();
  const [message, setMessage] = useState("");

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) return;
    const ok = await uploadEvidence(file);
    setMessage(ok ? t(locale, "evidence.success") : t(locale, "actions.loading"));
  };

  return (
    <section data-testid="page-evidence">
      <h1>{t(locale, "evidence.heading")}</h1>
      <p>{t(locale, "evidence.description")}</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="evidence-file">{t(locale, "evidence.fileLabel")}</label>
        <input id="evidence-file" name="file" type="file" required />
        <button type="submit">{t(locale, "actions.upload")}</button>
      </form>
      {message ? <p data-testid="evidence-message">{message}</p> : null}
    </section>
  );
}
