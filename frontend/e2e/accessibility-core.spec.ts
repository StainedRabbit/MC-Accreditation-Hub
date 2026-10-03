import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const password = process.env.E2E_SYNTHETIC_PASSWORD || fs.readFileSync(path.join(root, ".local/demo-credentials.txt"), "utf8")
  .match(/Password for these fictional accounts: (.+)/)![1].trim();

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email / Username").fill("demo.coordinator");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Welcome,/ })).toBeVisible();
  await expect(page.getByText("Updating records…")).toHaveCount(0, { timeout: 30000 });
}

function contrastRatio(foreground: string, background: string) {
  const luminance = (color: string) => {
    const channels = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map((channel) => {
      const normalized = channel / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };
  const first = luminance(foreground);
  const second = luminance(background);
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}

function compositeColor(overlay: string, background: string) {
  const over = overlay.match(/[\d.]+/g)!.map(Number);
  const under = background.match(/[\d.]+/g)!.map(Number);
  const alpha = over[3] ?? 1;
  return `rgb(${[0, 1, 2].map((index) => Math.round(over[index] * alpha + under[index] * (1 - alpha))).join(", ")})`;
}

test("mobile navigation and compliance indicators expose accessible state and contrast", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);

  const menu = page.getByRole("button", { name: "Open navigation" });
  const sidebar = page.locator(".sidebar");
  await expect(menu).toHaveAttribute("aria-controls", "primary-navigation");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(sidebar).toBeHidden();
  expect(await page.evaluate(() => {
    const hiddenNavItem = document.querySelector<HTMLElement>(".sidebar nav button");
    hiddenNavItem?.focus();
    return document.activeElement === hiddenNavItem;
  })).toBeFalsy();

  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("button", { name: "Close navigation" })).toBeFocused();
  const firstNavItem = sidebar.getByRole("button", { name: "Dashboard", exact: true });
  await page.keyboard.press("Tab");
  await expect(firstNavItem).toBeFocused();
  const navContrast = await firstNavItem.evaluate((element) => {
    const sidebarElement = element.closest(".sidebar")!;
    const image = getComputedStyle(sidebarElement).backgroundImage;
    const stops = [...image.matchAll(/rgb\([^)]+\)/g)].map((match) => match[0]);
    return {
      outline: getComputedStyle(element).outlineColor,
      text: getComputedStyle(element).color,
      surface: getComputedStyle(element).backgroundColor,
      stops,
    };
  });
  expect(navContrast.stops.length).toBeGreaterThanOrEqual(2);
  for (const stop of navContrast.stops) {
    const renderedSurface = compositeColor(navContrast.surface, stop);
    expect(contrastRatio(navContrast.outline, renderedSurface)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(navContrast.text, renderedSurface)).toBeGreaterThanOrEqual(4.5);
  }

  await page.keyboard.press("Escape");
  await expect(sidebar).toBeHidden();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();
  expect(contrastRatio(await menu.evaluate((element) => getComputedStyle(element).outlineColor), "rgb(255, 255, 255)")).toBeGreaterThanOrEqual(3);
  await menu.click();
  await sidebar.getByRole("button", { name: "Requirements", exact: true }).click();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("heading", { name: "Requirements", exact: true })).toBeFocused();

  await menu.click();
  await sidebar.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeFocused();
  const meters = page.getByRole("meter");
  await expect(meters.first()).toHaveAttribute("aria-valuenow", /^\d+$/);
  await expect(meters.first()).toHaveAccessibleName(/compliance|evidence coverage/i);
  const meterColors = await meters.first().evaluate((element) => ({
    fill: getComputedStyle(element.querySelector("span")!).backgroundColor,
    track: getComputedStyle(element).backgroundColor,
  }));
  expect(contrastRatio(meterColors.fill, meterColors.track)).toBeGreaterThanOrEqual(3);

  await menu.click();
  await sidebar.getByRole("button", { name: "Requirements", exact: true }).click();
  const smallText = await page.locator("table small").first().evaluate((element) => {
    let parent: HTMLElement | null = element as HTMLElement;
    let background = "rgba(0, 0, 0, 0)";
    while (parent) {
      const color = getComputedStyle(parent).backgroundColor;
      if (!color.endsWith(", 0)")) {
        background = color;
        break;
      }
      parent = parent.parentElement;
    }
    return { foreground: getComputedStyle(element).color, background };
  });
  expect(contrastRatio(smallText.foreground, smallText.background)).toBeGreaterThanOrEqual(4.5);
  const sidebarText = await page.locator(".sidebar .nav-label").evaluate((element) => {
    const style = getComputedStyle(element);
    const image = getComputedStyle(element.closest(".sidebar")!).backgroundImage;
    return { foreground: style.color, stops: [...image.matchAll(/rgb\([^)]+\)/g)].map((match) => match[0]) };
  });
  for (const stop of sidebarText.stops) expect(contrastRatio(sidebarText.foreground, stop)).toBeGreaterThanOrEqual(4.5);

  // A 640×800 CSS viewport represents a 1280×1600 screen at 200% browser zoom.
  await page.setViewportSize({ width: 640, height: 800 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Account security" }).click();
  const dialog = page.getByRole("dialog", { name: "Change password" });
  await expect(dialog).toBeVisible();
  const bounds = await dialog.boundingBox();
  const viewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
  expect(bounds).toBeTruthy();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.y).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width);
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height);
});
