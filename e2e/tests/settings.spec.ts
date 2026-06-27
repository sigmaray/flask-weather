import { test, expect } from "@playwright/test";

import { login } from "./support/auth";

test.describe("Settings", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Settings", exact: true }).click();
  });

  test("shows default check interval", async ({ page }) => {
    await expect(
      page.getByRole("columnheader", { name: /Default check interval/ }),
    ).toBeVisible();
    await expect(page.locator("td.col-default_check_interval_minutes")).toHaveText(/\d+/);
  });

  test("updates default check interval", async ({ page }) => {
    await page.getByTitle("Edit Record").click();

    const intervalField = page.getByLabel("Default check interval (minutes)");
    const originalValue = await intervalField.inputValue();
    const newValue = originalValue === "30" ? "45" : "30";

    await intervalField.fill(newValue);
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(page).toHaveURL(/\/admin\/app_settings/);
    await expect(page.locator("td.col-default_check_interval_minutes")).toHaveText(newValue);

    await page.getByTitle("Edit Record").click();
    await intervalField.fill(originalValue);
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.locator("td.col-default_check_interval_minutes")).toHaveText(
      originalValue,
    );
  });
});
