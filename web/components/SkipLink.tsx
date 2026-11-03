"use client";

import { t, type Locale } from "../lib/i18n";

type Props = { locale: Locale };

export function SkipLink({ locale }: Props) {
  return (
    <a href="#main-content" className="skip-link">
      {t(locale, "actions.skipToMain")}
    </a>
  );
}
