import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const password = process.env.E2E_SYNTHETIC_PASSWORD || fs.readFileSync(path.join(root, ".local/demo-credentials.txt"), "utf8")
  .match(/Password for these fictional accounts: (.+)/)![1].trim();
const samplePdf = process.env.E2E_SAMPLE_PDF || path.join(root, ".local/sample-evidence.pdf");
const requirementTitle = "Legacy review context fixture";

async function login(page: Page, role: string) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill(`demo.${role}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await expect(page.getByText("Updating records…")).toHaveCount(0, { timeout: 30000 });
}

async function openRequirement(page: Page) {
  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  await expect(page.getByText("Updating records…")).toHaveCount(0, { timeout: 30000 });
  await page.getByRole("row").filter({ hasText: requirementTitle })
    .getByRole("button", { name: "View", exact: true }).click();
}

async function postSubmission(page: Page, mapping: number, version: number) {
  const csrf = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  return page.request.post("/api/submissions/", {
    data: { mapping, version }, headers: { "X-CSRFToken": csrf! },
  });
}

test("legacy item review shows current criteria, exact file and prior decision", async ({ browser }) => {
  const custodianContext = await browser.newContext();
  const reviewerContext = await browser.newContext();
  const custodian = await custodianContext.newPage();
  const reviewer = await reviewerContext.newPage();
  await login(custodian, "custodian");
  const cycles = await (await custodian.request.get("/api/cycles/")).json();
  const cycle = cycles.find((entry: { title: string }) => entry.title === "DEMO · Graduate School 2026");
  expect(cycle).toBeTruthy();
  await openRequirement(custodian);
  await custodian.getByRole("button", { name: "Upload evidence" }).click();
  const upload = custodian.getByRole("dialog");
  await upload.getByLabel("Document title").fill("Legacy review evidence record");
  const bytes = fs.readFileSync(samplePdf);
  expect(bytes.length).toBeGreaterThan(0);
  await upload.locator("input[type=file]").setInputFiles({
    name: "legacy-review-v1.pdf", mimeType: "application/pdf", buffer: bytes,
  });
  await upload.getByRole("button", { name: "Upload & Map" }).click();
  await expect(upload).toHaveCount(0);
  const docs = await (await custodian.request.get(`/api/documents/?cycle=${cycle.id}&search=Legacy%20review%20evidence%20record`)).json();
  const document = docs.find((entry: { title: string }) => entry.title === "Legacy review evidence record");
  expect(document?.mappings).toHaveLength(1);
  const first = await postSubmission(custodian, document.mappings[0].id, document.versions.find((v: { number: number }) => v.number === 1).id);
  expect(first.status()).toBe(201);
  const firstSubmission = await first.json();

  await login(reviewer, "reviewer");
  await openRequirement(reviewer);
  await reviewer.getByRole("button", { name: "Review", exact: true }).click();
  let review = reviewer.getByRole("dialog");
  await expect(review.getByText("Current requirement criteria · revision 1")).toBeVisible();
  await expect(review.getByText(/A dated file with a clear responsible office/)).toBeVisible();
  await expect(review.getByText(/File: legacy-review-v1.pdf · SHA-256/)).toBeVisible();
  await expect(review.getByText(/valid until No expiry/)).toBeVisible();
  await expect(review.getByText(/Uploaded by Juan Dela Cruz · submitted by Juan Dela Cruz/)).toBeVisible();
  await expect(review.getByText(/Submission criteria revision 1/)).toBeVisible();
  await expect(review.getByRole("combobox", { name: "Decision" })).toHaveValue("");
  await expect(review.getByRole("button", { name: "Record Decision" })).toBeDisabled();
  await review.getByRole("combobox", { name: "Decision" }).selectOption("rejected");
  await expect(review.getByLabel(/Review comments/)).toHaveAttribute("required", "");
  await review.getByLabel(/Review comments/).fill("Replace the sample with a dated office copy.");
  await review.getByRole("button", { name: "Record Decision" }).click();
  await expect(review).toHaveCount(0);

  const csrf = (await custodianContext.cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  expect(csrf).toBeTruthy();
  const replacement = await custodian.request.post(`/api/documents/${document.id}/versions/`, {
    multipart: { file: { name: "legacy-review-v2.pdf", mimeType: "application/pdf", buffer: bytes } },
    headers: { "X-CSRFToken": csrf! },
  });
  expect(replacement.status()).toBe(201);
  const updatedDocument = await replacement.json();
  const secondVersion = updatedDocument.versions.find((v: { number: number }) => v.number === 2);
  expect(secondVersion).toBeTruthy();
  const second = await postSubmission(custodian, document.mappings[0].id, secondVersion.id);
  expect(second.status()).toBe(201);
  const secondSubmission = await second.json();

  await reviewer.reload();
  await expect(reviewer.getByText("Updating records…")).toHaveCount(0, { timeout: 30000 });
  await openRequirement(reviewer);
  await reviewer.getByRole("button", { name: "Review", exact: true }).click();
  review = reviewer.getByRole("dialog");
  await expect(review.getByText(/File: legacy-review-v2.pdf · SHA-256/)).toBeVisible();
  await expect(review.getByText(/Most recent prior decision for this mapping: Rejected by Elena Garcia/)).toBeVisible();
  await review.getByRole("combobox", { name: "Decision" }).selectOption("approved");
  await review.getByRole("button", { name: "Record Decision" }).click();
  await expect(review).toHaveCount(0);
  const decisions = await (await reviewer.request.get("/api/review-decisions/")).json();
  expect(decisions.filter((entry: { submission_id: number }) => [firstSubmission.id, secondSubmission.id].includes(entry.submission_id))).toHaveLength(2);
  await Promise.all([custodianContext.close(), reviewerContext.close()]);
});
