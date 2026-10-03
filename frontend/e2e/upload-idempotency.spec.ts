import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const password = process.env.E2E_SYNTHETIC_PASSWORD || fs.readFileSync(path.join(root, ".local/demo-credentials.txt"), "utf8")
  .match(/Password for these fictional accounts: (.+)/)![1].trim();
const samplePdf = process.env.E2E_SAMPLE_PDF || path.join(root, ".local/sample-evidence.pdf");

async function login(page: Page, role: string) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill(`demo.${role}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await expect(page.getByText("Updating records…")).toHaveCount(0, { timeout: 30000 });
}

test("uncertain Upload & Map retry reuses the key and maps one saved version", async ({ browser }) => {
  const coordinatorContext = await browser.newContext();
  const contributorContext = await browser.newContext();
  const coordinator = await coordinatorContext.newPage();
  await login(coordinator, "coordinator");
  await coordinator.getByRole("button", { name: "Requirements", exact: true }).click();
  await coordinator.getByRole("button", { name: "Add Requirement" }).click();
  const setup = coordinator.getByRole("dialog");
  const title = `Idempotency retry ${Date.now()}`;
  await setup.getByRole("combobox", { name: "Accreditation area", exact: true }).selectOption({ label: "Faculty" });
  await setup.getByLabel("Requirement code").fill(`IDEMP-${Date.now()}`);
  await setup.getByLabel("Requirement title").fill(title);
  await setup.getByLabel("Responsible office / person").fill("Graduate School");
  await setup.getByLabel("Evidence item 1").fill("Retry-safe evidence");
  await setup.getByRole("button", { name: "Save Requirement" }).click();
  await coordinator.getByRole("row").filter({ hasText: title }).getByRole("button", { name: "View" }).click();
  const cycle = (await (await coordinator.request.get("/api/cycles/")).json())[0];
  const requirements = await (await coordinator.request.get(`/api/requirements/?cycle=${cycle.id}`)).json();
  const requirement = requirements.find((item: { title: string }) => item.title === title);
  expect(requirement).toBeTruthy();
  const assignmentData = await (await coordinator.request.get(`/api/requirements/${requirement.id}/assignments/`)).json();
  const custodian = assignmentData.candidates.find((candidate: { username: string }) => candidate.username === "demo.custodian");
  expect(custodian).toBeTruthy();
  const csrf = (await coordinator.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  const assigned = await coordinator.request.post(`/api/requirements/${requirement.id}/assignments/`, {
    data: { user: custodian.id, reason: "Idempotent upload browser recovery setup." },
    headers: { "X-CSRFToken": csrf! },
  });
  expect(assigned.status()).toBe(201);

  const contributor = await contributorContext.newPage();
  await login(contributor, "custodian");
  await contributor.getByRole("button", { name: "Requirements", exact: true }).click();
  await contributor.getByRole("row").filter({ hasText: title }).getByRole("button", { name: "View", exact: true }).click();
  await contributor.getByRole("button", { name: "Upload evidence" }).first().click();
  const upload = contributor.getByRole("dialog");
  const documentTitle = `${title} document`;
  await upload.getByLabel("Document title").fill(documentTitle);
  const evidenceBytes = fs.readFileSync(samplePdf);
  expect(evidenceBytes.length).toBeGreaterThan(0);
  await upload.locator("input[type=file]").setInputFiles({
    name: "retry-evidence.pdf", mimeType: "application/pdf", buffer: evidenceBytes,
  });

  let firstRequest = true;
  const keys: string[] = [];
  await contributor.route("**/api/documents/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push((await route.request().allHeaders())["idempotency-key"]);
    if (firstRequest) {
      firstRequest = false;
      const committed = await route.fetch();
      expect(committed.status(), await committed.text()).toBe(201);
      await route.abort("failed");
    } else {
      await route.continue();
    }
  });

  await upload.getByRole("button", { name: "Upload & Map" }).click();
  await expect(upload.getByText(/couldn't confirm whether the upload finished/i)).toBeVisible();
  await expect(upload.getByRole("button", { name: "Retry same upload" })).toBeVisible();
  await upload.getByRole("button", { name: "Retry same upload" }).click();
  await expect(upload).toHaveCount(0);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);

  const docs = await (await contributor.request.get(`/api/documents/?cycle=${cycle.id}&search=${encodeURIComponent(documentTitle)}`)).json();
  const document = docs.find((item: { title: string }) => item.title === documentTitle);
  expect(document).toBeTruthy();
  expect(document.versions).toHaveLength(1);
  expect(document.mappings).toHaveLength(1);
  await Promise.all([coordinatorContext.close(), contributorContext.close()]);
});
