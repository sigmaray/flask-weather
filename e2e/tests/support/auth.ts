import { expect, type Page } from "@playwright/test";

export const username = process.env.E2E_USERNAME ?? "admin";
export const password = process.env.E2E_PASSWORD ?? "admin";

export async function login(page: Page): Promise<void> {
  await page.goto("/auth/login");

  const loginHeading = page.getByRole("heading", { name: "Login" });
  if (!(await loginHeading.isVisible())) {
    await expect(page).toHaveURL(/\/admin\//);
    return;
  }

  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin\/admin_cities/);
}

export async function logout(page: Page): Promise<void> {
  await page.goto("/auth/logout");
  await expect(page).toHaveURL(/\/auth\/login/);
}
