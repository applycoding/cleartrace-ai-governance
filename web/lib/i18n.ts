import en from "../locales/en/common.json";
import fr from "../locales/fr/common.json";

export type Locale = "en" | "fr";

export const resources = {
  en: { common: en },
  fr: { common: fr },
} as const;

export function resolveLocale(value: string | undefined): Locale {
  if (value?.startsWith("fr")) {
    return "fr";
  }
  return "en";
}

export function t(locale: Locale, key: string): string {
  const parts = key.split(".");
  let node: unknown = resources[locale].common;
  for (const part of parts) {
    if (typeof node !== "object" || node === null || !(part in node)) {
      return key;
    }
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : key;
}
