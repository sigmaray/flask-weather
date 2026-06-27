import { expect, type Page } from "@playwright/test";

export async function expectFlash(
  page: Page,
  message: string | RegExp,
  timeout = 10_000,
): Promise<void> {
  const alert = page.locator(".alert").filter({ hasText: message });
  await expect(alert.first()).toBeVisible({ timeout });
}

export async function goToTools(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Tools", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tools" })).toBeVisible();
}

export async function acceptNextConfirm(page: Page): Promise<void> {
  page.once("dialog", (dialog) => dialog.accept());
}

export async function openCreateCityForm(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Create", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/admin_cities\/new/);
}

export async function readCitiesCount(page: Page): Promise<string> {
  const value = await page
    .locator('p:has-text("Cities in database:") strong')
    .first()
    .textContent();
  return value?.trim() ?? "0";
}

export async function readWeatherRecordsCount(page: Page): Promise<string> {
  const value = await page
    .locator('p:has-text("Weather records:") strong')
    .last()
    .textContent();
  return value?.trim() ?? "0";
}

export async function clearAllCities(page: Page): Promise<void> {
  await page.goto("/admin/tools/");

  if ((await readWeatherRecordsCount(page)) !== "0") {
    acceptNextConfirm(page);
    await page.getByRole("button", { name: "Clear weather" }).click();
    await expectFlash(page, /Deleted \d+ weather record\(s\)\.|No weather records to delete\./);
    await page.goto("/admin/tools/");
  }

  if ((await readCitiesCount(page)) === "0") {
    return;
  }

  acceptNextConfirm(page);
  await page.getByRole("button", { name: "Clear cities" }).click();
  await expectFlash(page, /Deleted \d+ city\/cities\./);
}

export async function openCityDetails(page: Page, cityName: string): Promise<void> {
  await page.locator('input[name="search"]').fill(cityName);
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("row", { name: new RegExp(cityName) }).getByTitle("View Record").click();
  await expect(page).toHaveURL(/\/admin\/admin_cities\/details/);
}
