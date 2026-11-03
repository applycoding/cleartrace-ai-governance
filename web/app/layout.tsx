import type { Metadata } from "next";
import "./globals.css";
import { I18nApp } from "../components/I18nApp";

export const metadata: Metadata = {
  title: "ClearTrace",
  description: "AI governance platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-CA">
      <body>
        <I18nApp>{children}</I18nApp>
      </body>
    </html>
  );
}
