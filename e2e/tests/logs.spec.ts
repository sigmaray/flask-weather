import { test, expect } from "@playwright/test";

import { login, logout } from "./support/auth";
import {
  ensureTestCitiesSeeded,
  expectFlash,
  openCityDetails,
  openCreateCityForm,
} from "./support/helpers";

test.describe.serial("Logs", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("API Requests and Error Log pages require authentication", async ({ page }) => {
    await logout(page);

    await page.goto("/admin/weather_api_log/");
    await expect(page).toHaveURL(/\/auth\/login/);

    await page.goto("/admin/app_error_log/");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("API Requests page shows logged weather fetches", async ({ page }) => {
    await ensureTestCitiesSeeded(page);
    await openCityDetails(page, "Berlin");
    await page.getByRole("button", { name: "Fetch now" }).click();
    await expectFlash(page, "Weather data fetched.", 30_000);

    await page.getByRole("link", { name: "API Requests", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/weather_api_log/);
    await expect(page.getByText("Weather API Requests (last 100, in memory)")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Method" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();

    const row = page.getByRole("row").filter({ hasText: "open-meteo.com" }).first();
    await expect(row).toBeVisible();
    await expect(row.getByRole("cell", { name: "GET", exact: true })).toBeVisible();
    await expect(row.locator(".badge")).toContainText("200");

    await row.getByText("View").click();
    await expect(row.locator("pre").filter({ hasText: /timezone|temperature/ })).toBeVisible();
  });

  test("Error Log page shows errors from failed weather fetch", async ({ page }) => {
    const cityName = "E2E Bad City";

    await page.goto("/admin/admin_cities/");
    await page.locator('input[name="search"]').fill(cityName);
    await page.getByRole("button", { name: "Search" }).click();

    let row = page.getByRole("row", { name: new RegExp(cityName) }).first();
    if ((await row.count()) === 0) {
      await openCreateCityForm(page);
      await page.getByLabel("Name").fill(cityName);
      await page.getByLabel("Country").fill("NowhereLand");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page).toHaveURL(/\/admin\/admin_cities/);
      row = page.getByRole("row", { name: new RegExp(cityName) }).first();
    }

    await row.getByTitle("View Record").click();
    await page.getByRole("button", { name: "Fetch now" }).click();
    await expectFlash(page, /Failed to fetch weather:/, 30_000);

    await page.getByRole("link", { name: "Error Log", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/app_error_log/);
    await expect(page.getByText("Application Errors (last 100, in memory)")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Source" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Traceback" })).toBeVisible();

    const errorRow = page.getByRole("row").filter({ hasText: "weather.fetch" }).first();
    await expect(errorRow).toBeVisible();
    await expect(errorRow).toContainText("Geocoding failed");
    await expect(errorRow.locator(".badge")).toContainText("GeocodingError");

    await errorRow.getByText("View").click();
    await expect(errorRow.locator("pre").filter({ hasText: /GeocodingError|Traceback/ })).toBeVisible();
  });
});
