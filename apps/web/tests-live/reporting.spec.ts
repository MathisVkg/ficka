import { test, expect } from "@playwright/test";
test("persisted entries drive dashboard and report totals without mixing status, dates or currency", async ({
  page,
  request,
}) => {
  const prefix = "E2E reporting " + crypto.randomUUID(),
    ids: { path: string; id: string }[] = [];
  async function create(path: string, data: Record<string, unknown>) {
    const response = await request.post("/api/v1/" + path, {
      data: {
        title: prefix,
        amount: "121.00",
        status: "paid",
        entry_date: "2020-01-05",
        payment_date: "2020-01-15",
        ...data,
      },
    });
    expect(response.status()).toBe(201);
    const value = await response.json();
    ids.push({ path, id: value.id });
    return value;
  }
  try {
    await create("income", {
      entry_date: "2019-12-31",
      vat_amount: "20.00",
      vat_rate: "21",
    });
    await create("expenses", {
      amount: "60.50",
      vat_amount: "10.50",
      vat_rate: "21",
      category_id: "00000000-0000-0000-0000-000000000004",
    });
    await create("expenses", { amount: "0.50", vat_rate: "0" });
    await create("income", {
      amount: "242.00",
      status: "pending",
      vat_rate: "21",
      payment_date: "2020-01-20",
    });
    await create("expenses", {
      amount: "12.10",
      status: "pending",
      vat_rate: "21",
      payment_date: "2020-02-01",
    });
    await create("income", { amount: "1000.00", status: "draft" });
    await create("income", { amount: "99.00", currency: "USD" });
    await create("expenses", {
      amount: "9.00",
      currency: "GBP",
      status: "pending",
    });
    const deleted = await create("expenses", { amount: "500.00" });
    await request.delete("/api/v1/expenses/" + deleted.id);
    const query = "date_from=2020-01-01&date_to=2020-01-31";
    const summary = await (
      await request.get("/api/v1/reports/summary?" + query)
    ).json();
    expect(summary.actual.income).toBe("121.00");
    expect(summary.actual.expenses).toBe("61.00");
    expect(summary.actual.net).toBe("60.00");
    expect(summary.expected.income).toBe("242.00");
    expect(summary.expected.expenses).toBe("0.00");
    expect(summary.vat.difference).toBe("29.40");
    expect(summary.non_eur_excluded_count).toBe(2);
    await page.goto("/");
    await page
      .getByLabel("Reporting period", { exact: true })
      .selectOption("custom");
    await page.getByLabel("Report start date").fill("2020-01-01");
    await page.getByLabel("Report end date").fill("2020-01-31");
    await page.getByRole("button", { name: "Apply range" }).click();
    await expect(page.getByTestId("kpi-income")).toContainText("€121.00");
    await expect(page.getByTestId("kpi-expenses")).toContainText("€61.00");
    await expect(page.getByTestId("kpi-net")).toContainText("€60.00");
    await expect(page.getByTestId("kpi-vat")).toContainText("€29.40");
    await expect(page.getByTestId("cash-flow-chart")).toBeVisible();
    await page.goto("/reports");
    await page
      .getByLabel("Reporting period", { exact: true })
      .selectOption("custom");
    await page.getByLabel("Report start date").fill("2020-01-01");
    await page.getByLabel("Report end date").fill("2020-01-31");
    await page.getByRole("button", { name: "Apply range" }).click();
    await expect(page.getByTestId("kpi-net")).toContainText("€60.00");
    await expect(page.getByTestId("expected-expenses")).toContainText("€0.00");
    await expect(
      page.getByRole("table", { name: "Expense category breakdown" }),
    ).toContainText("Uncategorized");
    await page.getByLabel("VAT reporting year").fill("2019");
    await expect(
      page.getByRole("table", { name: "Recorded VAT by quarter for 2019" }),
    ).toContainText("€20.00");
  } finally {
    for (const value of ids)
      await request.delete("/api/v1/" + value.path + "/" + value.id);
  }
});
