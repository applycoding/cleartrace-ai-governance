import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const routes = [
  "/",
  "/register",
  "/frameworks",
  "/findings",
  "/review",
  "/evidence",
  "/risk",
  "/audit",
  "/admin",
];

async function switchToFrench(page: import("@playwright/test").Page) {
  await page.getByTestId("language-switch").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr-CA");
}

for (const route of routes) {
  test(`EN journey ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("html")).toHaveAttribute("lang", "en-CA");
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test(`FR journey ${route}`, async ({ page }) => {
    await page.goto(route);
    await switchToFrench(page);
    await expect(page.getByRole("navigation")).toBeVisible();
  });
}

test("axe scan on home EN", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(serious).toEqual([]);
});

test("axe scan on home FR", async ({ page }) => {
  await page.goto("/");
  await switchToFrench(page);
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(serious).toEqual([]);
});
