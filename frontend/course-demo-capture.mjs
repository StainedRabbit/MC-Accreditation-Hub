// Capture the actual UI against the dedicated fictional course-demo database.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, expect } from '@playwright/test';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const state = JSON.parse(fs.readFileSync(path.join(root, '.local/course-demo/state.json'), 'utf8'));
if (state.database !== 'mc_course_demo') throw new Error('The isolated course demo state is required.');
const out = path.join(root, 'docs/course-presentation/screenshots');
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync(path.join(out, 'full'), { recursive: true });
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const contexts = [];

async function pageFor(role) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  contexts.push(context);
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:5173/');
  if (role === 'coordinator') await shot(page, '01-login');
  await page.getByLabel('Email / Username').fill(`demo.${role}`);
  await page.getByLabel('Password', { exact: true }).fill(state.password);
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Welcome,/ })).toBeVisible();
  await ready(page);
  return page;
}

async function ready(page) {
  await expect(page.getByText('Updating records…')).toHaveCount(0, { timeout: 30000 });
}

async function shot(page, name) {
  await ready(page);
  await expect(page.getByText('Updating report…')).toHaveCount(0, { timeout: 30000 });
  await expect(page.getByText('Loading current review context…')).toHaveCount(0, { timeout: 30000 });
  await expect(page.getByRole('button', { name: 'Searching…' })).toHaveCount(0, { timeout: 30000 });
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: false });
  await page.screenshot({ path: path.join(out, 'full', `${name}.png`), fullPage: true });
  console.log(name);
}

async function openFaculty(page) {
  await page.getByRole('button', { name: 'Requirements', exact: true }).click();
  await ready(page);
  await page.getByRole('row').filter({ hasText: 'Faculty Documentation' })
    .getByRole('button', { name: 'View', exact: true }).click();
}

