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

test("a lost package submit response recovers the saved attempt once", async ({ browser }) => {
  const coordinatorContext = await browser.newContext();
  const contributorContext = await browser.newContext();
  const coordinator = await coordinatorContext.newPage();
  await login(coordinator, "coordinator");
  await coordinator.getByRole("button", { name: "Requirements", exact: true }).click();
  await coordinator.getByRole("button", { name: "Add Requirement" }).click();
  const setup = coordinator.getByRole("dialog");
  const title = `Submit recovery ${Date.now()}`;
  await setup.getByRole("combobox", { name: "Accreditation area", exact: true }).selectOption({ label: "Faculty" });
  await setup.getByLabel("Requirement code").fill(`SUBMIT-${Date.now()}`);
  await setup.getByLabel("Requirement title").fill(title);
  await setup.getByLabel("Responsible office / person").fill("Graduate School");
  await setup.getByLabel("Evidence item 1").fill("Recovery evidence");
  await setup.getByRole("button", { name: "Save Requirement" }).click();
  await coordinator.getByRole("row").filter({ hasText: title }).getByRole("button", { name: "View", exact: true }).click();
  const cycle = (await (await coordinator.request.get("/api/cycles/")).json())[0];
  const requirements = await (await coordinator.request.get(`/api/requirements/?cycle=${cycle.id}`)).json();
  const requirement = requirements.find((item: { title: string }) => item.title === title);
  expect(requirement).toBeTruthy();
  const assignmentData = await (await coordinator.request.get(`/api/requirements/${requirement.id}/assignments/`)).json();
  const custodian = assignmentData.candidates.find((candidate: { username: string }) => candidate.username === "demo.custodian");
  expect(custodian).toBeTruthy();
  const csrf = (await coordinatorContext.cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  const assigned = await coordinator.request.post(`/api/requirements/${requirement.id}/assignments/`, {
    data: { user: custodian.id, reason: "Package submit recovery browser setup." },
    headers: { "X-CSRFToken": csrf! },
  });
  expect(assigned.status()).toBe(201);

  const contributor = await contributorContext.newPage();
  await login(contributor, "custodian");
  await contributor.getByRole("button", { name: "Requirements", exact: true }).click();
  await contributor.getByRole("row").filter({ hasText: title }).getByRole("button", { name: "View", exact: true }).click();
  await contributor.getByRole("button", { name: "Upload evidence" }).first().click();
  const upload = contributor.getByRole("dialog");
  await upload.getByLabel("Document title").fill(`${title} document`);
  const evidenceBytes = fs.readFileSync(samplePdf);
  expect(evidenceBytes.length).toBeGreaterThan(0);
  await upload.locator("input[type=file]").setInputFiles({
    name: "package-recovery.pdf", mimeType: "application/pdf", buffer: evidenceBytes,
  });
  await upload.getByRole("button", { name: "Upload & Map" }).click();
  await expect(upload).toHaveCount(0);
  await contributor.getByRole("button", { name: "New package draft" }).click();
  const draftForm = contributor.getByRole("dialog");
  await draftForm.getByRole("checkbox", { name: /Include Recovery evidence/ }).check();
  await draftForm.getByRole("button", { name: "Save draft" }).click();
  await expect(draftForm).toHaveCount(0);
  const drafts = await (await contributor.request.get(`/api/packages/?requirement=${requirement.id}`)).json();
  const draft = drafts.find((item: { status: string }) => item.status === "draft");
  expect(draft).toBeTruthy();

  let submits = 0;
  await contributor.route(`**/api/packages/${draft.id}/submit/`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    submits += 1;
    const committed = await route.fetch();
    expect(committed.status(), await committed.text()).toBe(200);
    await route.abort("failed");
  });
  await contributor.getByRole("button", { name: "Submit package" }).click();
  await expect(contributor.getByText("Package submitted for review. Its saved status was recovered.")).toBeVisible();
  expect(submits).toBe(1);
  const savedAttempt = await (await contributor.request.get(`/api/packages/${draft.id}/`)).json();
  expect(savedAttempt.status).toBe("submitted");
  expect(savedAttempt.submitted_at).toBeTruthy();
  const history = await (await coordinator.request.get(`/api/audit/?kind=academic&cycle=${cycle.id}&action=package_submitted`)).json();
  expect(history.results.filter((event: { detail: { package?: number } }) => event.detail.package === draft.id)).toHaveLength(1);
  await Promise.all([coordinatorContext.close(), contributorContext.close()]);
});
