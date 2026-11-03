"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SkipLink } from "./SkipLink";
import type { Locale } from "../lib/i18n";
import { t } from "../lib/i18n";

const links = [
  { href: "/register", key: "nav.register" },
  { href: "/frameworks", key: "nav.frameworks" },
  { href: "/findings", key: "nav.findings" },
  { href: "/review", key: "nav.review" },
  { href: "/evidence", key: "nav.evidence" },
  { href: "/risk", key: "nav.risk" },
  { href: "/audit", key: "nav.audit" },
  { href: "/admin", key: "nav.admin" },
] as const;

type Props = {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  children: React.ReactNode;
};

export function AppShell({ locale, onLocaleChange, children }: Props) {
  const pathname = usePathname();
  return (
    <div>
      <SkipLink locale={locale} />
      <header style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <strong>{t(locale, "app.title")}</strong>
          <span style={{ color: "#555" }}>{t(locale, "app.tagline")}</span>
          <button
            type="button"
            data-testid="language-switch"
            onClick={() => onLocaleChange(locale === "en" ? "fr" : "en")}
          >
            {t(locale, "actions.switchLanguage")}
          </button>
        </div>
        <nav aria-label="Main" style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
            >
              {t(locale, link.key)}
            </Link>
          ))}
        </nav>
      </header>
      <main id="main-content" style={{ padding: "1.5rem" }}>
        {children}
      </main>
    </div>
  );
}
