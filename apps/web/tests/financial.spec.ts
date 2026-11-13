import { test, expect, type Page } from "@playwright/test";
import { reportFixture } from "./helpers/report-fixtures";
const cat = {
  id: "00000000-0000-0000-0000-000000000001",
  name: "Services",
  type: "income",
  color: "#7250c9",
  active: true,
};
const entry = {
  id: "11111111-1111-4111-8111-111111111111",
  type: "income",
  title: "Design project",
  amount: "121.00",
  currency: "EUR",
  country: "BE",
  category_id: cat.id,
  category: cat,
  counterparty: "Studio",
  entry_date: "2026-01-05",
  payment_date: "2026-01-20",
  status: "pending",
  vat_rate: "21.0000",
  vat_amount: "21.00",
  vat_overridden: false,
  amount_excluding_vat: "100.00",
  notes: "",
  created_at: "2026-01-05T10:00:00Z",
  updated_at: "2026-01-05T10:00:00Z",
};
async function mockApi(page: Page, populated = false) {
  let saved: typeof entry | null = populated ? { ...entry } : null;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (url.pathname.includes("/reports/"))
      return route.fulfill({
        json: reportFixture(url.pathname.split("/").pop()!, url.searchParams),
      });
    if (url.pathname.endsWith("/categories"))
      return route.fulfill({ json: [cat] });
    if (request.method() === "DELETE") {
      saved = null;
      return route.fulfill({ status: 204 });
    }
    if (["POST", "PATCH"].includes(request.method())) {
      saved = { ...entry, ...request.postDataJSON() };
      return route.fulfill({
        status: request.method() === "POST" ? 201 : 200,
        json: saved,
      });
    }
    if (url.pathname.endsWith(entry.id)) return route.fulfill({ json: saved });
    return route.fulfill({
      json: {
        items: saved ? [saved] : [],
        total: saved ? 1 : 0,
        page: 1,
        page_size: 20,
      },
    });
  });
}
test("creation validates, synchronizes dates, preserves custom dates and warns on close", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/income");
  await page
    .getByRole("button", { name: "New income", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Create income" }).click();
  await expect(dialog.getByText("Enter a title.")).toBeVisible();
  await dialog.getByLabel("Title").fill("Test income");
  await dialog.getByLabel("Amount including VAT").fill("121.00");
  await dialog.getByLabel("Entry date").fill("2026-01-03");
  await expect(dialog.getByLabel("Payment date", { exact: false })).toHaveValue(
    "2026-01-03",
  );
  await dialog.getByLabel("Payment date", { exact: false }).fill("2026-01-15");
  await dialog.getByLabel("Entry date").fill("2026-01-04");
  await expect(dialog.getByLabel("Payment date", { exact: false })).toHaveValue(
    "2026-01-15",
  );
  await dialog.getByRole("button", { name: "Match entry date" }).click();
  await expect(dialog.getByLabel("Payment date", { exact: false })).toHaveValue(
    "2026-01-04",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.getByRole("button", { name: "Keep working" }).click();
  await expect(dialog.getByLabel("Title")).toHaveValue("Test income");
  await dialog.getByText("VAT and additional details", { exact: true }).click();
  await dialog.getByLabel("VAT preset").selectOption("21");
  await expect(dialog.locator(".vat-preview")).toContainText("100.00 EUR");
  await dialog.getByRole("button", { name: "Create income" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Test income", exact: true }),
  ).toBeVisible();
});
test("editing preserves saved payment date, confirms received date, and soft-deletes with confirmation", async ({
  page,
}) => {
  await mockApi(page, true);
  await page.goto("/income");
  await page
    .getByRole("button", { name: "Edit Design project", exact: true })
    .click();
  let dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Payment date", { exact: false })).toHaveValue(
    "2026-01-20",
  );
  await dialog.getByLabel("Entry date").fill("2026-01-07");
  await expect(dialog.getByLabel("Payment date", { exact: false })).toHaveValue(
    "2026-01-20",
  );
  await dialog.getByRole("button", { name: "Save changes" }).click();
  if (test.info().project.name === "mobile") {
    await page
      .getByRole("button", { name: "Edit Design project", exact: true })
      .click();
    await page.getByRole("dialog").getByLabel("Status").selectOption("paid");
  } else
    await page
      .getByRole("button", {
        name: "Mark received: Design project",
        exact: true,
      })
      .click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel("Actual payment date").fill("2026-01-21");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "Design project" }),
  ).toContainText("Received");
  await page
    .getByRole("button", { name: "Delete Design project", exact: true })
    .click();
  await expect(page.getByRole("alertdialog")).toContainText(
    "retained in the database",
  );
  await page.getByRole("button", { name: "Keep working" }).click();
  await expect(
    page.getByRole("button", { name: "Design project", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Delete Design project", exact: true })
    .click();
  await page.getByRole("button", { name: "Delete entry", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A clear record starts here" }),
  ).toBeVisible();
});
test("save errors preserve expense form input", async ({ page }) => {
  await mockApi(page);
  await page.goto("/expenses");
  await page
    .getByRole("button", { name: "New expense", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Title").fill("Office supplies");
  await dialog.getByLabel("Amount including VAT").fill("42.00");
  await page.route("**/api/v1/expenses", (route) =>
    route.fulfill({
      status: 503,
      json: { error: { message: "Database temporarily unavailable" } },
    }),
  );
  await dialog.getByRole("button", { name: "Create expense" }).click();
  await expect(dialog.getByRole("alert")).toContainText(
    "Database temporarily unavailable",
  );
  await expect(dialog.getByLabel("Title")).toHaveValue("Office supplies");
  await expect(dialog.getByLabel("Amount including VAT")).toHaveValue("42.00");
  await expect(
    dialog.getByRole("button", { name: "Create expense" }),
  ).toBeEnabled();
});
test("fluid layouts at all requested widths", async ({ page }) => {
  await mockApi(page, true);
  for (const width of [1920, 1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const path of ["/", "/income", "/expenses", "/settings"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const bounds = await page.locator("main").boundingBox();
      expect(bounds).not.toBeNull();
      expect(Math.abs(bounds!.x + bounds!.width - width)).toBeLessThan(2);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBeTruthy();
    }
    await page.goto("/income");
    await page
      .getByRole("button", { name: "New income", exact: true })
      .first()
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const bounds = await dialog.boundingBox();
    expect(Math.abs(bounds!.x + bounds!.width / 2 - width / 2)).toBeLessThan(2);
    await expect(
      dialog.getByRole("button", { name: "Create income" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});

test("invalid total with a VAT override stays in inline validation", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/expenses");
  await page
    .getByRole("button", { name: "New expense", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Title").fill("Validation example");
  await dialog.getByLabel("Amount including VAT").fill("invalid");
  await dialog.getByText("VAT and additional details", { exact: true }).click();
  await dialog.getByLabel("VAT amount override").fill("1.00");
  await dialog
    .getByRole("button", { name: "Create expense", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText(
    "Check the highlighted values",
  );
  await expect(dialog.getByLabel("Amount including VAT")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await dialog.getByLabel("Title").focus();
  for (let i = 0; i < 22; i++) {
    await page.keyboard.press("Tab");
    expect(
      await dialog.evaluate((node) => node.contains(document.activeElement)),
    ).toBeTruthy();
  }
});

test("saving disables entry editing and duplicate submission", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/income");
  await page
    .getByRole("button", { name: "New income", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Title").fill("Slow save");
  await dialog.getByLabel("Amount including VAT").fill("10.00");
  let release!: () => void;
  let posts = 0;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/income", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    posts++;
    await gate;
    await route.fulfill({
      status: 201,
      json: { ...entry, title: "Slow save" },
    });
  });
  try {
    await dialog
      .getByRole("button", { name: "Create income", exact: true })
      .click();
    await expect(
      dialog.getByRole("button", { name: "Saving…", exact: true }),
    ).toBeDisabled();
    await expect(dialog.getByLabel("Title")).toBeDisabled();
    await dialog.locator("form").dispatchEvent("submit");
    expect(posts).toBe(1);
  } finally {
    release();
  }
  await expect(dialog).toHaveCount(0);
});

test("currency display preserves the stored two-decimal precision", async ({
  page,
}) => {
  await mockApi(page);
  await page.route("**/api/v1/income?**", (route) =>
    route.fulfill({
      json: {
        items: [{ ...entry, amount: "0.50", currency: "JPY" }],
        total: 1,
        page: 1,
        page_size: 20,
      },
    }),
  );
  await page.goto("/income");
  await expect(
    page
      .getByRole("row")
      .filter({ hasText: "Design project" })
      .locator(".amount-column"),
  ).toContainText("0.50");
});
