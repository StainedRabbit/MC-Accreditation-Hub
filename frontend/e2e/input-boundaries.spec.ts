import { test, expect } from "@playwright/test";

test("failed CSRF bootstrap blocks login without sending credentials", async ({ page }) => {
  let loginRequests = 0;
  await page.route("**/api/auth/csrf/", route => route.fulfill({ status: 503, body: "unavailable" }));
  await page.route("**/api/auth/login/", route => { loginRequests++; return route.abort(); });
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("synthetic.invalid");
  await page.getByLabel("Password", { exact: true }).fill("synthetic-placeholder");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Unable to prepare this request");
  expect(loginRequests).toBe(0);
});

test("malformed CSRF bootstrap blocks login without sending credentials", async ({ page }) => {
  let loginRequests = 0;
  await page.route("**/api/auth/csrf/", route => route.fulfill({ status: 200, contentType: "text/html", body: "invalid" }));
  await page.route("**/api/auth/login/", route => { loginRequests++; return route.abort(); });
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("synthetic.invalid");
  await page.getByLabel("Password", { exact: true }).fill("synthetic-placeholder");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Unable to prepare this request");
  expect(loginRequests).toBe(0);
});
