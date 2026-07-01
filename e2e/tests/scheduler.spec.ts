import { test, expect } from "@playwright/test";

import { login } from "./support/auth";

test.describe.serial("Scheduler (Background Tasks)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Background Tasks", exact: true }).click();
  });

    test("can pause and resume jobs", async ({ page }) => {
    // If the scheduler is disabled entirely, just verify the message
    const disabled = page.locator(".alert-info");
    if (await disabled.isVisible()) {
      await expect(disabled).toContainText("In-process scheduler is disabled");
      return;
    }

    // Check that we're on the scheduler page
    await expect(page.getByRole("heading", { name: "Background Tasks" })).toBeVisible();

    // The fetch_weather job should be present
    const row = page.getByRole("row").filter({ hasText: "fetch_weather" });
    await expect(row).toBeVisible();

    // Verify it is initially running (or paused, but let's see its state)
    // If it's paused, resume it first to have a stable state
    let isPaused = await row.getByRole("button", { name: "Resume" }).isVisible();
    if (isPaused) {
        await row.getByRole("button", { name: "Resume" }).click();
        await expect(page.locator(".alert-success").first()).toContainText("resumed successfully");
    }

    // Now pause it
    await row.getByRole("button", { name: "Pause" }).click();
    await expect(page.locator(".alert-success").first()).toContainText("paused successfully");
    
    // Now it should show "Paused" badge
    await expect(row.getByText("Paused")).toBeVisible();
    await expect(row.getByRole("button", { name: "Resume" })).toBeVisible();

    // Now resume it
    await row.getByRole("button", { name: "Resume" }).click();
    await expect(page.locator(".alert-success").first()).toContainText("resumed successfully");
    
    // Now it should show "Active" badge
    await expect(row.getByText("Active")).toBeVisible();
    await expect(row.getByRole("button", { name: "Pause" })).toBeVisible();
  });

  test("can cancel a job", async ({ page }) => {
    // If the scheduler is disabled entirely, just verify the message
    const disabled = page.locator(".alert-info");
    if (await disabled.isVisible()) {
      await expect(disabled).toContainText("In-process scheduler is disabled");
      return;
    }

    // Since we need to test cancelling, but fetch_weather might be needed by other tests 
    // or it runs once globally, removing it here will permanently remove it. 
    // That's fine for E2E since we don't rely on it anywhere else in playwright tests.
    const row = page.getByRole("row").filter({ hasText: "fetch_weather" });
    if (await row.isVisible()) {
      page.once("dialog", (dialog) => dialog.accept());
      await row.getByRole("button", { name: "Cancel" }).click();

      await expect(page.locator(".alert-success").first()).toContainText("removed successfully");
      await expect(page.getByRole("row").filter({ hasText: "fetch_weather" })).not.toBeVisible();
    }
  });
});
