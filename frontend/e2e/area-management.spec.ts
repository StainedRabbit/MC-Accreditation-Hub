import { test, expect, type Page } from "@playwright/test";

test.skip(!process.env.E2E_ISOLATED_DB_NAME, "Run through scripts/run_isolated_browser.py.");

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(process.env.E2E_SYNTHETIC_PASSWORD!);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
}

test("cycle Coordinator can add, edit, and delete an empty accreditation area", async ({ page }) => {
  const initialTitle = `Area E2E${Date.now()}`;
  const updatedTitle = `${initialTitle} Updated`;
  await login(page);
  await page.getByRole("button", { name: "Accreditation Areas", exact: true }).click();
  await page.getByRole("button", { name: "Add Area" }).click();

  const form = page.getByRole("dialog");
  await expect(form.getByLabel("Area code")).toHaveCount(0);
  await form.getByLabel("Area title").fill(initialTitle);
  await form.getByLabel("Icon").fill("📘");
  await form.getByLabel("Display order").fill("50");
  await form.getByRole("button", { name: "Add area" }).click();
  await expect(form).toHaveCount(0);
  let card = page.locator(".area-card-shell").filter({ hasText: initialTitle });
  await expect(card).toBeVisible();
  await expect(page.locator(".area-card-shell").first()).toContainText(initialTitle);

  await card.getByRole("button", { name: "Edit" }).click();
  const edit = page.getByRole("dialog");
  await edit.getByLabel("Area title").fill(updatedTitle);
  await edit.getByRole("button", { name: "Save changes" }).click();
  await expect(edit).toHaveCount(0);
  card = page.locator(".area-card-shell").filter({ hasText: updatedTitle });
  await expect(card).toBeVisible();

  const createdAreas = await (await page.request.get("/api/areas/")).json();
  const created = createdAreas.find((area: { title: string }) => area.title === updatedTitle);
  expect(created).toBeTruthy();
  expect(created.code).toMatch(/^AREA-\d+$/);
  page.once("dialog", (dialog) => dialog.accept());
  await card.getByRole("button", { name: "Delete" }).click();
  await expect(page.locator(".area-card-shell").filter({ hasText: updatedTitle })).toHaveCount(0);

  const history = await (await page.request.get(`/api/audit/?kind=academic&cycle=${created.cycle}&area=${created.id}`)).json();
  expect(history.results.map((event: { action: string }) => event.action)).toEqual([
    "area_deleted", "area_updated", "area_created",
  ]);
});

test("requirements sort both ways and a new requirement returns to the top", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  const table = page.locator(".table-wrap table").first();
  const titles = () => table.locator("tbody tr td:first-child strong").allTextContents();
  const header = table.getByRole("button", { name: /Requirement/ }).first();
  const collator = new Intl.Collator("en-PH", { sensitivity: "base", numeric: true });
  await header.click();
  const ascending = await titles();
  expect(ascending).toEqual([...ascending].sort(collator.compare));
  await header.click();
  const descending = await titles();
  expect(descending).toEqual([...descending].sort((a, b) => collator.compare(b, a)));

  const title = `A new synthetic requirement ${Date.now()}`;
  await page.getByRole("button", { name: "Add Requirement" }).click();
  const form = page.getByRole("dialog");
  await expect(form.getByLabel("Requirement code")).toHaveCount(0);
  await form.getByLabel("Requirement title").fill(title);
  await form.getByLabel("Responsible person").fill("demo.custodian");
  await form.getByRole("button", { name: /\(demo\.custodian\)/ }).click();
  await form.getByLabel("Evidence item 1").fill("Synthetic checklist item");
  await form.getByRole("button", { name: "Save Requirement" }).click();
  await expect(form).toHaveCount(0);
  await expect(table.locator("tbody tr").first()).toContainText(title);
});
