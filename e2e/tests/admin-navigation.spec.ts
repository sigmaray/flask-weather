import { test, expect } from "@playwright/test";

import { login } from "./support/auth";

test.describe("Admin navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("navigates all admin sections", async ({ page }) => {
    await page.getByRole("link", { name: "Tools", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Tools" })).toBeVisible();
    await expect(page.getByText("Weather fetch")).toBeVisible();

    await page.getByRole("link", { name: "Users", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/users/);
    await expect(page.getByRole("columnheader", { name: /Username/ })).toBeVisible();

    await page.getByRole("link", { name: "Cities", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/admin_cities/);
    await expect(page.getByRole("columnheader", { name: "Name", exact: true })).toBeVisible();

    await page.getByRole("link", { name: "Weather", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/weather_records/);
    await expect(page.getByRole("columnheader", { name: /Temperature/ })).toBeVisible();

    await page.getByRole("link", { name: "Settings", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/app_settings/);
    await expect(
      page.getByRole("columnheader", { name: /Default check interval/ }),
    ).toBeVisible();

    await page.getByRole("link", { name: "Background Tasks", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/scheduler/);
    await expect(page.getByRole("heading", { name: "Background Tasks" })).toBeVisible();

    await page.getByRole("link", { name: "Map", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/weather_map/);
    await expect(page.getByRole("heading", { name: "Weather map" })).toBeVisible();

    await page.getByRole("link", { name: "API Requests", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/weather_api_log/);
    await expect(page.getByText("Weather API Requests (last 100, in memory)")).toBeVisible();

    await page.getByRole("link", { name: "Error Log", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/app_error_log/);
    await expect(page.getByText("Application Errors (last 100, in memory)")).toBeVisible();
  });

  test("authenticated root redirects to cities list", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/admin\/admin_cities/);
  });
});
