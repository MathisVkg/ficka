import { test, expect } from "@playwright/test";
for (const [path, noun] of [
  ["income", "income"],
  ["expenses", "expense"],
]) {
  test(
    "real " + noun + " lifecycle through web and PostgreSQL",
    async ({ page, request }) => {
      const title = "E2E " + noun + " " + crypto.randomUUID();
      await page.goto("/" + path);
      await page
        .getByRole("button", { name: "New " + noun, exact: true })
        .first()
        .click();
      let dialog = page.getByRole("dialog");
      await dialog.getByLabel("Title").fill(title);
      await dialog.getByLabel("Amount including VAT").fill("121.00");
      await dialog.getByLabel("Status").selectOption("pending");
      await dialog.getByLabel("Entry date").fill("2026-01-05");
      await dialog
        .getByLabel("Payment date", { exact: false })
        .fill("2026-01-20");
      await dialog
        .getByText("VAT and additional details", { exact: true })
        .click();
      await dialog.getByLabel("VAT preset").selectOption("21");
      await dialog.getByRole("button", { name: "Create " + noun }).click();
      await page.getByRole("button", { name: title, exact: true }).waitFor();
      const stored = await (
        await request.get(
          "/api/v1/" + path + "?search=" + encodeURIComponent(title),
        )
      ).json();
      expect(stored.items[0].vat_amount).toBe("21.00");
      expect(stored.items[0].amount_excluding_vat).toBe("100.00");
      await page
        .getByRole("button", { name: "Edit " + title, exact: true })
        .click();
      dialog = page.getByRole("dialog");
      await dialog.getByLabel("Entry date").fill("2026-01-06");
      await expect(
        dialog.getByLabel("Payment date", { exact: false }),
      ).toHaveValue("2026-01-20");
      await dialog.getByLabel("Status").selectOption("paid");
      await dialog.getByLabel("Actual payment date").fill("2026-01-21");
      await dialog.getByRole("button", { name: "Save changes" }).click();
      await expect(
        page.getByRole("row").filter({ hasText: title }),
      ).toContainText(path === "income" ? "Received" : "Paid");
      await page
        .getByLabel("Search entries")
        .fill("no-matching-" + crypto.randomUUID());
      await expect(
        page.getByRole("heading", { name: "No entries match these filters" }),
      ).toBeVisible();
      await page
        .getByRole("button", { name: "Clear filters", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Delete " + title, exact: true })
        .click();
      const deletion = page.waitForResponse(
        (response) =>
          response.request().method() === "DELETE" &&
          response.url().endsWith("/api/v1/" + path + "/" + stored.items[0].id),
      );
      await page
        .getByRole("button", { name: "Delete entry", exact: true })
        .click();
      await expect(
        page.getByRole("button", { name: title, exact: true }),
      ).toHaveCount(0);
      expect((await deletion).ok()).toBeTruthy();
      expect(
        (
          await request.get("/api/v1/" + path + "/" + stored.items[0].id)
        ).status(),
      ).toBe(404);
    },
  );
}
test("real category management and server-backed page navigation", async ({
  page,
  request,
}) => {
  const name = "E2E category " + crypto.randomUUID();
  await page.goto("/settings");
  await page.getByRole("button", { name: "Add income category" }).click();
  await page.getByRole("dialog").getByLabel("Category name").fill(name);
  await page
    .getByRole("button", { name: "Save category", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Rename " + name, exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Category name")
    .fill(name + " renamed");
  await page
    .getByRole("button", { name: "Save category", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Archive " + name + " renamed", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Archive category", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Restore " + name + " renamed",
      exact: true,
    }),
  ).toBeVisible();
  const prefix = "E2E paging " + crypto.randomUUID();
  const ids: string[] = [];
  try {
    for (let i = 0; i < 21; i++) {
      const response = await request.post("/api/v1/income", {
        data: {
          title: prefix + " " + i,
          amount: String(i + 1),
          entry_date: "2026-01-05",
        },
      });
      expect(response.status()).toBe(201);
      ids.push((await response.json()).id);
    }
    await page.goto("/income");
    await page.getByLabel("Search entries").fill(prefix);
    await expect(page.getByText("21 entries", { exact: true })).toBeVisible();
    await expect(page.getByRole("table").getByRole("row")).toHaveCount(21);
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.getByText("Page 2 of 2", { exact: true })).toBeVisible();
    await expect(page.getByRole("table").getByRole("row")).toHaveCount(2);
  } finally {
    for (const id of ids) await request.delete("/api/v1/income/" + id);
  }
});
