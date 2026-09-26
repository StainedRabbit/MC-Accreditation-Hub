import { test, expect } from "@playwright/test";

test.skip(!process.env.E2E_ISOLATED_DB_NAME, "Run through scripts/run_isolated_browser.py.");

test("search loads both result types beyond fifty and discards stale continuation", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(process.env.E2E_SYNTHETIC_PASSWORD!);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await page.getByRole("button", { name: "Search", exact: true }).first().click();

  const firstRequirements = Array.from({ length: 50 }, (_, index) => ({
    id: index + 1, code: `SYN-${index + 1}`, title: `Fictional requirement ${index + 1}`,
    area: "Faculty", status: "missing",
  }));
  const firstDocuments = Array.from({ length: 50 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    title: `Fictional document ${index + 1}`, category: "Fixture", area: "Faculty",
  }));
  let releaseContinuation!: () => void;
  let continuationStarted!: () => void;
  const gate = new Promise<void>((resolve) => { releaseContinuation = resolve; });
  const started = new Promise<void>((resolve) => { continuationStarted = resolve; });
  let documentRequests = 0;
  await page.route("**/api/search/?**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("kind") === "requirements") {
      await route.fulfill({ json: { requirements: [{ id: 51, code: "SYN-51", title: "Fictional requirement 51",
        area: "Faculty", status: "missing" }], documents: [], next_requirements: null, next_documents: null } });
    } else if (url.searchParams.get("kind") === "documents") {
      documentRequests++;
      if (documentRequests === 2) { continuationStarted(); await gate; }
      await route.fulfill({ json: { requirements: [], documents: [{ id: "00000000-0000-4000-8000-000000000051",
        title: "Fictional document 51", category: "Fixture", area: "Faculty" }],
        next_requirements: null, next_documents: null } });
    } else {
      await route.fulfill({ json: { requirements: firstRequirements, documents: firstDocuments,
        next_requirements: 50, next_documents: firstDocuments[49].id } });
    }
  });
  await page.getByLabel("Search all authorized records").fill("fictional");
  await page.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(page.getByRole("button", { name: "Load more requirements" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Load more documents" })).toBeVisible();
  await page.getByRole("button", { name: "Load more requirements" }).click();
  await expect(page.getByRole("button", { name: /Fictional requirement 51/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Load more requirements" })).toHaveCount(0);
  await page.getByRole("button", { name: "Load more documents" }).click();
  await expect(page.getByRole("button", { name: /Fictional document 51/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Load more documents" })).toHaveCount(0);
  await page.getByRole("button", { name: "Search", exact: true }).last().click();
  await expect(page.getByRole("button", { name: "Load more documents" })).toBeVisible();
  await page.getByRole("button", { name: "Load more documents" }).click();
  await started;
  await page.getByLabel("Search all authorized records").fill("changed term");
  releaseContinuation();
  await expect(page.getByText("Fictional document 51")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Load more documents" })).toHaveCount(0);
});
