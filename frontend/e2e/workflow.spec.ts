import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const credentials = fs.readFileSync(
  path.join(root, ".local/demo-credentials.txt"),
  "utf8",
);
const password = credentials
  .match(/Password for these fictional accounts: (.+)/)![1]
  .trim();
const screenshots = path.join(root, ".local/screenshots");
fs.mkdirSync(screenshots, { recursive: true });

async function login(page: Page, role: string) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill(`demo.${role}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await expect(page.getByText("Updating records…")).toHaveCount(0);
}

test("Figma login and mobile layout", async ({ page }) => {
  await page.setViewportSize({ width: 1916, height: 900 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "MC Accreditation Hub" }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(screenshots, "login-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: path.join(screenshots, "login-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("create, upload, request revisions, replace and approve", async ({
  page,
  browser,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 1916, height: 900 });
  await login(page, "coordinator");
  await page.screenshot({
    path: path.join(screenshots, "dashboard-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await page
    .getByRole("button", { name: "Add Requirement", exact: true })
    .click();
  const title = `Workflow demonstration ${Date.now()}`;
  const modal = page.getByRole("dialog");
  await modal
    .getByRole("combobox", { name: "Accreditation area", exact: true })
    .selectOption({ label: "Faculty" });
  await modal.getByLabel("Requirement code").fill(`E2E-${Date.now()}`);
  await modal.getByLabel("Requirement title").fill(title);
  await modal
    .getByLabel("Description / acceptance criteria")
    .fill("Fictional end-to-end verification of document approval.");
  await modal.getByLabel("Responsible office / person").fill("Graduate School");
  await modal.getByLabel("Evidence item 1").fill("Sample faculty plan");
  await modal
    .getByLabel("Acceptance criteria", { exact: true })
    .fill("A complete readable sample document.");
  await modal.getByRole("button", { name: "Save Requirement" }).click();
  await expect(modal).toHaveCount(0);
  await page
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Upload evidence", exact: true })
    .click();
  await modal.getByLabel("Document title").fill(`${title} evidence`);
  await modal
    .locator("input[type=file]")
    .setInputFiles(path.join(root, ".local/sample-evidence.pdf"));
  await modal.getByRole("button", { name: "Upload & Submit" }).click();
  await expect(modal).toHaveCount(0);
  await expect(page.getByText("Updating records…")).toHaveCount(0);
  await expect(
    page
      .locator(".requirement-summary")
      .getByText("For Verification", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(screenshots, "requirement-desktop.png"),
    fullPage: true,
  });
  const reviewerContext = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const reviewer = await reviewerContext.newPage();
  await login(reviewer, "reviewer");
  await reviewer
    .getByRole("button", { name: "Evidence Verification", exact: true })
    .click();
  await reviewer
    .getByRole("row")
    .filter({ hasText: `${title} evidence` })
    .getByRole("button", { name: "Review", exact: true })
    .click();
  await reviewer
    .getByRole("combobox", { name: "Decision", exact: true })
    .selectOption("revision_requested");
  await reviewer
    .getByRole("textbox", { name: "Review comments (required)" })
    .fill("Please include a revised sample.");
  await reviewer
    .getByRole("button", { name: "Record Decision", exact: true })
    .click();
  await expect(reviewer.getByRole("dialog")).toHaveCount(0);
  await reviewer
    .getByRole("button", { name: "Requirements", exact: true })
    .click();
  await reviewer
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await expect(
    reviewer.getByRole("button", { name: "Mark Complete", exact: true }),
  ).toHaveCount(0);
  await expect(
    reviewer.getByRole("button", { name: "Reopen Requirement", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await expect(page.getByText("Revision Requested").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Upload new version", exact: true })
    .click();
  await modal
    .locator("input[type=file]")
    .setInputFiles(path.join(root, ".local/sample-evidence.pdf"));
  await modal.getByRole("button", { name: "Upload & Submit" }).click();
  await expect(modal).toHaveCount(0);
  await reviewer.reload();
  await reviewer
    .getByRole("button", { name: "Evidence Verification", exact: true })
    .click();
  await reviewer
    .getByRole("row")
    .filter({ hasText: `${title} evidence` })
    .getByRole("button", { name: "Review", exact: true })
    .click();
  await reviewer
    .getByRole("button", { name: "Record Decision", exact: true })
    .click();
  await expect(reviewer.getByRole("dialog")).toHaveCount(0);
  await reviewer
    .getByRole("button", { name: "Requirements", exact: true })
    .click();
  await reviewer
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await expect(
    reviewer.getByRole("button", { name: "Mark Complete", exact: true }),
  ).toHaveCount(0);
  await expect(
    reviewer.getByRole("button", { name: "Reopen Requirement", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: title });
  await expect(
    row.getByText("Ready for Completion Review", { exact: true }),
  ).toBeVisible();
  await row.getByRole("button", { name: "View", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ready for Completion Review" }),
  ).toBeVisible();
  await expect(
    page.getByText("No Coordinator certification has been recorded yet."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Mark Complete", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Version 1", { exact: true })).toBeVisible();
  await expect(page.getByText("Version 2", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  const readyBefore = Number(
    await page
      .locator(".stat")
      .filter({ hasText: "Ready for Completion Review" })
      .locator("strong")
      .textContent(),
  );
  const completeBefore = Number(
    await page
      .locator(".stat")
      .filter({ hasText: "Completed" })
      .locator("strong")
      .textContent(),
  );
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await page.getByRole("button", { name: "Mark Complete", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Rationale" })).toHaveAttribute(
    "required",
    "",
  );
  await page
    .getByRole("textbox", { name: "Rationale" })
    .fill("All mandatory evidence has been reviewed and is current.");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Mark Complete", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByText("Marked complete", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(
    page
      .locator(".stat")
      .filter({ hasText: "Ready for Completion Review" })
      .locator("strong"),
  ).toHaveText(String(readyBefore - 1));
  await expect(
    page.locator(".stat").filter({ hasText: "Completed" }).locator("strong"),
  ).toHaveText(String(completeBefore + 1));
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await page
    .getByRole("row")
    .filter({ hasText: title })
    .getByRole("button", { name: "View", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Reopen Requirement", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Rationale" })
    .fill("Follow-up review is needed before final submission.");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Reopen Requirement", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByText("Reopened requirement", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(
    page
      .locator(".stat")
      .filter({ hasText: "Ready for Completion Review" })
      .locator("strong"),
  ).toHaveText(String(readyBefore));
  await expect(
    page.locator(".stat").filter({ hasText: "Completed" }).locator("strong"),
  ).toHaveText(String(completeBefore));
  await page
    .getByRole("button", { name: "Evidence Repository", exact: true })
    .click();
  await page.screenshot({
    path: path.join(screenshots, "repository-desktop.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Accreditation Areas", exact: true })
    .click();
  await page.screenshot({
    path: path.join(screenshots, "areas-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
  await page.screenshot({
    path: path.join(screenshots, "dashboard-mobile.png"),
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
  await reviewerContext.close();
});
