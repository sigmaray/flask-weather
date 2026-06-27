import { test, expect } from "@playwright/test";

import { login } from "./support/auth";
import { goToTools } from "./support/helpers";

test.describe("Weather Archive smoke", () => {
  test("login and open tools page", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("link", { name: "Cities", exact: true })).toBeVisible();
    await goToTools(page);
    await expect(page.getByRole("button", { name: "Fetch due cities" })).toBeVisible();
  });
});