try {
  const coordinator = await pageFor('coordinator');
  await shot(coordinator, '02-dashboard-before');
  await openFaculty(coordinator);
  await shot(coordinator, '03-requirement-before');
  await coordinator.getByRole('button', { name: 'Manage assignments' }).click();
  await shot(coordinator, '04-assignment');
  await coordinator.getByRole('button', { name: 'Close dialog' }).click();

  const custodian = await pageFor('custodian');
  await openFaculty(custodian);
  const sources = [
    ['Faculty plan evidence', 'fictional-faculty-plan.pdf'],
    ['Implementation report evidence', 'fictional-implementation-report.pdf'],
  ];
  for (let index = 0; index < sources.length; index++) {
    await custodian.getByRole('button', { name: 'Upload evidence' }).nth(index).click();
    const upload = custodian.getByRole('dialog');
    await upload.getByLabel('Document title').fill(sources[index][0]);
    await upload.locator('input[type=file]').setInputFiles(path.join(root, '.local/course-demo/source', sources[index][1]));
    await upload.getByRole('button', { name: 'Upload & Map' }).click();
    await expect(upload).toHaveCount(0);
  }
  await custodian.getByRole('heading', { name: 'Evidence checklist' })
    .evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 125));
  await shot(custodian, '05-evidence-mapped');
  await custodian.getByRole('button', { name: 'Evidence Repository' }).click();
  await ready(custodian);
  await shot(custodian, '06-repository-and-scan');
  await custodian.getByRole('row').filter({ hasText: 'Faculty plan evidence' })
    .getByRole('button', { name: 'View', exact: true }).click();
  await custodian.getByRole('heading', { name: 'Document version history' })
    .evaluate(el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 125));
  await shot(custodian, '06b-version-history-and-scan');
  await openFaculty(custodian);
  await custodian.getByRole('button', { name: 'New package draft' }).click();
  const editor = custodian.getByRole('dialog');
  await editor.getByLabel('Package notes').fill('Fictional MIT 007 course demonstration.');
  await editor.getByRole('checkbox', { name: /Include Approved plan or policy/ }).check();
  await editor.getByRole('checkbox', { name: /Include Implementation report/ }).check();
  await shot(custodian, '07-package-draft');
  await editor.getByRole('button', { name: 'Save draft' }).click();
  await custodian.getByRole('button', { name: 'Submit package' }).click();
  await expect(custodian.locator('.requirement-summary').getByText('For Verification', { exact: true })).toBeVisible();
  await shot(custodian, '08-package-submitted');

  const reviewer = await pageFor('reviewer');
  await reviewer.getByRole('button', { name: 'Evidence Verification' }).click();
  await expect(reviewer.getByRole('row').filter({ hasText: 'Faculty Documentation' })).toBeVisible();
  await shot(reviewer, '09-review-queue');
  await reviewer.getByRole('row').filter({ hasText: 'Faculty Documentation' })
    .getByRole('button', { name: 'Review package' }).click();
  const review = reviewer.getByRole('dialog');
  await shot(reviewer, '10-review-context');
  await review.getByRole('combobox', { name: 'Decision' }).selectOption('approved');
  await review.getByRole('button', { name: 'Record package decision' }).click();

  await coordinator.reload();
  await ready(coordinator);
  await openFaculty(coordinator);
  await expect(coordinator.getByRole('heading', { name: 'Ready for Completion Review' })).toBeVisible();
  await shot(coordinator, '11-ready-for-certification');
  await coordinator.getByRole('button', { name: 'Mark Complete' }).click();
  const cert = coordinator.getByRole('dialog');
  await cert.getByLabel('Rationale').fill('Current approved fictional package covers both mandatory items.');
  await cert.getByRole('checkbox').check();
  await shot(coordinator, '12-certification-dialog');
  await cert.getByRole('button', { name: 'Mark Complete' }).click();
  await expect(cert).toHaveCount(0);
  await shot(coordinator, '13-requirement-complete');
  await coordinator.getByRole('button', { name: 'Dashboard' }).click();
  await ready(coordinator);
  await shot(coordinator, '14-dashboard-after');
  await coordinator.getByRole('button', { name: 'Reports', exact: true }).click();
  await ready(coordinator);
  await shot(coordinator, '15-compliance-report');
  await coordinator.getByRole('button', { name: 'Search', exact: true }).click();
  await coordinator.getByLabel('Search all authorized records').fill('Faculty');
  await coordinator.getByRole('button', { name: 'Search', exact: true }).last().click();
  await shot(coordinator, '16-scoped-search');
  await coordinator.getByRole('button', { name: 'Audit Trail' }).click();
  await ready(coordinator);
  await shot(coordinator, '17-audit-trail');

  const viewer = await pageFor('viewer');
  await viewer.getByRole('button', { name: 'Evidence Repository' }).click();
  await ready(viewer);
  await shot(viewer, '18-viewer-approved-only');
  const packages = await coordinator.evaluate(async () => {
    const response = await fetch('/api/packages/', { credentials: 'include' });
    if (!response.ok) throw new Error(`Coordinator packages returned ${response.status}`);
    return response.json();
  });
  const packageId = packages.find(item => item.requirement_title === 'Faculty Documentation')?.id || packages[0]?.id;
  if (!packageId) throw new Error('The fictional submitted package was not found.');
  const denied = await viewer.goto(`http://127.0.0.1:5173/api/packages/${packageId}/`);
  console.log('Viewer package detail status:', denied.status());
  if (![403, 404].includes(denied.status())) throw new Error('Viewer package history was unexpectedly visible.');
  await shot(viewer, '19-scoped-denial');
  const label = spawnSync('python', ['-B', 'scripts/label_course_screenshots.py'],
    { cwd: root, encoding: 'utf8' });
  if (label.status !== 0) throw new Error(`Screenshot labeling failed: ${label.stderr}`);
  console.log(label.stdout.trim());
  console.log('Fictional course demo capture complete.');
} finally {
  await Promise.all(contexts.map(context => context.close()));
  await browser.close();
}
