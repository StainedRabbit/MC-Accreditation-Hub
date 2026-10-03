import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const password = process.env.E2E_SYNTHETIC_PASSWORD || fs.readFileSync(path.join(root, ".local/demo-credentials.txt"), "utf8")
  .match(/Password for these fictional accounts: (.+)/)![1].trim();

test("overdue drilldown and report filter keep readiness population", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  const cycle = await page.getByLabel("Accreditation cycle").inputValue();
  const requirements = await (await page.request.get("/api/requirements/?cycle=" + cycle)).json();
  const target = requirements[0];
  expect(target).toBeTruthy();
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  const changed = await page.request.patch("/api/requirements/" + target.id + "/", {
    data: { deadline: "2000-01-01" }, headers: { "X-CSRFToken": csrf! },
  });
  expect(changed.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  const drilldown = page.getByRole("button", { name: /Overdue.*View incomplete requirements/ });
  await expect(drilldown).toContainText("1");
  await drilldown.click();
  await expect(page.getByRole("checkbox", { name: "Overdue only" })).toBeChecked();
  const row = page.locator("table tbody tr");
  await expect(row).toHaveCount(1);
  await expect(row).toContainText(target.code);
  await expect(row.locator(".badge.overdue")).toHaveText("Overdue");
  await row.getByRole("button", { name: /View/ }).click();
  await expect(page.locator(".requirement-summary .badge.overdue")).toHaveText("Overdue");

  await page.getByRole("button", { name: "Reports", exact: true }).click();
  const baseline = await (await page.request.get("/api/reports/compliance/?cycle=" + cycle)).json();
  await page.getByRole("checkbox", { name: "Overdue only" }).check();
  await expect(page.locator(".report-provenance")).toContainText("overdue: Overdue only");
  await expect(page.locator(".report-provenance")).toContainText("Asia/Manila");
  const filtered = await (await page.request.get("/api/reports/compliance/?cycle=" + cycle + "&overdue=1")).json();
  expect(filtered.selected_filters.overdue).toBe(true);
  expect(filtered.rows).toHaveLength(1);
  expect(filtered.rows[0].id).toBe(target.id);
  expect([filtered.numerator, filtered.denominator, filtered.percentage])
    .toEqual([baseline.numerator, baseline.denominator, baseline.percentage]);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  const download = await downloadPromise;
  const csv = fs.readFileSync(await download.path(), "utf8");
  expect(csv).toContain("Overdue filter,Overdue only");
  expect(csv).toContain("Overdue count (population)");
  expect(csv).toContain("Status,Overdue,Archived");
});
