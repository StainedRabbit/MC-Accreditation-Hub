import { test, expect } from "@playwright/test";

test.skip(!process.env.E2E_ISOLATED_DB_NAME, "Run through scripts/run_isolated_browser.py.");

function event(id: number, record: string, action = "synthetic_review") {
  return { id, actor: "Fictional Coordinator", actor_id: 1, action, record,
    detail: {}, area_id: 1, request_id: "fixture", created_at: "2026-09-27T00:00:00Z" };
}

test("audit search changes clear the old cursor and ignore a delayed older page", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(process.env.E2E_SYNTHETIC_PASSWORD!);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();

  let releaseOlder!: () => void;
  let olderStarted!: () => void;
  const olderGate = new Promise<void>((resolve) => { releaseOlder = resolve; });
  const started = new Promise<void>((resolve) => { olderStarted = resolve; });
  const requested: Array<{ search: string | null; action: string | null; cursor: string | null; fromDate: string | null; toDate: string | null }> = [];
  await page.route("**/api/audit/?**", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    const search = params.get("search"), action = params.get("action"), cursor = params.get("cursor");
    requested.push({ search, action, cursor, fromDate: params.get("from_date"), toDate: params.get("to_date") });
    if (cursor === "older-90") {
      olderStarted();
      await olderGate;
      await route.fulfill({ json: { results: [event(85, "stale older record")], next_cursor: null } });
    } else if (search === "fresh" && cursor === "older-70") {
      await route.fulfill({ json: { results: [event(60, "fresh oldest record")], next_cursor: null } });
    } else if (search === "fresh" && action === "synthetic_new") {
      await route.fulfill({ json: { results: [event(55, "new action record", "synthetic_new")], next_cursor: null } });
    } else if (search === "fresh") {
      await route.fulfill({ json: { results: [event(80, "fresh recent record"), event(70, "fresh older record")], next_cursor: "older-70" } });
    } else {
      await route.fulfill({ json: { results: [event(100, "initial record"), event(90, "initial older record")], next_cursor: "older-90" } });
    }
  });

  await page.getByRole("button", { name: "Audit Trail" }).click();
  await expect(page.getByText("initial record")).toBeVisible();
  await page.getByRole("button", { name: "Load older events" }).click();
  await started;
  await page.getByLabel("Search", { exact: true }).fill("fresh");
  await expect(page.getByText("fresh recent record")).toBeVisible();
  releaseOlder();
  await expect(page.getByText("stale older record")).toHaveCount(0);

  await page.getByRole("button", { name: "Load older events" }).click();
  await expect(page.getByText("fresh oldest record")).toBeVisible();
  expect(requested.some((entry) => entry.search === "fresh" && entry.cursor === "older-70")).toBe(true);
  expect(requested.some((entry) => entry.search === "fresh" && entry.cursor === "older-90")).toBe(false);

  await page.getByLabel("Action", { exact: true }).fill("synthetic_new");
  await expect(page.getByRole("button", { name: "Load older events" })).toHaveCount(0);
  await expect(page.getByText("new action record")).toBeVisible();
  await expect(page.getByText("fresh recent record")).toHaveCount(0);
  await page.getByLabel("From date").fill("2026-09-01");
  await page.getByLabel("To date").fill("2026-09-30");
  await expect.poll(() => requested.some((entry) => entry.fromDate === "2026-09-01" && entry.toDate === "2026-09-30")).toBe(true);
  expect(requested.some((entry) => entry.search === "fresh" && entry.action === "synthetic_new" && entry.fromDate === "2026-09-01" && entry.toDate === "2026-09-30")).toBe(true);
});
