import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.skip(!process.env.E2E_ISOLATED_DB_NAME, "Run through scripts/run_isolated_browser.py.");

const screenshots = path.resolve("..", ".local", "ui-polish-qa");

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(process.env.E2E_SYNTHETIC_PASSWORD!);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await expect(page.getByText("Updating records…")).toHaveCount(0);
}

async function capture(page: Page, name: string) {
  fs.mkdirSync(screenshots, { recursive: true });
  await page.screenshot({ path: path.join(screenshots, name), fullPage: true });
}

test("dashboard and compliance retain all nine metrics in balanced responsive groups", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await signIn(page);
  const cycle = await page.getByLabel("Accreditation cycle").inputValue();
  const summary = await (await page.request.get(`/api/compliance/?cycle=${cycle}`)).json();
  const documents = await (await page.request.get(`/api/documents/?cycle=${cycle}`)).json();
  const primary = page.locator(".primary-stats .stat");
  const workflow = page.locator(".workflow-stat");
  await expect(primary).toHaveCount(7);
  await expect(workflow).toHaveCount(2);
  for (const [label, value] of [
    ["Overall Compliance", summary.percentage === null ? "N/A" : `${summary.percentage}%`],
    ["Total Requirements", summary.total], ["Completed", summary.complete],
    ["For Verification", summary.for_verification], ["Needs Revision", summary.needs_revision],
    ["Missing Evidence", summary.missing],
  ] as const) {
    await expect(primary.filter({ hasText: label }).locator("strong")).toHaveText(String(value));
  }
  await expect(primary.filter({ hasText: "Total Documents" }).locator("strong"))
    .toHaveText(String(documents.length));
  await expect(workflow.filter({ hasText: "Ready for Completion Review" }).locator("strong"))
    .toHaveText(String(summary.ready_for_completion_review));
  await expect(workflow.filter({ hasText: "In Progress" }).locator("strong"))
    .toHaveText(String(summary.in_progress));
  await expect(page.getByRole("heading", { name: "Requirement Compliance" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Accreditation Area Progress" })).toBeVisible();
  expect(await page.locator(".primary-stats").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length)).toBe(7);
  await capture(page, "dashboard-desktop.png");

  await page.getByRole("button", { name: "Compliance Monitoring" }).click();
  await expect(primary).toHaveCount(7);
  await expect(workflow).toHaveCount(2);
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(primary).toHaveCount(7);
  await expect(workflow).toHaveCount(2);
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
  await page.waitForTimeout(300);
  expect(await page.locator(".primary-stats").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length)).toBe(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, "dashboard-mobile.png");
});

test("audit rows expose readable details, correlation, timezone, filters and older pages", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await signIn(page);
  const event = (id: number, action: string) => ({ id, actor: "Fictional Coordinator", actor_id: 1,
    action, record: `Fictional requirement ${id}`, area_id: 2, request_id: `synthetic-request-${id}`,
    created_at: "2026-09-27T00:00:00Z", detail: { reason: "Synthetic review note", package_number: 2 } });
  await page.route("**/api/audit/?**", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    const search = params.get("search"), before = params.get("before");
    const results = search ? [event(70, "filtered_event")] : before ? [event(80, "older_event")] : [event(100, "package_approved")];
    await route.fulfill({ json: { results, next_before: !search && !before ? 100 : null } });
  });
  await page.getByRole("button", { name: "Audit Trail" }).click();
  const rows = page.locator(".audit-table tbody > tr:not(.audit-expanded)");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Fictional Coordinator");
  await expect(rows.first()).toContainText("package approved");
  await expect(rows.first()).toContainText("Area #2");
  await expect(rows.first()).toContainText("Asia/Manila");
  await expect(rows.first().locator("pre")).toHaveCount(0);
  await rows.first().getByRole("button", { name: "View details" }).click();
  const details = page.locator(".audit-expanded");
  await expect(details).toContainText("synthetic-request-100");
  await expect(details).toContainText("Synthetic review note");
  await expect(rows.first().getByRole("button", { name: "Hide details" })).toHaveAttribute("aria-expanded", "true");
  await capture(page, "audit-desktop.png");

  await page.getByRole("button", { name: "Load older events" }).click();
  await expect(rows).toHaveCount(2);
  await expect(rows.last()).toContainText("older event");
  await page.getByLabel("Search", { exact: true }).fill("filtered");
  await expect(rows).toHaveCount(0);
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("filtered event");
  await expect(page.getByText("Fictional requirement 100")).toHaveCount(0);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
  await page.waitForTimeout(300);
  await rows.first().getByRole("button", { name: "View details" }).click();
  await expect(page.locator(".audit-expanded")).toContainText("synthetic-request-70");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, "audit-mobile.png");
});
