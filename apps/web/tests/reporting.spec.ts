import { test, expect, type Page } from "@playwright/test";
import { reportFixture } from "./helpers/report-fixtures";
async function mockReports(page: Page, populated = true, zeroNet = false) {
  const requests: URL[] = [];
  await page.route("**/api/health/ready", (route) =>
    route.fulfill({ json: { status: "ready" } }),
  );
  await page.route("**/api/v1/reports/**", (route) => {
    const url = new URL(route.request().url());
    requests.push(url);
    return route.fulfill({
      json: reportFixture(
        url.pathname.split("/").pop()!,
        url.searchParams,
        populated,
        zeroNet,
      ),
    });
  });
  return requests;
}
test("dashboard loads real-shaped totals and separates VAT and pending", async ({
  page,
}) => {
  await mockReports(page);
  await page.goto("/");
  await expect(page.getByTestId("kpi-income")).toContainText("€121.30");
  await expect(page.getByTestId("kpi-net")).toContainText("€60.80");
  await expect(page.getByTestId("kpi-vat")).toContainText("€9.50");
  await expect(page.getByTestId("cash-flow-chart")).toBeVisible();
  await expect(
    page.getByText("Pending client payment", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Overdue", { exact: false })).not.toHaveCount(0);
  await expect(
    page.getByText("2 non-EUR cash movements excluded.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Recorded difference · illustrative", { exact: true }),
  ).toBeVisible();
});
test("period controls update shared dates and cash-flow shortcuts", async ({
  page,
}) => {
  const requests = await mockReports(page);
  await page.goto("/");
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
  await page
    .getByLabel("Reporting period", { exact: true })
    .selectOption("quarter");
  await expect
    .poll(() => requests.filter((r) => r.pathname.endsWith("summary")).length)
    .toBeGreaterThan(1);
  const quarter = requests
    .filter((r) => r.pathname.endsWith("summary"))
    .at(-1)!;
  expect(["01", "04", "07", "10"]).toContain(
    quarter.searchParams.get("date_from")!.slice(5, 7),
  );
  await page.getByRole("button", { name: "6 months", exact: true }).click();
  await expect(
    page.getByLabel("Reporting period", { exact: true }),
  ).toHaveValue("6-months");
  await page.getByRole("button", { name: "12 months", exact: true }).click();
  await expect(
    page.getByLabel("Reporting period", { exact: true }),
  ).toHaveValue("12-months");
  await page.getByRole("button", { name: "Year to date", exact: true }).click();
  await expect(
    page.getByLabel("Reporting period", { exact: true }),
  ).toHaveValue("ytd");
  await page
    .getByLabel("Reporting period", { exact: true })
    .selectOption("custom");
  await page.getByLabel("Report start date").fill("2025-01-01");
  await page.getByLabel("Report end date").fill("2025-03-31");
  await page.getByRole("button", { name: "Apply range" }).click();
  await expect
    .poll(() =>
      requests.some(
        (r) =>
          r.pathname.endsWith("summary") &&
          r.searchParams.get("date_from") === "2025-01-01" &&
          r.searchParams.get("date_to") === "2025-03-31",
      ),
    )
    .toBeTruthy();
  for (const endpoint of ["summary", "cash-flow", "expense-categories"])
    await expect
      .poll(() =>
        requests.some(
          (r) =>
            r.pathname.endsWith(endpoint) &&
            r.searchParams.get("date_from") === "2025-01-01",
        ),
      )
      .toBeTruthy();
  expect(
    requests
      .filter((r) => r.pathname.endsWith("pending"))
      .every(
        (r) =>
          r.searchParams.get("scope") === "all" &&
          !r.searchParams.has("date_from"),
      ),
  ).toBeTruthy();
});
test("empty reports contain zero totals and compact honest chart states", async ({
  page,
}) => {
  await mockReports(page, false);
  await page.goto("/");
  await expect(page.getByTestId("kpi-income")).toContainText("€0.00");
  await expect(
    page.getByRole("heading", {
      name: "No actual cash movements in this period",
    }),
  ).toBeVisible();
  await expect(page.getByTestId("cash-flow-chart")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "No paid EUR expenses in this period" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "No pending EUR movements" }),
  ).toBeVisible();
  await page.goto("/reports");
  await expect(page.getByTestId("kpi-net")).toContainText("€0.00");
  await expect(
    page.getByRole("table", { name: /Recorded VAT by quarter/ }),
  ).toContainText("€0.00");
});
test("reports filter grouping, expected view, independent VAT year and pending", async ({
  page,
}) => {
  const requests = await mockReports(page);
  await page.goto("/reports");
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
  await expect(page.getByTestId("expected-income")).toContainText("242.00");
  await page.getByLabel("Cash-flow grouping").selectOption("week");
  await page.getByLabel("Cash-flow basis").selectOption("expected");
  await expect
    .poll(() =>
      requests.some(
        (r) =>
          r.searchParams.get("grouping") === "week" &&
          r.searchParams.get("basis") === "expected",
      ),
    )
    .toBeTruthy();
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
  await page.getByLabel("VAT reporting year").fill("2025");
  await expect
    .poll(() =>
      requests.some(
        (r) =>
          r.pathname.endsWith("vat") && r.searchParams.get("year") === "2025",
      ),
    )
    .toBeTruthy();
  await expect(
    page.getByRole("table", { name: "Recorded VAT by quarter for 2025" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Illustrative recorded difference, not VAT payable or a refund.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Pending movements", exact: true }),
  ).toBeVisible();
});
test("report errors preserve layout and retry replaces unavailable totals", async ({
  page,
}) => {
  await mockReports(page);
  let failed = true;
  await page.route("**/api/v1/reports/**", (route) =>
    failed
      ? route.fulfill({
          status: 503,
          json: { error: { message: "Reporting database unavailable" } },
        })
      : route.fallback(),
  );
  await page.goto("/reports");
  await expect(page.locator(".report-error")).toContainText(
    "Reporting database unavailable",
  );
  await expect(
    page.getByRole("heading", { name: "Reports", exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("kpi-income")).toContainText("—");
  failed = false;
  await page
    .getByRole("button", { name: "Retry reports", exact: true })
    .click();
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
  await expect(page.locator(".report-error")).toHaveCount(0);
});
test("genuine zero net remains visible with financial activity", async ({
  page,
}) => {
  await mockReports(page, true, true);
  await page.goto("/");
  await expect(page.getByTestId("kpi-net")).toContainText("€0.00");
  await expect(page.getByTestId("cash-flow-chart")).toBeVisible();
});
test("pending movement links open the corresponding saved entry", async ({
  page,
}) => {
  await mockReports(page);
  const entry = {
    id: "11111111-1111-4111-8111-111111111111",
    type: "income",
    title: "Pending client payment",
    amount: "242.00",
    currency: "EUR",
    country: "BE",
    category: null,
    category_id: null,
    counterparty: null,
    entry_date: "2026-01-01",
    payment_date: "2026-01-15",
    status: "pending",
    vat_rate: "21.0000",
    vat_amount: "42.00",
    amount_excluding_vat: "200.00",
    vat_overridden: false,
    notes: null,
    created_at: "2026-01-01T10:00:00Z",
    updated_at: "2026-01-01T10:00:00Z",
  };
  await page.route("**/api/v1/income**", (route) =>
    route.fulfill({
      json: new URL(route.request().url()).pathname.endsWith(entry.id)
        ? entry
        : { items: [entry], total: 1, page: 1, page_size: 20 },
    }),
  );
  await page.route("**/api/v1/categories**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/");
  await page
    .getByRole("link", { name: "Pending client payment", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Pending client payment",
  );
  await expect(page).toHaveURL(/income#entry=/);
});
test("populated dashboard and reports fit all required viewport widths", async ({
  page,
}) => {
  await mockReports(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const width of [1920, 1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const path of ["/", "/reports"]) {
      await page.goto(path);
      await expect(page.getByTestId("cash-flow-chart")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      const bounds = await page.locator("main").boundingBox();
      expect(Math.abs(bounds!.x + bounds!.width - width)).toBeLessThan(2);
      expect(await page.locator("main").innerText()).not.toMatch(
        /NaN|Infinity/,
      );
    }
  }
  expect(errors).toEqual([]);
});

test("report money preserves grouping, large exact values and negative cents", async ({
  page,
}) => {
  await mockReports(page);
  await page.route("**/api/v1/reports/summary?**", (route) => {
    const url = new URL(route.request().url());
    const report = reportFixture("summary", url.searchParams, true) as {
      actual: { income: string; expenses: string; net: string };
    };
    report.actual.income = "1234567890123456.78";
    report.actual.expenses = "1234567890123457.00";
    report.actual.net = "-0.22";
    return route.fulfill({ json: report });
  });
  await page.goto("/");
  await expect(page.getByTestId("kpi-income")).toContainText(
    "€1,234,567,890,123,456.78",
  );
  await expect(page.getByTestId("kpi-net")).toContainText("−€0.22");
});
test("a new period hides old totals while the replacement is loading", async ({
  page,
}) => {
  await mockReports(page);
  await page.goto("/");
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/reports/summary?**", async (route) => {
    await gate;
    await route.fallback();
  });
  try {
    await page
      .getByLabel("Reporting period", { exact: true })
      .selectOption("last-month");
    await expect(page.getByTestId("kpi-income")).toContainText("…");
    await expect(page.getByTestId("kpi-income")).not.toContainText("121.30");
  } finally {
    release();
  }
  await expect(page.getByTestId("kpi-income")).toContainText("121.30");
});
