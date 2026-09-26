import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";

test.skip(!process.env.E2E_ISOLATED_DB_NAME, "Run through scripts/run_isolated_browser.py.");

const root = path.resolve("..");
const originalPassword = process.env.E2E_SYNTHETIC_PASSWORD!;

async function signIn(page: Page, role: string, password = originalPassword) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill(`demo.${role}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
}

function fixture(action: "deactivate-viewer" | "revoke-faculty") {
  execFileSync(process.env.E2E_PYTHON!, [path.join(root, "scripts/isolated_browser_fixture.py"), action],
    { cwd: root, env: process.env, stdio: "ignore", timeout: 30000 });
}

test("browser cookie survives password change and old password stops working", async ({ page }) => {
  await signIn(page, "coordinator");
  await page.getByRole("button", { name: "Account security" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Current password").fill(originalPassword);
  await dialog.getByLabel("New password", { exact: true }).fill(process.env.E2E_NEW_PASSWORD!);
  await dialog.getByLabel("Confirm new password").fill(process.env.E2E_NEW_PASSWORD!);
  await dialog.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(originalPassword);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Invalid username or password");
  await page.getByLabel("Password", { exact: true }).fill(process.env.E2E_NEW_PASSWORD!);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
});

test("deactivated fictional account loses its browser session", async ({ page }) => {
  await signIn(page, "viewer");
  fixture("deactivate-viewer");
  await page.reload();
  await expect(page.getByRole("button", { name: "Sign In", exact: true })).toBeVisible();
  await page.getByLabel("Email / Username").fill("demo.viewer");
  await page.getByLabel("Password", { exact: true }).fill(originalPassword);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Invalid username or password");
});

test("revoked fictional Faculty grant removes browser evidence scope", async ({ page }) => {
  await signIn(page, "custodian");
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  const faculty = page.getByRole("row").filter({ hasText: "Faculty Documentation" });
  await expect(faculty).toBeVisible();
  const records = await (await page.request.get("/api/requirements/")).json();
  const facultyId = records.find((record: { title: string }) => record.title === "Faculty Documentation")?.id;
  expect(facultyId).toBeTruthy();
  fixture("revoke-faculty");
  await page.reload();
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await expect(faculty).toHaveCount(0);
  expect((await page.request.get(`/api/requirements/${facultyId}/`)).status()).toBe(404);
});

test("public health probe responds against the isolated fictional database", async ({ page }) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    const response = await fetch("/api/health/");
    return { status: response.status, body: await response.json() };
  });
  expect(result).toEqual({ status: 200, body: { status: "ok" } });
});
