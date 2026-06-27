import { test, expect } from "@playwright/test";

import { login } from "./support/auth";
import {
  acceptNextConfirm,
  clearAllCities,
  ensureTestCitiesSeeded,
  expectFlash,
  goToTools,
  openCityDetails,
  readCitiesCount,
  readWeatherRecordsCount,
} from "./support/helpers";

test.describe.serial("Tools", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToTools(page);
  });

  test("seeds test cities when database is empty", async ({ page }) => {
    await clearAllCities(page);
    await goToTools(page);

    await page.getByRole("button", { name: "Seed test cities" }).click();
    await expectFlash(page, "Added 10 test cities.");
    await expect(readCitiesCount(page)).resolves.toBe("10");
  });

  test("seed cities is idempotent when cities already exist", async ({ page }) => {
    await page.getByRole("button", { name: "Seed test cities" }).click();
    await expectFlash(page, "Cities already exist in the database.");
  });

  test("clears all cities after confirmation", async ({ page }) => {
    if ((await readWeatherRecordsCount(page)) !== "0") {
      acceptNextConfirm(page);
      await page.getByRole("button", { name: "Clear weather" }).click();
      await expectFlash(page, /Deleted \d+ weather record\(s\)\.|No weather records to delete\./);
    }

    acceptNextConfirm(page);
    await page.getByRole("button", { name: "Clear cities" }).click();
    await expectFlash(page, /Deleted \d+ city\/cities\./);
    await expect(readCitiesCount(page)).resolves.toBe("0");

    await page.getByRole("button", { name: "Seed test cities" }).click();
    await expectFlash(page, "Added 10 test cities.");
  });

  test("clears weather records after confirmation", async ({ page }) => {
    if ((await readWeatherRecordsCount(page)) === "0") {
      await ensureTestCitiesSeeded(page);
      await openCityDetails(page, "Berlin");
      await page.getByRole("button", { name: "Fetch now" }).click();
      await expectFlash(page, "Weather data fetched.", 30_000);
      await goToTools(page);
    }

    acceptNextConfirm(page);
    await page.getByRole("button", { name: "Clear weather" }).click();
    await expectFlash(page, /Deleted \d+ weather record\(s\)\./);
    await expect(readWeatherRecordsCount(page)).resolves.toBe("0");
  });
});
