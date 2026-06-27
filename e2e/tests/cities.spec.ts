import { test, expect } from "@playwright/test";

import { login } from "./support/auth";
import {
  ensureTestCitiesSeeded,
  expectFlash,
  openCityDetails,
  openCreateCityForm,
} from "./support/helpers";

test.describe.configure({ mode: "serial" });

test.describe("Cities", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await login(page);
    await ensureTestCitiesSeeded(page);
    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("creates a city by name and country", async ({ page }) => {
    const cityName = `E2E City ${Date.now()}`;

    await openCreateCityForm(page);
    await page.getByLabel("Name").fill(cityName);
    await page.getByLabel("Country").fill("Germany");
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(page).toHaveURL(/\/admin\/admin_cities/);
    const row = page.getByRole("row", { name: new RegExp(cityName) });
    await expect(row).toContainText("Germany");
  });

  test("shows validation error when location is missing", async ({ page }) => {
    await openCreateCityForm(page);
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(page).toHaveURL(/\/admin\/admin_cities\/new/);
    await expectFlash(
      page,
      "Specify either name and country, or latitude and longitude.",
    );
  });

  test("opens city details with weather history and charts", async ({ page }) => {
    await openCityDetails(page, "Berlin");

    if (!(await page.getByRole("heading", { name: "History" }).isVisible())) {
      await page.getByRole("button", { name: "Fetch now" }).click();
      await expectFlash(page, "Weather data fetched.", 30_000);
    }

    await expect(page.getByRole("button", { name: "Fetch now" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
    await expect(page.locator("#temperatureChart")).toBeVisible();
    await expect(page.locator("#pressureChart")).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to cities" })).toBeVisible();
  });

  test("searches cities by name", async ({ page }) => {
    await page.locator('input[name="search"]').fill("Berlin");
    await page.getByRole("button", { name: "Search" }).click();

    await expect(page.getByRole("cell", { name: "Berlin", exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Paris", exact: true })).not.toBeVisible();
  });

  test("edits city check interval", async ({ page }) => {
    const cityName = `E2E Edit ${Date.now()}`;

    await openCreateCityForm(page);
    await page.getByLabel("Name").fill(cityName);
    await page.getByLabel("Country").fill("France");
    await page.getByRole("button", { name: "Save", exact: true }).click();

    const row = page.getByRole("row", { name: new RegExp(cityName) });
    await row.getByTitle("Edit Record").click();

    await page.getByLabel("Check interval (minutes)").fill("45");
    await page.getByRole("button", { name: "Save", exact: true }).click();

    await expect(row.getByRole("cell", { name: "45", exact: true })).toBeVisible();
  });

  test("fetch now on city detail stores a weather record", async ({ page }) => {
    test.setTimeout(60_000);

    await openCityDetails(page, "Berlin");

    const historyRows = page.locator(".weather-history-table tbody tr");
    const recordsBefore = await historyRows.count();

    await page.getByRole("button", { name: "Fetch now" }).click();
    await expectFlash(page, "Weather data fetched.", 30_000);

    await expect(historyRows).toHaveCount(recordsBefore + 1);
    await expect(page.locator("#temperatureChart")).toBeVisible();
  });
});
