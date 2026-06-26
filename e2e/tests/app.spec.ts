import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME ?? "admin";
const password = process.env.E2E_PASSWORD ?? "admin";

test.describe("Weather Archive", () => {
  test("login and navigate app", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();

    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText(username)).toBeVisible();
    await expect(page.getByRole("link", { name: "Logout" })).toBeVisible();

    await page.locator("nav").getByRole("link", { name: "Cities", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Cities" })).toBeVisible();

    await page.getByRole("link", { name: "Add city" }).click();
    await page.getByLabel("Latitude / Longitude").check();
    await page.getByLabel("Name").fill("Test City");
    await page.getByLabel("Latitude").fill("52.52");
    await page.getByLabel("Longitude").fill("13.405");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByRole("cell", { name: "Test City" })).toBeVisible();

    await page.locator("nav").getByRole("link", { name: "Settings", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });

  test("registration page does not exist", async ({ page }) => {
    const response = await page.goto("/auth/register");
    expect(response?.status()).toBe(404);
  });
});
