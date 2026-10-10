import { chromium } from '@playwright/test';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const root = path.resolve(import.meta.dirname, '..');
const dir = path.join(root, 'docs', 'course-presentation');
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(dir, 'MC_Accreditation_Hub_MIT007.html')).href);
await page.evaluate(() => document.fonts.ready);
const slides = page.locator('.slide');
const count = await slides.count();
const qa = path.join(root, '.local', 'course-demo', 'slide-qa');
fs.mkdirSync(qa, { recursive: true });
const problems = [];
for (let i = 0; i < count; i++) {
  const slide = slides.nth(i);
  const overflow = await slide.evaluate(el => {
    const base = el.getBoundingClientRect();
    return [...el.querySelectorAll('h1,h2,.lead,.bullets,.image-layout,.decisions,.architecture,.table-layout,.cover-footer')]
      .filter(node => {
        const r = node.getBoundingClientRect();
        return r.right > base.right + 2 || r.bottom > base.bottom - 32;
      }).map(node => `${node.className || node.tagName}: ${node.textContent?.slice(0, 60)}`);
  });
  if (overflow.length) problems.push({ slide: i + 1, overflow });
  await slide.screenshot({ path: path.join(qa, `${String(i + 1).padStart(2, '0')}.png`) });
}
await page.pdf({ path: path.join(dir, 'MC_Accreditation_Hub_MIT007.pdf'),
  printBackground: true, width: '13.333in', height: '7.5in', margin: {top:'0',right:'0',bottom:'0',left:'0'} });
console.log(JSON.stringify({ slides: count, overflow: problems }, null, 2));
await browser.close();
