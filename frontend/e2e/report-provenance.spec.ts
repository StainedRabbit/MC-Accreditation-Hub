import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const password = process.env.E2E_SYNTHETIC_PASSWORD || fs.readFileSync(path.join(root, ".local/demo-credentials.txt"), "utf8")
  .match(/Password for these fictional accounts: (.+)/)![1].trim();

async function signIn(page: Page, role: string) {
  await page.getByLabel("Email / Username").fill(`demo.${role}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
}

test("report provenance, filtered population, delayed responses and failed export gate", async ({ page }) => {
  await page.goto("/");
  await signIn(page, "coordinator");
  const cycle = await page.getByLabel("Accreditation cycle").inputValue();
  await page.getByRole("button", { name: "Reports", exact: true }).click();
  await expect(page.locator(".report-provenance")).toBeVisible();
  const dashboard = await (await page.request.get(`/api/compliance/?cycle=${cycle}`)).json();
  const filtered = await (await page.request.get(`/api/reports/compliance/?cycle=${cycle}&status=complete`)).json();
  expect([filtered.numerator, filtered.denominator, filtered.excluded, filtered.percentage])
    .toEqual([dashboard.complete, dashboard.total, dashboard.excluded, dashboard.percentage]);
  expect(filtered.filtered_row_count).toBe(filtered.rows.length);
  expect(filtered.selected_filters.status).toBe("complete");
  expect(filtered.timezone).toBe("Asia/Manila");
  await page.getByRole("combobox", { name: "Status" }).selectOption("complete");
  await expect(page.locator(".report-provenance")).toContainText("status: Complete");
  await expect(page.locator(".report-provenance")).toContainText("Instrument:");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  const download = await downloadPromise;
  const csv = fs.readFileSync(await download.path(), "utf8");
  for (const field of ["Instrument", "Readiness population", "Numerator (complete)",
                       "Denominator (active applicable)", "Filtered row count", "Formula version", "Timezone"])
    expect(csv).toContain(field);
  await page.evaluate(() => { (window as any).__printCalls = 0; window.print = () => { (window as any).__printCalls++; }; });
  await page.getByRole("button", { name: "Print report" }).click();
  expect(await page.evaluate(() => (window as any).__printCalls)).toBe(1);

  let releaseOld!: () => void;
  let sawOld!: () => void;
  const oldStarted = new Promise<void>((resolve) => { sawOld = resolve; });
  const oldGate = new Promise<void>((resolve) => { releaseOld = resolve; });
  await page.route("**/api/reports/compliance/?**", async (route) => {
    const status = new URL(route.request().url()).searchParams.get("status");
    if (status === "missing") { sawOld(); await oldGate; }
    if (status === "needs_revision") {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic report failure" }) });
    } else await route.continue();
  });
  await page.getByRole("combobox", { name: "Status" }).selectOption("missing");
  await oldStarted;
  await expect(page.getByRole("button", { name: "Print report" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Export CSV" })).toBeDisabled();
  await page.getByRole("combobox", { name: "Status" }).selectOption("in_progress");
  await expect(page.locator(".report-provenance")).toContainText("status: In Progress");
  releaseOld();
  await expect(page.locator(".report-provenance")).toContainText("status: In Progress");
  await page.getByRole("combobox", { name: "Status" }).selectOption("needs_revision");
  await expect(page.getByText("Synthetic report failure")).toBeVisible();
  await expect(page.locator(".report-provenance")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Print report" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Export CSV" })).toBeDisabled();
  expect(await page.evaluate(() => (window as any).__printCalls)).toBe(1);
});

test("cycle and account changes discard delayed search and detail; search fetches details by ID", async ({ page }) => {
  await page.route("**/api/cycles/?archived=1", async (route) => {
    const response = await route.fetch();
    const cycles = await response.json();
    await route.fulfill({ response, json: [...cycles, { ...cycles[0], id: 999999, title: "Fictional second cycle" }] });
  });
  await page.goto("/");
  await signIn(page, "coordinator");
  const originalCycle = await page.getByLabel("Accreditation cycle").inputValue();
  await page.getByRole("button", { name: "Search", exact: true }).first().click();
  let releaseSearch!: () => void;
  let sawSearch!: () => void;
  const searchStarted = new Promise<void>((resolve) => { sawSearch = resolve; });
  const searchGate = new Promise<void>((resolve) => { releaseSearch = resolve; });
  let searchCount = 0;
  const fakeId = "00000000-0000-4000-8000-000000000001";
  const fakeResult = { requirements: [], documents: [{ id: fakeId, title: "Synthetic fetched document", category: "Fixture", area: "Faculty" }] };
  await page.route("**/api/search/?**", async (route) => {
    searchCount++;
    if (searchCount === 1) { sawSearch(); await searchGate; }
    await route.fulfill({ json: fakeResult });
  });
  await page.getByLabel("Search all authorized records").fill("synthetic");
  await page.getByRole("button", { name: "Search", exact: true }).last().click();
  await searchStarted;
  await page.getByLabel("Accreditation cycle").selectOption("999999");
  releaseSearch();
  await expect(page.getByText("Synthetic fetched document")).toHaveCount(0);
  await page.getByLabel("Accreditation cycle").selectOption(originalCycle);
  await page.getByLabel("Search all authorized records").fill("synthetic");
  await page.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(page.getByRole("button", { name: /Synthetic fetched document/ })).toBeVisible();
  let detailCalls = 0;
  let releaseDetail!: () => void;
  let sawDetail!: () => void;
  const detailStarted = new Promise<void>((resolve) => { sawDetail = resolve; });
  const detailGate = new Promise<void>((resolve) => { releaseDetail = resolve; });
  const fakeDetail = { id: fakeId, title: "Synthetic fetched document", category: "Fixture",
    area: 1, area_title: "Faculty", cycle: Number(originalCycle), custodian: "Fixture", steward: null,
    steward_id: null, versions: [], mappings: [], can_upload: false, can_delegate_stewardship: false };
  await page.route(`**/api/documents/${fakeId}/`, async (route) => {
    detailCalls++;
    if (detailCalls === 1) {
      await route.fulfill({ status: 503, json: { detail: "Synthetic detail failure" } });
    } else if (detailCalls === 2) {
      await route.fulfill({ json: fakeDetail });
    } else {
      sawDetail();
      await detailGate;
      await route.fulfill({ json: fakeDetail });
    }
  });
  await page.getByRole("button", { name: /Synthetic fetched document/ }).click();
  await expect(page.getByText("Synthetic detail failure")).toBeVisible();
  await page.getByRole("button", { name: /Synthetic fetched document/ }).click();
  await expect(page.getByRole("heading", { name: "Synthetic fetched document" })).toBeVisible();
  await page.getByRole("button", { name: "Search", exact: true }).first().click();
  await page.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(page.getByRole("button", { name: /Synthetic fetched document/ })).toBeVisible();
  await page.getByRole("button", { name: /Synthetic fetched document/ }).click();
  await detailStarted;
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "viewer");
  releaseDetail();
  await expect(page.getByRole("heading", { name: "Synthetic fetched document" })).toHaveCount(0);
  expect(detailCalls).toBe(3);
});
