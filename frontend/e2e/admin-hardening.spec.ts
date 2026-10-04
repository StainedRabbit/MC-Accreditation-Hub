import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const backend = process.env.E2E_BACKEND_URL!;
const password = process.env.E2E_SYNTHETIC_PASSWORD!;
const fixture = JSON.parse(fs.readFileSync(path.join(process.env.E2E_SCRATCH!, 'admin-fixture.json'), 'utf8'));

async function login(page: any, username: string) {
  await page.goto(backend + '/api/admin/login/');
  await page.locator('#id_username').fill(username);
  await page.locator('#id_password').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByText('MC Accreditation Hub Administration')).toBeVisible();
}

test('routine admin and credential operator have separate reasoned paths', async ({ browser }) => {
  const account = await browser.newContext();
  const page = await account.newPage();
  await login(page, 'e2e.account.admin');
  await page.goto(backend + '/api/admin/hub/user/add/');
  await expect(page.locator('#id_username')).toBeVisible();
  await expect(page.locator('#id_reason')).toBeVisible();
  await expect(page.locator('#id_is_staff')).toHaveCount(0);
  await expect(page.locator('#id_is_superuser')).toHaveCount(0);
  await expect(page.getByText('Role assignments')).toHaveCount(0);
  await page.locator('#id_username').fill('e2e.browser.created');
  await page.locator('#id_email').fill('e2e.browser.created@test.invalid');
  await page.locator('input[name="_save"]').click();
  await expect(page.getByText('This field is required.')).toBeVisible();
  await page.locator('#id_reason').fill('Fictional browser intake');
  await page.locator('input[name="_save"]').click();
  await expect(page.getByText(/was added successfully/)).toBeVisible();
  await page.goto(backend + '/api/admin/hub/user/' + fixture['e2e.ordinary'] + '/change/');
  await expect(page.locator('#id_is_active')).toBeChecked();
  await expect(page.locator('#id_password')).toHaveCount(0);
  await page.locator('#id_is_active').uncheck();
  await page.locator('#id_reason').fill('Fictional deactivation');
  await page.locator('input[name="_save"]').click();
  await expect(page.getByText(/was changed successfully/)).toBeVisible();
  await page.goto(backend + '/api/admin/hub/user/' + fixture['e2e.account.admin'] + '/change/');
  await expect(page.locator('#id_username')).toHaveCount(0);
  await expect(page.locator('input[name="_save"]')).toHaveCount(0);
  expect((await page.goto(backend + '/api/admin/hub/user/' + fixture['e2e.ordinary'] + '/password/'))!.status()).toBe(403);
  await account.close();

  const credential = await browser.newContext();
  const recovery = await credential.newPage();
  await login(recovery, 'e2e.credential.operator');
  await recovery.goto(backend + '/api/admin/hub/user/' + fixture['e2e.ordinary'] + '/change/');
  await expect(recovery.getByRole('link', { name: 'Set a new password with a reason' })).toBeVisible();
  await recovery.getByRole('link', { name: 'Set a new password with a reason' }).click();
  await expect(recovery.getByRole('heading', { name: /Set password/ })).toBeVisible();
  await recovery.locator('#id_new_password1').fill('Synthetic-browser-234');
  await recovery.locator('#id_new_password2').fill('Synthetic-browser-234');
  await recovery.getByRole('button', { name: 'Set password' }).click();
  expect(await recovery.locator('#id_reason').evaluate((element: HTMLInputElement) => element.validity.valueMissing)).toBe(true);
  await recovery.locator('#id_reason').fill('Fictional verified recovery');
  await recovery.getByRole('button', { name: 'Set password' }).click();
  await expect(recovery.getByText(/Password changed/)).toBeVisible();
  await credential.close();
});
