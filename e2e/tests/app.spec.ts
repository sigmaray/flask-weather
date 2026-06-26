import { test, expect } from "@playwright/test";

const username = process.env.E2E_USERNAME ?? "admin";
const password = process.env.E2E_PASSWORD ?? "admin";

test.describe("Weather Archive", () => {
  test("login and navigate admin", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();

    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/admin\/admin_cities/);
    await expect(page.getByRole("link", { name: "Cities", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tools", exact: true })).toBeVisible();

    await page.getByRole("link", { name: "Tools", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Tools" })).toBeVisible();
  });

  test("registration page does not exist", async ({ page }) => {
    const response = await page.goto("/auth/register");
    expect(response?.status()).toBe(404);
  });
});
