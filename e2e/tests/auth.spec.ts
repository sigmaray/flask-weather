import { test, expect } from "@playwright/test";

import { login, logout } from "./support/auth";
import { expectFlash } from "./support/helpers";

test.describe("Authentication", () => {
  test("login with valid credentials redirects to cities", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("link", { name: "Cities", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tools", exact: true })).toBeVisible();
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/auth/login");
    await page.getByLabel("Username").fill("nobody");
    await page.getByLabel("Password").fill("wrong-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/auth\/login/);
    await expectFlash(page, "Invalid username or password.");
  });

  test("logout returns to login page", async ({ page }) => {
    await login(page);
    await logout(page);
    await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();
    await expectFlash(page, "You have been logged out.");
  });

  test("admin pages require authentication", async ({ page }) => {
    await page.goto("/admin/admin_cities/");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("root redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("registration page does not exist", async ({ page }) => {
    const response = await page.goto("/auth/register");
    expect(response?.status()).toBe(404);
  });
});
