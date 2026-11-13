import { test, expect } from "@playwright/test";
test("all navigation routes share the shell", async ({ page, isMobile }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Financial overview").getByLabel("No data"),
  ).toHaveCount(4);
  for (const label of [
    "Income",
    "Expenses",
    "Recurring",
    "Reports",
    "Settings",
    "Dashboard",
  ]) {
    if (isMobile)
      await page.getByRole("button", { name: "Open navigation" }).click();
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: label, exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: label, exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});
test("connection failure stays in the shell and can be retried", async ({
  page,
}) => {
  await page.route("**/api/health/ready", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText(
    "API or database unavailable",
  );
  await expect(
    page.getByRole("heading", { name: "Cash flow", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/health/ready");
  await page.route("**/api/health/ready", (route) =>
    route.fulfill({ json: { status: "ready" } }),
  );
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("status")).toContainText("All systems connected");
});
